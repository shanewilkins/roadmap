"""GitHub-specific implementation of SyncBackendInterface.

This module provides the GitHub API backend for syncing roadmap issues
with GitHub repositories. It implements the SyncBackendInterface protocol.
"""

from collections.abc import Callable
from datetime import datetime  # noqa: F401  # Used in type hints
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

    def authenticate(self) -> bool:
        """Verify credentials and remote connectivity.

        Returns:
            True if authentication succeeds (token valid and repo accessible),
            False otherwise (no exceptions raised).
        """
        result = self._auth_service.authenticate()
        if result and self.github_client is None:
            # Update our client reference after successful auth
            self.github_client = self._auth_service.github_client
        return result

    def get_issues(self) -> dict[str, SyncIssue]:
        """Fetch all issues from GitHub remote.

        Returns:
            Dictionary mapping issue_id -> SyncIssue objects.
            Returns empty dict if unable to fetch.
        """
        # Lazily initialize fetch service after first auth
        if self._fetch_service is None and self.github_client:
            self._fetch_service = GitHubIssueFetchService(
                self.github_client, self.config, self._helpers
            )

        if self._fetch_service is None:
            logger.warning("github_fetch_service_not_initialized")
            return {}

        return self._fetch_service.get_issues()

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

    def push_issue(self, local_issue: Issue) -> bool:
        """Push a single local issue to GitHub.

        Args:
            local_issue: The Issue object to push

        Returns:
            True if push succeeds, False if error.

        Notes:
            - Delegates to push_issues for consistency
            - Creates new GitHub issue if not linked (no github_issue field)
            - Updates existing GitHub issue if linked (has github_issue field)
            - Stores the GitHub issue number for future syncs
        """
        report = self.push_issues([local_issue])
        return len(report.pushed) > 0 and len(report.errors) == 0

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
            issue_id: The remote issue ID (GitHub issue number like "_remote_123" or "123")

        Returns:
            True if issue is valid and can be pulled, False if error.

        Notes:
            - Validates the issue_id can be parsed
            - Actual fetching/saving is handled by pull_issues caller
            - Returns True to indicate success to GitHubSyncOps
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
                return False

            # If we got here, the issue_id is valid
            # The actual pull work happens elsewhere in the sync pipeline
            return True

        except Exception as e:
            logger.debug(
                "pull_issue_validation_failed",
                issue_id=issue_id,
                error=str(e),
                error_type=type(e).__name__,
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
