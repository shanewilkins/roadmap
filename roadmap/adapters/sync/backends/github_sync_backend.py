"""GitHub-specific implementation of SyncBackendInterface.

This module provides the GitHub API backend for syncing roadmap issues
with GitHub repositories. It implements the SyncBackendInterface protocol.

Updated to use Result<T, SyncError> pattern for explicit error handling.
"""

from collections.abc import Callable
from datetime import datetime  # noqa: F401  # Used in type hints
import time
from typing import Any, TypeVar

from structlog import get_logger

from roadmap.adapters.sync.backends.github_backend_helpers import GitHubBackendHelpers
from roadmap.adapters.sync.backends.github_client import GitHubClientWrapper
from roadmap.adapters.sync.backends.services.github_authentication_service import (
    GitHubAuthenticationService,
)
from roadmap.adapters.sync.backends.services.github_issue_fetch_service import (
    GitHubIssueFetchService,
)
from roadmap.common.result import Err, Ok, Result
from roadmap.core.domain.issue import Issue
from roadmap.core.interfaces import (
    SyncConflict,
    SyncReport,
)
from roadmap.core.models.sync_models import (
    SyncIssue,
    SyncMilestone,
    SyncProject,
)
from roadmap.core.services.sync.sync_errors import (
    SyncError,
    SyncErrorType,
    authentication_error,
)
from roadmap.core.services.sync.sync_metadata_service import SyncMetadataService
from roadmap.infrastructure.coordination.core import RoadmapCore

logger = get_logger()

T = TypeVar("T")


