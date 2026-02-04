"""GitHub issue client service for roadmap application.

This module handles fetching and syncing GitHub issues with internal roadmap issues.
It provides a simple interface for GitHub issue operations without requiring a
GitHub repository to be configured.
"""

import os
from typing import TYPE_CHECKING, Any

from roadmap.adapters.github.handlers.base import GitHubAPIError
from roadmap.common.logging import get_logger
from roadmap.common.logging.error_logging import (
    log_external_service_error,
    log_validation_error,
)
from roadmap.common.observability.instrumentation import traced
from roadmap.infrastructure.github_gateway import GitHubGateway

if TYPE_CHECKING:
    from roadmap.core.interfaces import GitHubBackendInterface  # noqa: F401

logger = get_logger(__name__)


class GitHubIssueClient:
    """Client for fetching and managing GitHub issues.

    This client allows operations on GitHub issues without requiring
    owner/repo configuration upfront. Configuration can be provided
    per-request or via environment variables.
    """

    def __init__(
        self,
        token: str | None = None,
        github_backend: "GitHubBackendInterface | None" = None,
    ):
        """Initialize GitHub issue client.

        Args:
            token: Optional GitHub personal access token.
                  If not provided, will look for GITHUB_TOKEN environment variable.
            github_backend: Optional GitHub backend interface. If not provided,
                           will create GitHubBackendAdapter instances per-request.

        Raises:
            GitHubAPIError: If no token is available
        """
        self.token = token or os.getenv("GITHUB_TOKEN")
        if not self.token:
            raise GitHubAPIError(
                "GitHub token is required. Set GITHUB_TOKEN environment variable "
                "or provide token to GitHubIssueClient."
            )
        self._github_backend = github_backend
        logger.debug("github_issue_client_initialized")

    @traced("fetch_issue")
    def fetch_issue(self, owner: str, repo: str, issue_number: int) -> dict[str, Any]:
        """Fetch a GitHub issue by number.

        Args:
            owner: Repository owner (username or organization)
            repo: Repository name
            issue_number: GitHub issue number (must be positive integer)

        Returns:
            Dictionary with issue details:
                - number: Issue number
                - title: Issue title
                - body: Issue description
                - state: 'open' or 'closed'
                - labels: List of label names
                - assignees: List of assignee usernames
                - milestone: Milestone title or None
                - url: GitHub issue URL
                - created_at: ISO format timestamp
                - updated_at: ISO format timestamp

        Raises:
            GitHubAPIError: If issue not found or API error occurs
            ValueError: If issue_number is invalid
        """
        logger.info(
            "fetching_github_issue", owner=owner, repo=repo, number=issue_number
        )

        try:
            # Use injected backend or create adapter on-demand
            if self._github_backend is None:
                client = GitHubGateway.get_github_client(
                    {"token": self.token, "owner": owner, "repo": repo}
                )
                issue_data = client.fetch_issue(issue_number)
            else:
                issue_data = self._github_backend.get_issue(str(issue_number))

            logger.debug("github_issue_fetched_successfully", number=issue_number)
            return issue_data if isinstance(issue_data, dict) else {}
        except ValueError as e:
            log_validation_error(
                e,
                entity_type="GitHubIssue",
                field_name="issue_number",
                proposed_value=issue_number,
            )
            logger.warning(
                "invalid_github_issue_number", error=str(e), severity="data_error"
            )
            raise
        except GitHubAPIError as e:
            log_external_service_error(
                e,
                service_name="GitHub",
                operation="fetch_issue",
            )
            logger.warning(
                "github_issue_fetch_failed", error=str(e), severity="infrastructure"
            )
            raise

    @traced("validate_token")
    def validate_token(self) -> tuple[bool, str]:
        """Validate GitHub token by making a test API call.

        Returns:
            Tuple of (is_valid, message)
            - (True, "Token is valid (authenticated as USERNAME)") if successful
            - (False, error_message) if invalid or error
        """
        logger.info("validating_github_token")
        try:
            # Create a backend adapter with minimal configuration (needs owner/repo for initialization)
            # We'll use a dummy repo for validation since we only care about authentication
            client = GitHubGateway.get_github_client(
                {"token": self.token, "owner": "dummy", "repo": "dummy"}
            )
            is_valid, message = client.validate_github_token()

            if is_valid:
                logger.debug("github_token_validated", authenticated_user=message)
            else:
                logger.warning(
                    "github_token_validation_failed",
                    error_message=message,
                    severity="config_error",
                )
            return is_valid, message
        except GitHubAPIError as e:
            log_external_service_error(
                e,
                service_name="GitHub",
                operation="validate_token",
            )
            return False, str(e)

    @traced("issue_exists")
    def issue_exists(self, owner: str, repo: str, issue_number: int) -> bool:
        """Check if a GitHub issue exists.

        Args:
            owner: Repository owner (username or organization)
            repo: Repository name
            issue_number: GitHub issue number

        Returns:
            True if issue exists, False otherwise
        """
        logger.info(
            "checking_github_issue_exists", owner=owner, repo=repo, number=issue_number
        )
        try:
            self.fetch_issue(owner, repo, issue_number)
            logger.debug("github_issue_exists", number=issue_number)
            return True
        except GitHubAPIError:
            logger.debug("github_issue_does_not_exist", number=issue_number)
            return False

    @traced("get_issue_diff")
    def get_issue_diff(
        self,
        owner: str,
        repo: str,
        issue_number: int,
        local_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Get differences between local issue data and GitHub issue.

        Args:
            owner: Repository owner
            repo: Repository name
            issue_number: GitHub issue number
            local_data: Local issue data to compare (keys: title, body, state, labels, assignees)

        Returns:
            Dictionary with changes:
                - has_changes: bool
                - title_changed: bool (if different)
                - body_changed: bool (if different)
                - state_changed: bool (if different)
                - labels_changed: bool (if different)
                - assignees_changed: bool (if different)
                - github_data: dict with full GitHub issue data
                - changes: dict with field-level details

        Raises:
            GitHubAPIError: If issue fetch fails
        """
        logger.info(
            "comparing_issue_with_github", owner=owner, repo=repo, number=issue_number
        )

        github_data = self.fetch_issue(owner, repo, issue_number)

        changes = {}
        has_changes = False

        # Compare fields
        fields_to_compare = ["title", "body", "state"]
        for field in fields_to_compare:
            local_value = local_data.get(field, "")
            github_value = github_data.get(field, "")
            if local_value != github_value:
                changes[field] = {
                    "local": local_value,
                    "github": github_value,
                    "changed": True,
                }
                has_changes = True

        # Compare lists (labels, assignees)
        for field in ["labels", "assignees"]:
            local_value = sorted(set(local_data.get(field, [])))
            github_value = sorted(set(github_data.get(field, [])))
            if local_value != github_value:
                changes[field] = {
                    "local": local_value,
                    "github": github_value,
                    "changed": True,
                }
                has_changes = True

        result = {
            "has_changes": has_changes,
            "github_data": github_data,
            "changes": changes,
        }

        logger.debug(
            "issue_diff_computed", has_changes=has_changes, fields_changed=len(changes)
        )
        return result

    @traced("get_issues")
    def get_issues(
        self,
        owner: str,
        repo: str,
        state: str = "all",
        labels: list[str] | None = None,
        milestone: str | None = None,
        assignee: str | None = None,
        per_page: int = 100,
    ) -> list[dict[str, Any]]:
        """Get issues from a GitHub repository.

        Args:
            owner: Repository owner (username or organization)
            repo: Repository name
            state: Issue state filter ('open', 'closed', 'all')
            labels: Optional list of label names to filter by
            milestone: Optional milestone title to filter by
            assignee: Optional assignee username to filter by
            per_page: Number of issues per page (max 100)

        Returns:
            List of issue dictionaries from GitHub API

        Raises:
            GitHubAPIError: If API call fails
        """
        logger.info(
            "fetching_github_issues",
            owner=owner,
            repo=repo,
            state=state,
            limit=per_page,
        )

        try:
            # Use injected backend or create adapter on-demand
            if self._github_backend is None:
                client = GitHubGateway.get_github_client(
                    {"token": self.token, "owner": owner, "repo": repo}
                )
                issues_data = client.get_issues(
                    state, labels, milestone, assignee, per_page
                )
            else:
                # If backend provided, use it - backend get_issues() takes no parameters
                if hasattr(self._github_backend, "get_issues"):
                    all_issues = self._github_backend.get_issues()
                    # Filter results if needed (backend returns all issues)
                    issues_data = (
                        all_issues
                        if isinstance(all_issues, list)
                        else list(all_issues.values())
                        if isinstance(all_issues, dict)
                        else []
                    )
                else:
                    issues_data = []

            logger.debug(
                "github_issues_fetched",
                owner=owner,
                repo=repo,
                count=len(issues_data or []),
            )
            return issues_data if isinstance(issues_data, list) else []

        except GitHubAPIError as e:
            log_external_service_error(
                e,
                service_name="GitHub",
                operation="get_issues",
            )
            logger.warning(
                "github_issues_fetch_failed", error=str(e), severity="infrastructure"
            )
            raise
        except Exception as e:
            log_external_service_error(
                e,
                service_name="GitHub",
                operation="get_issues",
            )
            logger.error(
                "github_issues_fetch_error",
                error=str(e),
                error_type=type(e).__name__,
                severity="infrastructure",
            )
            raise GitHubAPIError(f"Failed to fetch issues: {str(e)}") from e
