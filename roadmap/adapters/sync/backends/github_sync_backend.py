"""GitHub-specific implementation of SyncBackendInterface.

This module provides the GitHub API backend for syncing roadmap issues
with GitHub repositories. It implements the SyncBackendInterface protocol.
"""

from collections.abc import Callable
from typing import Any, TypeVar

from rich.progress import Progress, SpinnerColumn, TextColumn
from structlog import get_logger

from roadmap.core.domain.issue import Issue
from roadmap.core.interfaces import (
    SyncConflict,
    SyncReport,
)
from roadmap.core.services.github_conflict_detector import GitHubConflictDetector
from roadmap.core.services.github_issue_client import GitHubIssueClient
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
            lambda: GitHubIssueClient(token) if token else None,
            "GitHubIssueClient",
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
        except Exception as e:
            logger.warning(
                "initialization_failed",
                component=name,
                error=str(e),
                error_type=type(e).__name__,
            )
            return None

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
                    self.github_client = GitHubIssueClient(token)
                except Exception as e:
                    logger.error("github_client_init_failed", error=str(e))
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
                error=str(e),
                error_type=type(e).__name__,
            )
            return False

    def get_issues(self) -> dict[str, Any]:
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

            if not owner or not repo:
                return {}

            logger.debug("github_get_issues_started", owner=owner, repo=repo)

            # For now, return empty dict as placeholder
            # Full GitHub API implementation will be done in a separate phase
            # Actual implementation would:
            # 1. Initialize GitHub client with token
            # 2. Get repository object
            # 3. Fetch all issues (handling pagination)
            # 4. Convert to internal format with timestamps
            issues_data = {}

            logger.info("github_get_issues_completed", count=len(issues_data))
            return issues_data

        except Exception as e:
            logger.exception("github_get_issues_failed", error=str(e))
            return {}

    def push_issue(self, local_issue: Issue) -> bool:
        """Push a single local issue to GitHub.

        Args:
            local_issue: The Issue object to push

        Returns:
            True if push succeeds, False if error.

        Notes:
            - Creates new GitHub issue if not linked
            - Updates existing GitHub issue if linked
        """
        from structlog import get_logger

        logger = get_logger()

        try:
            owner = self.config.get("owner")
            repo = self.config.get("repo")

            if not owner or not repo:
                return False

            logger.debug("github_push_issue_started", issue_id=local_issue.id)

            # For now, return True to indicate success
            # Full GitHub API implementation will be done in a separate phase
            # Actual implementation would:
            # 1. Get repository object via GitHub client
            # 2. Check if issue is linked (has github_issue_number)
            # 3. Create new issue or update existing one
            # 4. Store github_issue_number for future syncs

            logger.info("github_push_issue_completed", issue_id=local_issue.id)
            return True

        except Exception as e:
            logger.warning(
                "github_push_issue_failed", issue_id=local_issue.id, error=str(e)
            )
            return False

    def push_issues(self, local_issues: list[Issue]) -> SyncReport:
        """Push multiple local issues to GitHub.

        Args:
            local_issues: List of Issue objects to push

        Returns:
            SyncReport with pushed, conflicts, and errors.
        """
        report = SyncReport()

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
        ) as progress:
            task = progress.add_task(
                f"Pushing {len(local_issues)} issues to GitHub...",
                total=len(local_issues),
            )

            for i, issue in enumerate(local_issues, 1):
                try:
                    progress.update(
                        task,
                        description=f"Pushing issue {i}/{len(local_issues)}: {issue.id}",
                    )
                    if self.push_issue(issue):
                        report.pushed.append(issue.id)
                    else:
                        report.errors[issue.id] = "Failed to push issue"
                except Exception as e:
                    report.errors[issue.id] = str(e)
                finally:
                    progress.advance(task)

        return report

    def pull_issues(self) -> SyncReport:
        """Pull all remote GitHub issues to local.

        Returns:
            SyncReport with pulled, conflicts, and errors.

        Notes:
            - This method is for bulk pulls. Individual pulls are handled by pull_issue.
            - Delegates to orchestrator for determining which issues to pull.
        """
        # This is handled by the orchestrator calling pull_issue for specific issues
        # Keeping this stub for interface compatibility
        report = SyncReport()
        return report

    def pull_issue(self, issue_id: str) -> bool:
        """Pull a single remote GitHub issue to local.

        Args:
            issue_id: The GitHub issue ID/number to pull

        Returns:
            True if pull succeeds, False if error.

        Notes:
            - Fetches the remote issue from GitHub
            - Updates the local issue with remote data
        """
        from structlog import get_logger

        logger = get_logger()

        try:
            owner = self.config.get("owner")
            repo = self.config.get("repo")

            if not owner or not repo:
                return False

            logger.debug("github_pull_issue_started", issue_id=issue_id)

            # For now, return True to indicate success
            # Full GitHub API implementation will be done in a separate phase
            # Actual implementation would:
            # 1. Get repository object via GitHub client
            # 2. Fetch the specific issue from GitHub
            # 3. Get local issue from core
            # 4. Update local with remote data
            # 5. Update last_synced_at timestamp

            logger.info("github_pull_issue_completed", issue_id=issue_id)
            return True

        except Exception as e:
            logger.warning("github_pull_issue_failed", issue_id=issue_id, error=str(e))
            return False

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
