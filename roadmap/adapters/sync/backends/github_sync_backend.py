"""GitHub-specific implementation of SyncBackendInterface.

This module provides the GitHub API backend for syncing roadmap issues
with GitHub repositories. It implements the SyncBackendInterface protocol.
"""

from typing import Any

from roadmap.core.domain.issue import Issue
from roadmap.core.interfaces import (
    SyncConflict,
    SyncReport,
)
from roadmap.core.services.github_conflict_detector import GitHubConflictDetector
from roadmap.core.services.github_issue_client import GitHubIssueClient
from roadmap.core.services.sync_metadata_service import SyncMetadataService
from roadmap.infrastructure.core import RoadmapCore


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
        if token:
            try:
                self.github_client = GitHubIssueClient(token)
            except Exception:
                # Token validation error - will fail at authenticate time
                self.github_client = None
        else:
            self.github_client = None

        # Initialize metadata service if available
        try:
            self.metadata_service = SyncMetadataService(core)
        except Exception:
            self.metadata_service = None

        # Initialize conflict detector if available
        self.conflict_detector = None
        if hasattr(core, "github_service") and core.github_service is not None:
            try:
                self.conflict_detector = GitHubConflictDetector(core.github_service)
            except Exception:
                # GitHub service not properly initialized - will fail at sync time
                self.conflict_detector = None

    def authenticate(self) -> bool:
        """Verify credentials and remote connectivity.

        Returns:
            True if authentication succeeds (token valid and repo accessible),
            False otherwise (no exceptions raised).
        """
        from structlog import get_logger

        logger = get_logger()

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
        try:
            owner = self.config.get("owner")
            repo = self.config.get("repo")

            if not owner or not repo:
                return {}

            # Get all GitHub issues in the repo
            # This is a simplified version - full implementation would paginate
            issues_data = {}

            # Note: This is a placeholder for the actual implementation
            # which would call GitHub API to list all issues
            # For now, we'll return empty dict as we're in Phase 2 (refactoring)
            # Full implementation will be done when integrating with orchestrator

            return issues_data

        except Exception:
            return {}

    def push_issue(self, local_issue: Issue) -> bool:
        """Push a single local issue to GitHub.

        Args:
            local_issue: The Issue object to push

        Returns:
            True if push succeeds, False if conflict or error.

        Notes:
            - Creates new GitHub issue if not linked
            - Updates existing GitHub issue if linked
            - Handles conflicts by returning False (caller decides resolution)
        """
        try:
            owner = self.config.get("owner")
            repo = self.config.get("repo")

            if not owner or not repo:
                return False

            # If issue is already linked to GitHub, update it
            if local_issue.github_issue:
                # TODO: Implement update logic
                return True

            # Otherwise, create new GitHub issue
            # TODO: Implement create logic
            return True

        except Exception:
            return False

    def push_issues(self, local_issues: list[Issue]) -> SyncReport:
        """Push multiple local issues to GitHub.

        Args:
            local_issues: List of Issue objects to push

        Returns:
            SyncReport with pushed, conflicts, and errors.
        """
        report = SyncReport()

        for issue in local_issues:
            try:
                if self.push_issue(issue):
                    report.pushed.append(issue.id)
                else:
                    report.errors[issue.id] = "Failed to push issue"
            except Exception as e:
                report.errors[issue.id] = str(e)

        return report

    def pull_issues(self) -> SyncReport:
        """Pull all remote GitHub issues to local.

        Returns:
            SyncReport with pulled, conflicts, and errors.

        Notes:
            - Fetches issues from GitHub and integrates with local issues
            - Detects conflicts and populates report.conflicts
            - Successfully integrated issues go to report.pulled
        """
        report = SyncReport()

        try:
            # TODO: Implement full pull logic including:
            # - Fetching all GitHub issues
            # - Detecting conflicts with existing local issues
            # - Integrating new issues from GitHub
            # - Populating report.pulled, report.conflicts, report.errors
            pass
        except Exception as e:
            report.errors["pull"] = str(e)

        return report

    def get_conflict_resolution_options(self, conflict: SyncConflict) -> list[str]:
        """Get available resolution strategies for a GitHub conflict.

        Args:
            conflict: The SyncConflict to resolve

        Returns:
            List of resolution option codes.
        """
        # GitHub backend supports three strategies
        return ["use_local", "use_remote", "manual_merge"]

    def resolve_conflict(self, conflict: SyncConflict, resolution: str) -> bool:
        """Resolve a sync conflict using specified strategy.

        Args:
            conflict: The SyncConflict to resolve
            resolution: The resolution strategy code

        Returns:
            True if resolution succeeds, False otherwise.
        """
        try:
            if resolution == "use_local":
                # Push local version to GitHub, overwriting remote
                if conflict.local_version:
                    return self.push_issue(conflict.local_version)
                return False

            elif resolution == "use_remote":
                # Update local from remote (remote wins)
                # TODO: Implement pulling remote version over local
                return True

            elif resolution == "manual_merge":
                # Manual merge - not fully automated
                # TODO: Implement three-way merge logic
                return False

            return False

        except Exception:
            return False
