"""GitHub-specific implementation of SyncBackendInterface.

This module provides the GitHub API backend for syncing roadmap issues
with GitHub repositories. It implements the SyncBackendInterface protocol.
"""

from collections.abc import Callable
from datetime import datetime
from typing import Any, TypeVar

from structlog import get_logger

from roadmap.adapters.sync.backends.github_backend_helpers import GitHubBackendHelpers
from roadmap.adapters.sync.backends.github_client import GitHubClientWrapper
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
from roadmap.core.services.github_conflict_detector import GitHubConflictDetector

# Backwards compatibility: some tests and call sites patch or reference
# `GitHubIssueClient` on this module. Keep a module-level name pointing to
# the original implementation when available so `unittest.mock.patch` targets
# remain valid.
try:
    # prefer importing the original client class when available
    from roadmap.core.services.github_issue_client import (
        GitHubIssueClient,  # type: ignore
    )
except Exception:
    GitHubIssueClient = None  # type: ignore
from roadmap.core.services.sync_metadata_service import SyncMetadataService
from roadmap.infrastructure.core import RoadmapCore

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
        self.github_client = self._safe_init(
            lambda: GitHubClientWrapper(token) if token else None,
            "GitHubClientWrapper",
        )

        # Initialize metadata service if available
        self.metadata_service = self._safe_init(
            lambda: SyncMetadataService(core),
            "SyncMetadataService",
        )

        # Initialize conflict detector if available
        self.conflict_detector = None
        if hasattr(core, "github_service") and core.github_service is not None:
            self.conflict_detector = self._safe_init(
                lambda: GitHubConflictDetector(core.github_service),
                "GitHubConflictDetector",
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

    def authenticate(self) -> bool:
        """Verify credentials and remote connectivity.

        Returns:
            True if authentication succeeds (token valid and repo accessible),
            False otherwise (no exceptions raised).
        """
        try:
            token = self.config.get("token")
            if not token:
                # No token - auth fails
                logger.debug("github_auth_no_token")
                return False

            # Initialize client if not already done
            if self.github_client is None:
                try:
                    self.github_client = GitHubClientWrapper(token)
                except (ImportError, TypeError) as e:
                    logger.error(
                        "github_client_init_failed",
                        error_type=type(e).__name__,
                        error=str(e),
                        suggested_action="check_dependencies",
                    )
                    return False
                except Exception as e:
                    logger.error(
                        "github_client_init_failed",
                        error_type=type(e).__name__,
                        error=str(e),
                        error_classification="initialization_error",
                    )
                    return False

            owner = self.config.get("owner")
            repo = self.config.get("repo")

            # Type assertions (config is validated in __init__)
            assert isinstance(owner, str), "owner must be a string"
            assert isinstance(repo, str), "repo must be a string"

            # Try to fetch a single issue to validate token and repo access
            # We use a dummy issue number that likely doesn't exist
            # If we get a 401/403, auth failed. If we get 404, auth succeeded.
            logger.info("github_auth_attempting", owner=owner, repo=repo)
            try:
                self.github_client.fetch_issue(owner, repo, 1)
                # Even if issue 1 doesn't exist, we got through auth
                logger.info("github_auth_success", owner=owner, repo=repo)
                return True
            except Exception as e:
                # Check if it's an auth error
                error_msg = str(e).lower()
                if (
                    "401" in error_msg
                    or "403" in error_msg
                    or "unauthorized" in error_msg
                ):
                    logger.warning(
                        "github_auth_failed_unauthorized",
                        owner=owner,
                        repo=repo,
                        error=str(e),
                    )
                    return False
                # Other errors (like 404 for issue not found) mean auth succeeded
                logger.info(
                    "github_auth_success_with_error",
                    owner=owner,
                    repo=repo,
                    error=str(e),
                )
                return True

        except Exception as e:
            logger.error(
                "github_auth_unexpected_error",
                error_type=type(e).__name__,
                error=str(e),
                error_classification="authentication_error",
                suggested_action="check_network",
            )
            return False

    def get_issues(self) -> dict[str, SyncIssue]:
        """Fetch all issues from GitHub remote.

        Returns:
            Dictionary mapping issue_id -> issue_data (as dict).
            Returns empty dict if unable to fetch.

        Notes:
            - Fetches all issues from the GitHub repository
            - Returns issue data in GitHub API format
        """
        from structlog import get_logger

        logger = get_logger()

        try:
            owner = self.config.get("owner")
            repo = self.config.get("repo")
            token = self.config.get("token")

            if not owner or not repo or not token:
                return {}

            logger.debug("github_get_issues_started", owner=owner, repo=repo)

            # Fetch all issues using GitHub Client
            issues_data = {}

            try:
                from roadmap.adapters.github.github import GitHubClient

                client = GitHubClient(token=token, owner=owner, repo=repo)

                # Fetch issues with pagination
                page = 1
                per_page = 100

                while True:
                    url = f"https://api.github.com/repos/{owner}/{repo}/issues"
                    params = {
                        "state": "all",  # Get both open and closed issues
                        "per_page": per_page,
                        "page": page,
                        "sort": "updated",
                        "direction": "desc",
                    }

                    response = client.session.get(url, params=params)
                    response.raise_for_status()

                    issues = response.json()
                    if not issues:
                        break

                    for issue in issues:
                        # Use GitHub issue number as the ID (with gh- prefix)
                        issue_id = f"gh-{issue.get('number')}"

                        # Extract relevant fields
                        issues_data[issue_id] = {
                            "id": issue_id,
                            "number": issue.get("number"),
                            "title": issue.get("title", ""),
                            "body": issue.get("body", ""),
                            "state": issue.get("state", "open"),  # 'open' or 'closed'
                            "labels": [
                                label.get("name") for label in issue.get("labels", [])
                            ]
                            if issue.get("labels")
                            else [],
                            "assignees": [
                                assignee.get("login")
                                for assignee in issue.get("assignees", [])
                            ]
                            if issue.get("assignees")
                            else [],
                            "assignee": issue.get("assignee", {}).get("login")
                            if issue.get("assignee")
                            else None,
                            "milestone": issue.get("milestone", {}).get("title")
                            if issue.get("milestone")
                            else None,
                            "url": issue.get("html_url", ""),
                            "created_at": issue.get("created_at"),
                            "updated_at": issue.get("updated_at"),
                        }

                    page += 1

                    # Continue fetching all pages (no limit for production)
                    # Pagination ensures we get all issues regardless of count

                logger.info(
                    "github_get_issues_completed",
                    count=len(issues_data),
                    owner=owner,
                    repo=repo,
                )
                # Convert dict representations to SyncIssue objects
                return {
                    issue_id: self._dict_to_sync_issue(issue_dict)
                    for issue_id, issue_dict in issues_data.items()
                }

            except (ConnectionError, TimeoutError) as e:
                logger.error(
                    "github_api_fetch_failed",
                    operation="fetch_issues",
                    owner=owner,
                    repo=repo,
                    error_type=type(e).__name__,
                    error=str(e),
                    is_recoverable=True,
                    suggested_action="retry_after_delay",
                )
                return {}
            except Exception as e:
                logger.error(
                    "github_api_fetch_failed",
                    operation="fetch_issues",
                    owner=owner,
                    repo=repo,
                    error_type=type(e).__name__,
                    error=str(e),
                    is_recoverable=False,
                    suggested_action="check_configuration",
                )
                return {}

        except Exception as e:
            logger.error(
                "github_get_issues_failed",
                error_type=type(e).__name__,
                error=str(e),
                is_recoverable=False,
                suggested_action="check_configuration",
            )
            return {}

    def push_issue(self, local_issue: Issue) -> bool:
        """Push a single local issue to GitHub.

        Args:
            local_issue: The Issue object to push

        Returns:
            True if push succeeds, False if error.

        Notes:
            - Creates new GitHub issue if not linked (no github_issue field)
            - Updates existing GitHub issue if linked (has github_issue field)
            - Stores the GitHub issue number for future syncs
        """
        from structlog import get_logger

        from roadmap.adapters.sync.services import (
            IssuePersistenceService,
            IssueStateService,
            SyncLinkingService,
        )

        logger = get_logger()

        try:
            owner = self.config.get("owner")
            repo = self.config.get("repo")
            token = self.config.get("token")

            if not owner or not repo or not token:
                return False

            logger.debug("github_push_issue_started", issue_id=local_issue.id)

            from roadmap.adapters.github.github import GitHubClient

            client = GitHubClient(token=token, owner=owner, repo=repo)

            # Check if this issue is already linked to a GitHub issue
            github_issue_number = IssuePersistenceService.get_github_issue_number(
                local_issue
            )

            if github_issue_number:
                # Update existing GitHub issue
                github_issue_number = int(github_issue_number)
                url = f"https://api.github.com/repos/{owner}/{repo}/issues/{github_issue_number}"
                payload = IssueStateService.issue_to_push_payload(local_issue)

                response = client.session.patch(url, json=payload)
                response.raise_for_status()

                # Link in database for fast lookups during future syncs
                SyncLinkingService.link_issue_in_database(
                    self.remote_link_repo,
                    local_issue.id,
                    "github",
                    github_issue_number,
                )

                logger.info(
                    "github_push_issue_updated",
                    issue_id=local_issue.id,
                    github_number=github_issue_number,
                )
                return True

            else:
                # Create new GitHub issue
                # First, check if an issue with the same title already exists on GitHub
                all_remote_issues = self.get_issues()
                duplicate_issue = None

                for remote_issue in all_remote_issues.values():
                    if remote_issue.title.lower() == local_issue.title.lower():
                        duplicate_issue = remote_issue
                        logger.warning(
                            "github_push_issue_found_duplicate",
                            issue_id=local_issue.id,
                            github_number=remote_issue.backend_id,
                            title=local_issue.title,
                        )
                        break

                # If we found a duplicate, link it instead of creating a new one
                if duplicate_issue and duplicate_issue.backend_id:
                    github_issue_number = duplicate_issue.backend_id
                    SyncLinkingService.link_issue_in_database(
                        self.remote_link_repo,
                        local_issue.id,
                        "github",
                        github_issue_number,
                    )
                    logger.info(
                        "github_duplicate_issue_linked",
                        issue_id=local_issue.id,
                        github_number=github_issue_number,
                    )
                    return True

                # Create new GitHub issue
                url = f"https://api.github.com/repos/{owner}/{repo}/issues"
                payload = IssueStateService.issue_to_push_payload(local_issue)

                response = client.session.post(url, json=payload)
                response.raise_for_status()

                github_response = response.json()
                github_issue_number = github_response.get("number")

                # Link in database for fast lookups during future syncs
                if github_issue_number:
                    SyncLinkingService.link_issue_in_database(
                        self.remote_link_repo,
                        local_issue.id,
                        "github",
                        github_issue_number,
                    )

                logger.info(
                    "github_push_issue_created",
                    issue_id=local_issue.id,
                    github_number=github_issue_number,
                )
                return True

        except (ConnectionError, TimeoutError) as e:
            logger.warning(
                "github_push_issue_failed",
                issue_id=local_issue.id,
                error_type=type(e).__name__,
                error=str(e),
                is_recoverable=True,
                suggested_action="retry_after_delay",
            )
            return False
        except Exception as e:
            logger.warning(
                "github_push_issue_failed",
                issue_id=local_issue.id,
                error_type=type(e).__name__,
                error=str(e),
                error_classification="sync_error",
            )
            return False

    def push_issues(self, local_issues: list[Issue]) -> SyncReport:
        """Push multiple local issues to GitHub.

        Args:
            local_issues: List of Issue objects to push

        Returns:
            SyncReport with pushed, conflicts, and errors.
        """
        # Delegate orchestration to helper class
        from roadmap.adapters.sync.backends.github_sync_ops import GitHubSyncOps

        ops = GitHubSyncOps(self)
        return ops.push_issues(local_issues)

    def pull_issues(self, issue_ids: list[str]) -> SyncReport:
        """Pull specified remote GitHub issues to local.

        Args:
            issue_ids: List of remote issue IDs to pull

        Returns:
            SyncReport with pulled, conflicts, and errors.

        Notes:
            - Each ID should correspond to a remote issue
            - Updates or creates local files as needed
            - Uses parallel execution with thread pool for performance
        """
        from roadmap.adapters.sync.backends.github_sync_ops import GitHubSyncOps

        ops = GitHubSyncOps(self)
        return ops.pull_issues(issue_ids)

    def pull_issue(self, issue_id: str) -> bool:
        """Pull a single remote GitHub issue to local.

        Args:
            issue_id: The remote issue ID to pull

        Returns:
            True if pull succeeds, False if error.

        Notes:
            - Fetches the remote issue and updates local
            - Should not raise exceptions; return False on failure
        """
        from structlog import get_logger

        from roadmap.adapters.sync.services import (
            IssueStateService,
        )

        logger = get_logger()

        try:
            # Fetch the remote issue by ID
            remote_issues = self.get_issues()
            remote_issue = remote_issues.get(issue_id)

            if not remote_issue:
                logger.warning("pull_issue_not_found_remote", issue_id=issue_id)
                return False

            title = remote_issue.title or ""

            if not issue_id or not title:
                logger.warning(
                    "pull_issue_missing_id_or_title", remote_issue=remote_issue
                )
                return False
            logger.debug("github_pull_issue_started", issue_id=issue_id)

            # Convert remote SyncIssue to local Issue object
            github_issue_number = remote_issue.backend_id

            matching_local_issue = self._find_matching_local_issue(
                title, github_issue_number
            )

            # Convert to local Issue and prepare updates
            # Normalize status from GitHub format to local Status enum
            normalized_status = IssueStateService.normalize_status(remote_issue.status)

            updates = {
                "title": remote_issue.title,
                "status": normalized_status,
                "assignee": remote_issue.assignee,
                "milestone": remote_issue.milestone,
                "content": remote_issue.headline or "",  # SyncIssue.headline → content
            }

            # Update/create locally and link
            self._apply_or_create_local_issue(
                issue_id,
                matching_local_issue,
                updates,
                github_issue_number,
                remote_issue,
            )

            logger.info("github_pull_issue_completed", issue_id=issue_id)
            return True

        except Exception as e:
            logger.warning(
                "github_pull_issue_failed",
                issue_id=issue_id,
                error=str(e),
                exc_info=True,
            )
            return False

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

    def get_milestones(self) -> dict[str, SyncMilestone]:
        """Fetch all milestones from GitHub."""
        # TODO: Implement full milestone fetching from GitHub API
        return {}

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

    def get_projects(self) -> dict[str, SyncProject]:
        """Fetch all projects from GitHub.

        Currently returns empty dict as project fetching is not yet implemented.
        GitHub uses classic Project Boards and newer Projects (beta).
        """
        # TODO: Implement GitHub Projects API integration
        return {}

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