class GitHubSyncBackend:
    """GitHub API implementation of the SyncBackendInterface.

    Syncs roadmap issues with GitHub issues using the GitHub REST API.
    Requires a GitHub Personal Access Token with 'repo' scope.

    Attributes:
        core: RoadmapCore instance with access to local issues
        config: GitHub configuration with 'owner', 'repo', 'token'
        github_client: GitHubIssueClient for API communication
    """

    def __init__(self, core: RoadmapCore, config: dict[str, Any]):
        """Initialize GitHub sync backend.

        Args:
            core: RoadmapCore instance
            config: Dict with required keys:
                - owner: GitHub repository owner
                - repo: GitHub repository name
                - token: GitHub Personal Access Token (optional, checked at auth time)

        Raises:
            ValueError: If required config keys are missing
        """
        if not config.get("owner") or not config.get("repo"):
            raise ValueError("GitHub config must include 'owner' and 'repo'")

        self.core = core
        self.config = config

        # Initialize GitHub client if token is provided, otherwise defer to authenticate()
        token = config.get("token")
        owner = config.get("owner")
        repo = config.get("repo")
        self.github_client = self._safe_init(
            lambda: GitHubClientWrapper(token, owner, repo) if token else None,
            "GitHubClientWrapper",
        )

        # Initialize metadata service if available
        self.metadata_service = self._safe_init(
            lambda: SyncMetadataService(core),
            "SyncMetadataService",
        )

        # Initialize remote link repository if available
        # This enables fast database lookups during sync operations
        self.remote_link_repo = None
        if (
            hasattr(core, "db")
            and core.db is not None
            and hasattr(core.db, "remote_links")
        ):
            self.remote_link_repo = core.db.remote_links

        # Helper utilities extracted for mapping and local persistence
        self._helpers = GitHubBackendHelpers(
            core=self.core, remote_link_repo=self.remote_link_repo
        )

        # Initialize delegated services
        self._auth_service = GitHubAuthenticationService(config)
        self._fetch_service = None  # Initialized lazily after auth

    def _safe_init(self, factory: Callable[[], T], name: str) -> T | None:
        """Safely initialize a component, returning None on failure.

        Args:
            factory: Callable that returns the initialized component
            name: Component name for logging

        Returns:
            Initialized component or None if initialization fails
        """
        try:
            return factory()
        except (ImportError, AttributeError) as e:
            logger.warning(
                "initialization_failed",
                component=name,
                error=str(e),
                error_type=type(e).__name__,
                suggested_action="check_dependencies",
            )
            return None
        except Exception as e:
            logger.warning(
                "initialization_failed",
                component=name,
                error=str(e),
                error_type=type(e).__name__,
                error_classification="unknown_error",
            )
            return None

    def get_backend_name(self) -> str:
        """Get the canonical name of this backend.

        Returns:
            'github' - used as key in Issue.remote_ids dict
        """
        return "github"

    def authenticate(self) -> Result[bool, SyncError]:
        """Verify credentials and remote connectivity.

        Returns:
            Ok(True) if authentication succeeds (token valid and repo accessible)
            Err(SyncError) with authentication error details
        """
        try:
            result = self._auth_service.authenticate()
            if result and self.github_client is None:
                # Update our client reference after successful auth
                self.github_client = self._auth_service.github_client

            if result:
                return Ok(True)
            else:
                return Err(authentication_error("GitHub authentication failed"))
        except Exception as e:
            logger.error(
                "github_authenticate_exception",
                error=str(e),
                error_type=type(e).__name__,
            )
            return Err(
                SyncError.from_exception(
                    e,
                    error_type=SyncErrorType.AUTHENTICATION_FAILED,
                )
            )

    def get_api_client(self) -> Any:
        """Get the GitHub API client with handler methods for push/pull operations.

        Returns:
            IssueHandler instance with create_issue(), update_issue(), etc. methods.

        This method is used internally by GitHubSyncOps for actual API calls.
        It ensures operations use the proper handler-based client for low-level
        API operations, not the high-level GitHubClient wrapper.
        """
        import requests

        from roadmap.adapters.github.handlers.issues import IssueHandler

        # Create a session with the token
        session = requests.Session()
        token = self.config.get("token")
        if token:
            session.headers.update(
                {
                    "Authorization": f"token {token}",
                    "Accept": "application/vnd.github.v3+json",
                    "User-Agent": "roadmap-cli/1.0",
                }
            )

        # Return a properly configured issue handler for API calls
        return IssueHandler(
            session=session,
            owner=self.config.get("owner"),
            repo=self.config.get("repo"),
        )

    def get_label_client(self) -> Any | None:
        """Get a GitHub client that supports label operations."""
        token = self.config.get("token")
        if not token:
            return None

        from roadmap.adapters.github.github import GitHubClient

        return GitHubClient(
            token=token,
            owner=self.config.get("owner"),
            repo=self.config.get("repo"),
        )

    def get_issues(self) -> Result[dict[str, SyncIssue], SyncError]:
        """Fetch all issues from GitHub remote.

        Returns:
            Ok(dict) mapping issue_id -> SyncIssue objects on success
            Err(SyncError) with error details on failure
        """
        try:
            # Lazily initialize fetch service after first auth
            if self._fetch_service is None and self.github_client:
                self._fetch_service = GitHubIssueFetchService(
                    self.github_client, self.config, self._helpers
                )

            if self._fetch_service is None:
                logger.warning("github_fetch_service_not_initialized")
                return Err(
                    SyncError(
                        error_type=SyncErrorType.AUTHENTICATION_FAILED,
                        message="GitHub fetch service not initialized - authenticate first",
                        suggested_fix="Call authenticate() before get_issues()",
                    )
                )

            issues = self._fetch_service.get_issues()
            return Ok(issues)
        except Exception as e:
            logger.error(
                "github_get_issues_exception",
                error=str(e),
                error_type=type(e).__name__,
            )
            return Err(
                SyncError.from_exception(
                    e,
                    error_type=SyncErrorType.NETWORK_ERROR,
                )
            )

    def push_issues(self, local_issues: list[Issue]) -> Result[SyncReport, SyncError]:
        """Push multiple local issues to GitHub.

        Args:
            local_issues: List of Issue objects to push

        Returns:
            Ok(SyncReport) with pushed, conflicts, and errors on success
            Err(SyncError) with fatal error details if operation cannot proceed
        """
        try:
            # Delegate orchestration to helper class
            from roadmap.adapters.sync.backends.github_sync_ops import GitHubSyncOps

            ops = GitHubSyncOps(self)
            report = ops.push_issues(local_issues)
            return Ok(report)
        except Exception as e:
            logger.error(
                "github_push_issues_exception",
                error=str(e),
                error_type=type(e).__name__,
                issue_count=len(local_issues),
            )
            return Err(
                SyncError.from_exception(
                    e,
                    error_type=SyncErrorType.UNKNOWN_ERROR,
                    entity_type="Issue",
                )
            )

    def push_issue(self, local_issue: Issue) -> Result[bool, SyncError]:
        """Push a single local issue to GitHub.

        Args:
            local_issue: The Issue object to push

        Returns:
            Ok(True) if push succeeds
            Err(SyncError) with error details if push fails

        Deprecated:
            Use push_issues([issue]) instead. This method exists for backward
            compatibility but is not used by the sync orchestrator.
        """
        report_result = self.push_issues([local_issue])
        if report_result.is_err():
            return report_result  # type: ignore[return-value]

        report = report_result.unwrap()
        if len(report.pushed) > 0 and len(report.errors) == 0:
            return Ok(True)
        else:
            error_msg = report.errors.get(str(local_issue.id), "Push failed")
            return Err(
                SyncError(
                    error_type=SyncErrorType.UNKNOWN_ERROR,
                    message=error_msg,
                    entity_type="Issue",
                    entity_id=str(local_issue.id),
                )
            )

    def pull_issues(self, issue_ids: list[str]) -> Result[SyncReport, SyncError]:
        """Pull specified remote GitHub issues to local.

        Args:
            issue_ids: List of remote issue IDs to pull

        Returns:
            Ok(SyncReport) with pulled, conflicts, and errors on success
            Err(SyncError) with fatal error details if operation cannot proceed

        Notes:
            - Each ID should correspond to a remote issue
            - Updates or creates local files as needed
            - Uses parallel execution with thread pool for performance
        """
        try:
            from roadmap.adapters.sync.backends.github_sync_ops import GitHubSyncOps

            ops = GitHubSyncOps(self)
            report = ops.pull_issues(issue_ids)
            return Ok(report)
        except Exception as e:
            logger.error(
                "github_pull_issues_exception",
                error=str(e),
                error_type=type(e).__name__,
                issue_count=len(issue_ids),
            )
            return Err(
                SyncError.from_exception(
                    e,
                    error_type=SyncErrorType.UNKNOWN_ERROR,
                    entity_type="Issue",
                )
            )

    def pull_milestones(self, milestone_ids: list[str]) -> SyncReport:
        """Pull specified remote GitHub milestones to local.

        Args:
            milestone_ids: List of remote milestone IDs to pull (GitHub milestone numbers)

        Returns:
            SyncReport with pulled, conflicts, and errors.
        """
        from roadmap.adapters.sync.backends.github_sync_ops import GitHubSyncOps

        ops = GitHubSyncOps(self)
        return ops.pull_milestones(milestone_ids)

    def push_milestones(self, local_milestones: list) -> SyncReport:
        """Push multiple local milestones to GitHub.

        Args:
            local_milestones: List of Milestone objects to push

        Returns:
            SyncReport with pushed, conflicts, and errors.

        Note:
            Currently not implemented - milestones must be created on GitHub first.
        """
        from roadmap.adapters.sync.backends.github_sync_ops import GitHubSyncOps

        ops = GitHubSyncOps(self)
        return ops.push_milestones(local_milestones)

    def pull_issue(self, issue_id: str) -> Result[bool, SyncError]:
        """Pull a single remote GitHub issue to local.

        Args:
            issue_id: The remote issue ID (GitHub issue number like "_remote_123" or "123")

        Returns:
            Ok(True) if issue is valid and can be pulled
            Err(SyncError) if error during validation

        Notes:
            - Validates the issue_id can be parsed
            - Actual fetching/saving is handled by pull_issues caller
            - Returns Ok(True) to indicate success to GitHubSyncOps
        """
        try:
            # Parse issue_id - extract numeric part from "_remote_123" format
            if issue_id.startswith("_remote_"):
                issue_num_str = issue_id[8:]  # Remove "_remote_" prefix
            else:
                issue_num_str = issue_id

            # Validate it's a valid integer
            try:
                int(issue_num_str)
            except (ValueError, TypeError):
                logger.debug(
                    "pull_issue_invalid_id",
                    issue_id=issue_id,
                    reason="Cannot parse as integer",
                )
                return Err(
                    SyncError(
                        error_type=SyncErrorType.VALIDATION_ERROR,
                        message=f"Invalid issue ID format: {issue_id}",
                        suggested_fix="Ensure issue_id is a valid number",
                    )
                )

            # If we got here, the issue_id is valid
            # The actual pull work happens elsewhere in the sync pipeline
            return Ok(True)

        except Exception as e:
            logger.debug(
                "pull_issue_validation_failed",
                issue_id=issue_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            return Err(
                SyncError.from_exception(
                    e,
                    error_type=SyncErrorType.VALIDATION_ERROR,
                )
            )

    def _convert_sync_to_issue(self, issue_id: str, sync_issue: SyncIssue) -> "Issue":
        """Convert SyncIssue to local Issue object.

        Args:
            issue_id: Local issue ID
            sync_issue: SyncIssue with remote data

        Returns:
            Issue instance with converted data

        Raises:
            ValueError: If conversion fails
        """
        return self._helpers._convert_sync_to_issue(issue_id, sync_issue)

    def _convert_github_to_issue(
        self, issue_id: str, remote_data: dict[str, Any]
    ) -> "Issue":
        """Convert GitHub issue dict to local Issue object.

        Args:
            issue_id: Local issue ID
            remote_data: GitHub issue data from API

        Returns:
            Issue instance with converted data

        Raises:
            ValueError: If conversion fails
        """
        return self._helpers._convert_github_to_issue(issue_id, remote_data)

    def _parse_timestamp(self, timestamp_str: str | None) -> "datetime | None":
        """Parse ISO format timestamp string.

        Args:
            timestamp_str: ISO format timestamp (may have 'Z' suffix)

        Returns:
            datetime object or None if parsing fails
        """
        return self._helpers._parse_timestamp(timestamp_str)

    def get_conflict_resolution_options(self, conflict: SyncConflict) -> list[str]:
        """Get available resolution strategies for a conflict.

        Args:
            conflict: The SyncConflict to resolve

        Returns:
            List of resolution option codes (e.g., ['use_local', 'use_remote', 'merge'])
        """
        # GitHub backend supports the three basic strategies
        return ["use_local", "use_remote", "merge"]

    def resolve_conflict(self, conflict: SyncConflict, resolution: str) -> bool:
        """Resolve a sync conflict using specified strategy.

        Args:
            conflict: The SyncConflict to resolve
            resolution: The resolution strategy code ('use_local', 'use_remote', or 'merge')

        Returns:
            True if resolution succeeds, False otherwise.
        """
        from structlog import get_logger

        logger = get_logger()

        try:
            logger.debug(
                "github_resolve_conflict_started",
                issue_id=conflict.issue_id,
                resolution=resolution,
            )

            # For now, return True to indicate success
            # Full implementation will handle actual conflict resolution
            # when GitHub backend API is fully implemented

            logger.info(
                "github_resolve_conflict_completed",
                issue_id=conflict.issue_id,
                resolution=resolution,
            )
            return True

        except Exception as e:
            logger.warning(
                "github_resolve_conflict_failed",
                issue_id=conflict.issue_id,
                resolution=resolution,
                error=str(e),
            )
            return False

    def get_milestones(self) -> Result[dict[str, SyncMilestone], SyncError]:
        """Fetch all milestones from GitHub.

        Returns:
            Ok(dict) mapping milestone_number -> SyncMilestone objects on success
            Err(SyncError) with error details on failure
        """
        from roadmap.adapters.sync.backends.services.github_milestone_fetch_service import (
            GitHubMilestoneFetchService,
        )

        if not self.github_client:
            logger.warning("github_milestone_fetch_no_client")
            return Err(
                SyncError(
                    error_type=SyncErrorType.AUTHENTICATION_FAILED,
                    message="GitHub client not initialized - authenticate first",
                    entity_type="Milestone",
                    suggested_fix="Call authenticate() before get_milestones()",
                )
            )

        try:
            fetch_service = GitHubMilestoneFetchService(self.github_client, self.config)
            milestones = fetch_service.get_milestones(state="all")

            logger.info(
                "github_milestones_retrieved",
                count=len(milestones),
                owner=self.config.get("owner"),
                repo=self.config.get("repo"),
            )

            return Ok(milestones)

        except Exception as e:
            logger.error(
                "github_get_milestones_failed",
                error=str(e),
                error_type=type(e).__name__,
                owner=self.config.get("owner"),
                repo=self.config.get("repo"),
            )
            return Err(
                SyncError.from_exception(
                    e,
                    error_type=SyncErrorType.NETWORK_ERROR,
                    entity_type="Milestone",
                )
            )

    # --- Helper methods for pull/create matching and persistence ---
    def _find_matching_local_issue(
        self, title: str, github_issue_number: str | int | None
    ):
        """Find a matching local issue by GitHub number or by title.

        Accepts either numeric or string GitHub IDs; comparison is done
        by normalizing both sides to string.
        """
        return self._helpers._find_matching_local_issue(title, github_issue_number)

    def _apply_or_create_local_issue(
        self,
        issue_id: str,
        matching_local_issue,
        updates: dict,
        github_issue_number: str | int | None,
        remote_issue: SyncIssue | None = None,
    ) -> None:
        """Apply updates to an existing local issue or create a new one, and ensure linking/persistence.

        Args:
            issue_id: remote issue id (e.g. 'gh-123') used as fallback local id
            matching_local_issue: existing local Issue object or None
            updates: dict of fields to update on local issue
            github_issue_number: numeric GitHub issue number if available
            remote_issue: original SyncIssue object from GitHub (used when creating)
        """
        return self._helpers._apply_or_create_local_issue(
            issue_id, matching_local_issue, updates, github_issue_number, remote_issue
        )

    def get_projects(self) -> Result[dict[str, SyncProject], SyncError]:
        """Fetch all projects from GitHub.

        Currently returns empty dict as project fetching is not yet implemented.
        GitHub uses classic Project Boards and newer Projects (beta).
        """
        # TODO: Implement GitHub Projects API integration
        return Ok({})

    def delete_issues(self, issue_numbers: list[int]) -> int:
        """Delete GitHub issues via GraphQL batch mutation.

        Args:
            issue_numbers: GitHub issue numbers to delete

        Returns:
            Count of successfully deleted issues
        """
        if not issue_numbers:
            return 0

        token = self.config.get("token")
        owner = self.config.get("owner")
        repo = self.config.get("repo")

        if not token or not owner or not repo:
            logger.warning(
                "github_delete_issues_missing_config",
                has_token=bool(token),
                has_owner=bool(owner),
                has_repo=bool(repo),
            )
            return 0

        start_time = time.time()
        logger.info(
            "github_delete_issues_starting",
            requested_count=len(issue_numbers),
        )
        deleted_count = 0
        skipped_pr_numbers: list[int] = []
        lookup_batch_size = 20
        delete_batch_size = 5
        inter_batch_delay_seconds = 0.2
        rate_limit_delay_seconds = 1.0

        for i in range(0, len(issue_numbers), lookup_batch_size):
            batch = issue_numbers[i : i + lookup_batch_size]
            node_ids, skipped_prs = self._resolve_issue_node_ids(
                batch, owner, repo, token
            )
            if skipped_prs:
                skipped_pr_numbers.extend(skipped_prs)
            if not node_ids:
                logger.warning(
                    "github_delete_issues_batch_skipped",
                    batch_size=len(batch),
                    reason="node_ids_empty",
                )
                continue

            node_items = list(node_ids.items())
            for j in range(0, len(node_items), delete_batch_size):
                delete_chunk = dict(node_items[j : j + delete_batch_size])
                batch_deleted, rate_limited, failed_numbers = self._delete_issues_batch(
                    delete_chunk,
                    token,
                )
                deleted_count += batch_deleted
                logger.info(
                    "github_delete_issues_batch_complete",
                    batch_size=len(delete_chunk),
                    deleted_count=batch_deleted,
                )

                if failed_numbers and rate_limited:
                    logger.warning(
                        "github_delete_issues_retrying_failed",
                        failed_count=len(failed_numbers),
                        delay_seconds=rate_limit_delay_seconds,
                    )
                    time.sleep(rate_limit_delay_seconds)
                    retry_items = {
                        number: node_ids[number]
                        for number in failed_numbers
                        if number in node_ids
                    }
                    if retry_items:
                        retry_deleted, _, _ = self._delete_issues_batch(
                            retry_items,
                            token,
                        )
                        deleted_count += retry_deleted

                time.sleep(inter_batch_delay_seconds)
                if rate_limited:
                    logger.warning(
                        "github_delete_issues_rate_limited",
                        delay_seconds=rate_limit_delay_seconds,
                    )
                    time.sleep(rate_limit_delay_seconds)

        duration = time.time() - start_time
        failed_count = max(
            0, len(issue_numbers) - deleted_count - len(skipped_pr_numbers)
        )
        if skipped_pr_numbers:
            logger.info(
                "github_delete_issues_prs_skipped",
                skipped_count=len(skipped_pr_numbers),
                skipped_numbers=skipped_pr_numbers[:20],
            )

        logger.info(
            "github_delete_issues_completed",
            requested_count=len(issue_numbers),
            deleted_count=deleted_count,
            failed_count=failed_count,
            skipped_pr_count=len(skipped_pr_numbers),
            duration_seconds=round(duration, 3),
        )

        return deleted_count

    def _resolve_issue_node_ids(
        self,
        issue_numbers: list[int],
        owner: str,
        repo: str,
        token: str,
    ) -> tuple[dict[int, str], list[int]]:
        """Resolve GitHub issue numbers to GraphQL node IDs.

        Returns tuple of (node_ids, skipped_pr_numbers).
        """
        query_parts = []
        for idx, number in enumerate(issue_numbers):
            query_parts.append(
                """
                issue{idx}: repository(owner: \"{owner}\", name: \"{repo}\") {{
                  issueOrPullRequest(number: {number}) {{
                    __typename
                    ... on Issue {{ id number }}
                    ... on PullRequest {{ id number }}
                  }}
                }}
                """.format(idx=idx, owner=owner, repo=repo, number=number)
            )

        query = "query {" + "\n".join(query_parts) + "\n}"
        response = self._post_graphql_with_backoff(
            query,
            token,
            operation="resolve_issue_node_ids",
        )
        if response is None:
            return {}, []

        data = response.get("data") or {}
        node_ids: dict[int, str] = {}
        skipped_pr_numbers: list[int] = []
        for idx, number in enumerate(issue_numbers):
            key = f"issue{idx}"
            issue_data = data.get(key, {}).get("issueOrPullRequest")
            if issue_data and issue_data.get("__typename") == "Issue":
                if issue_data.get("id"):
                    node_ids[number] = issue_data["id"]
                else:
                    logger.warning(
                        "github_issue_node_id_missing",
                        issue_number=number,
                    )
            elif issue_data and issue_data.get("__typename") == "PullRequest":
                logger.warning(
                    "github_issue_node_id_skipped_pull_request",
                    issue_number=number,
                )
                skipped_pr_numbers.append(number)
            else:
                logger.warning(
                    "github_issue_node_id_missing",
                    issue_number=number,
                )

        logger.info(
            "github_issue_node_ids_resolved",
            requested_count=len(issue_numbers),
            resolved_count=len(node_ids),
        )

        return node_ids, skipped_pr_numbers

    def _delete_issues_batch(
        self, node_ids: dict[int, str], token: str
    ) -> tuple[int, bool, list[int]]:
        """Delete issues by node ID via GraphQL mutation."""
        mutation_parts = []
        for idx, (number, node_id) in enumerate(node_ids.items()):
            mutation_parts.append(
                """
                delete{idx}: deleteIssue(input: {{issueId: \"{node_id}\"}}) {{
                  clientMutationId
                }}
                """.format(idx=idx, node_id=node_id)
            )

        mutation = "mutation {" + "\n".join(mutation_parts) + "\n}"
        response = self._post_graphql_with_backoff(
            mutation,
            token,
            operation="delete_issues_batch",
        )
        if response is None:
            return 0, False, list(node_ids.keys())

        error_types = self._extract_graphql_error_types(response)
        error_details = self._extract_graphql_error_details(response)
        rate_limited = "RESOURCE_LIMITS_EXCEEDED" in error_types

        data = response.get("data") or {}
        deleted = 0
        failed_numbers: list[int] = []
        for idx, number in enumerate(node_ids.keys()):
            key = f"delete{idx}"
            if data.get(key) is not None:
                deleted += 1
            else:
                logger.warning(
                    "github_issue_delete_failed",
                    issue_number=number,
                )
                failed_numbers.append(number)

        logger.info(
            "github_delete_batch_summary",
            attempted_count=len(node_ids),
            deleted_count=deleted,
        )

        if error_details:
            logger.warning(
                "github_delete_batch_errors",
                error_types=sorted(error_types),
                error_count=len(error_details),
                error_samples=error_details[:5],
                failed_numbers=failed_numbers[:10],
            )

        return deleted, rate_limited, failed_numbers

    def _extract_graphql_error_types(self, payload: dict[str, Any]) -> set[str]:
        """Extract error types from a GraphQL payload."""
        errors = payload.get("errors") or []
        return {
            error_type
            for error in errors
            if isinstance(error, dict)
            and isinstance((error_type := error.get("type")), str)
        }

    def _extract_graphql_error_details(
        self, payload: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Extract error details from a GraphQL payload."""
        errors = payload.get("errors") or []
        details: list[dict[str, Any]] = []
        for error in errors:
            if not isinstance(error, dict):
                continue
            details.append(
                {
                    "type": error.get("type"),
                    "path": error.get("path"),
                    "message": error.get("message"),
                }
            )
        return details

    def _post_graphql_with_backoff(
        self,
        query: str,
        token: str,
        operation: str,
        max_attempts: int = 3,
        delay: float = 2.0,
        backoff: float = 2.0,
    ) -> dict[str, Any] | None:
        """Post GraphQL with backoff when resource limits are hit."""
        attempt = 0
        current_delay = delay
        payload: dict[str, Any] | None = None

        while attempt < max_attempts:
            attempt += 1
            payload = self._post_graphql(query, token)
            if payload is None:
                if attempt < max_attempts:
                    logger.warning(
                        "github_graphql_retry_request_failed",
                        operation=operation,
                        attempt=attempt,
                        delay_seconds=current_delay,
                    )
                    time.sleep(current_delay)
                    current_delay *= backoff
                    continue
                return None

            error_types = self._extract_graphql_error_types(payload)
            if "RESOURCE_LIMITS_EXCEEDED" in error_types and attempt < max_attempts:
                logger.warning(
                    "github_graphql_rate_limited",
                    operation=operation,
                    attempt=attempt,
                    delay_seconds=current_delay,
                )
                time.sleep(current_delay)
                current_delay *= backoff
                continue

            return payload

        return payload

    def _post_graphql(self, query: str, token: str) -> dict[str, Any] | None:
        """Post a GraphQL query to GitHub and return JSON data."""
        import requests

        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github.v4+json",
            "User-Agent": "roadmap-cli/1.0",
        }
        try:
            response = requests.post(
                "https://api.github.com/graphql",
                json={"query": query},
                headers=headers,
                timeout=30,
            )
            response.raise_for_status()
            payload = response.json()
            if payload.get("errors"):
                logger.warning(
                    "github_graphql_errors",
                    errors=payload.get("errors"),
                )
            return payload
        except requests.RequestException as e:
            logger.warning(
                "github_graphql_request_failed",
                error=str(e),
                severity="operational",
            )
            return None

    @staticmethod
    def _dict_to_sync_issue(issue_dict: dict[str, Any]) -> SyncIssue:
        """Convert a raw GitHub API issue dict to SyncIssue.

        Args:
            issue_dict: Dict with issue data from GitHub API

        Returns:
            SyncIssue instance
        """
        # Delegate to helpers for consistent conversion
        helpers = GitHubBackendHelpers(core=None)
        return helpers._dict_to_sync_issue(issue_dict)
