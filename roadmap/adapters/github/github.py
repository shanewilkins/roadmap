"""GitHub API client for roadmap CLI."""

import os
from typing import Any, cast

import requests
from requests.adapters import HTTPAdapter
from structlog import get_logger
from urllib3.util.retry import Retry

from roadmap.adapters.github.handlers.base import (
    BaseGitHubHandler,
    GitHubAPIError,
)
from roadmap.adapters.github.handlers.labels import LabelHandler
from roadmap.infrastructure.security.credentials import get_credential_manager

logger = get_logger()


class GitHubClient(BaseGitHubHandler):
    """GitHub API client for managing issues and milestones."""

    def __init__(
        self,
        token: str | None = None,
        owner: str | None = None,
        repo: str | None = None,
    ):
        """Initialize GitHub client.

        Args:
            token: GitHub personal access token
            owner: Repository owner (username or organization)
            repo: Repository name
        """
        # Try to get token from multiple sources with priority:
        # 1. Explicit parameter
        # 2. Environment variable
        # 3. Credential manager
        self.token = token or self._get_token_secure()
        self.owner = owner
        self.repo = repo

        if not self.token:
            raise GitHubAPIError(
                "GitHub token is required. Set GITHUB_TOKEN environment variable, use credential manager, or provide token."
            )

        # Set up session with retry strategy
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=[
                "HEAD",
                "GET",
                "POST",
                "PUT",
                "DELETE",
                "OPTIONS",
                "TRACE",
            ],
        )
        adapter = HTTPAdapter(max_retries=cast(int, retry_strategy))
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        # Set default headers
        self.session.headers.update(
            {
                "Authorization": f"token {self.token}",
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "roadmap-cli/1.0",
            }
        )

        # Initialize label handler
        self._label_handler = LabelHandler(self.session, owner, repo)

        # Initialize issue handler
        from roadmap.adapters.github.handlers.issues import IssueHandler

        self._issue_handler = IssueHandler(self.session, owner, repo)

    def _get_token_secure(self) -> str | None:
        """Get token from secure sources (environment variable or credential manager)."""
        # First try environment variable
        env_token = os.getenv("GITHUB_TOKEN")
        if env_token:
            return env_token

        # Then try credential manager
        try:
            credential_manager = get_credential_manager()
            return credential_manager.get_token()
        except Exception as e:
            logger.debug("credential_manager_failed", error=str(e))
            return None

    def set_repository(self, owner: str, repo: str) -> None:
        """Set the target repository."""
        self.owner = owner
        self.repo = repo

    def test_authentication(self) -> dict[str, Any]:
        """Test authentication and get user info."""
        response = self._make_request("GET", "/user")
        return response.json()

    def test_repository_access(self) -> dict[str, Any]:
        """Test repository access."""
        self._check_repository()
        response = self._make_request("GET", f"/repos/{self.owner}/{self.repo}")
        return response.json()

    def status_to_labels(self, status: str) -> list[str]:
        """Convert issue status to GitHub labels.

        Args:
            status: The issue status (e.g., 'todo', 'in-progress', 'blocked', 'review', 'closed')

        Returns:
            List of GitHub labels corresponding to the status
        """
        status_label_map = {
            "todo": ["status:todo"],
            "in-progress": ["status:in-progress"],
            "blocked": ["status:blocked"],
            "review": ["status:review"],
            "closed": ["status:closed"],
        }
        return status_label_map.get(status, [])

    def labels_to_status(self, labels: list[str]) -> str | None:
        """Convert GitHub labels to issue status.

        Args:
            labels: List of GitHub labels

        Returns:
            The corresponding issue status, or None if no status label found
        """
        label_status_map = {
            "status:todo": "todo",
            "status:in-progress": "in-progress",
            "status:blocked": "blocked",
            "status:review": "review",
            "status:closed": "closed",
        }
        for label in labels:
            if label in label_status_map:
                return label_status_map[label]
        return None

    def get_labels(self) -> list[dict[str, Any]]:
        """Get repository labels.

        Returns:
            List of label dictionaries
        """
        self._label_handler.owner = self.owner
        self._label_handler.repo = self.repo
        return self._label_handler.get_labels()

    def create_label(
        self, name: str, color: str, description: str | None = None
    ) -> dict[str, Any]:
        """Create a new label.

        Args:
            name: Label name
            color: Label color (hex code)
            description: Label description

        Returns:
            Created label dictionary
        """
        self._label_handler.owner = self.owner
        self._label_handler.repo = self.repo
        return self._label_handler.create_label(name, color, description)

    def setup_default_labels(self) -> None:
        """Set up default labels for priority and status."""
        self._label_handler.owner = self.owner
        self._label_handler.repo = self.repo
        self._label_handler.setup_default_labels()

    def get_issues(
        self,
        state: str = "all",
        labels: list[str] | None = None,
        milestone: str | None = None,
        assignee: str | None = None,
        per_page: int = 100,
    ) -> list[dict[str, Any]]:
        """Get issues from the repository.

        Args:
            state: Issue state ('open', 'closed', 'all')
            labels: Optional list of label names to filter by
            milestone: Optional milestone title to filter by
            assignee: Optional assignee username to filter by
            per_page: Number of issues per page (max 100)

        Returns:
            List of issue dictionaries
        """
        self._issue_handler.owner = self.owner
        self._issue_handler.repo = self.repo
        return self._issue_handler.get_issues(
            state=state,
            labels=labels,
            milestone=milestone,
            assignee=assignee,
            per_page=per_page,
        )

    def fetch_issue(self, issue_number: int) -> dict[str, Any]:
        """Fetch a GitHub issue by number.

        Args:
            issue_number: GitHub issue number (must be positive integer)

        Returns:
            Dictionary with issue details: number, title, body, state, labels, assignees

        Raises:
            GitHubAPIError: If issue not found or API error occurs
            ValueError: If issue_number is invalid
        """
        if not isinstance(issue_number, int) or issue_number <= 0:
            raise ValueError(
                f"Issue number must be a positive integer, got {issue_number}"
            )

        self._check_repository()
        try:
            response = self._make_request(
                "GET", f"/repos/{self.owner}/{self.repo}/issues/{issue_number}"
            )
            data = response.json()

            # Extract relevant fields
            return {
                "number": data.get("number"),
                "title": data.get("title"),
                "body": data.get("body") or "",
                "state": data.get("state"),  # 'open' or 'closed'
                "labels": [label["name"] for label in data.get("labels", [])],
                "assignees": [
                    assignee["login"] for assignee in data.get("assignees", [])
                ],
                "milestone": data.get("milestone", {}).get("title")
                if data.get("milestone")
                else None,
                "url": data.get("html_url"),
                "created_at": data.get("created_at"),
                "updated_at": data.get("updated_at"),
            }
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                raise GitHubAPIError(
                    f"GitHub issue #{issue_number} not found in {self.owner}/{self.repo}"
                ) from e
            elif e.response.status_code == 401:
                raise GitHubAPIError(
                    "GitHub authentication failed - invalid token"
                ) from e
            else:
                raise GitHubAPIError(
                    f"GitHub API error: {e.response.status_code} {e.response.reason}"
                ) from e
        except requests.exceptions.RequestException as e:
            raise GitHubAPIError(f"GitHub API connection error: {str(e)}") from e

    def validate_github_token(self) -> tuple[bool, str]:
        """Validate GitHub token by making a test API call.

        Returns:
            Tuple of (is_valid, message)
            - (True, "Token is valid") if successful
            - (False, error_message) if invalid or error
        """
        try:
            response = self._make_request("GET", "/user")
            if response.status_code == 200:
                user_data = response.json()
                login = user_data.get("login", "unknown")
                return True, f"Token is valid (authenticated as {login})"
            else:
                return False, f"Token validation failed: {response.status_code}"
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                return False, "GitHub token is invalid or expired"
            else:
                return False, f"GitHub API error: {e.response.status_code}"
        except requests.exceptions.RequestException as e:
            return False, f"GitHub API connection error: {str(e)}"

    def validate_assignee(self, assignee: str) -> tuple[bool, str]:
        """Validate that a user is a valid assignee for this repository.

        Args:
            assignee: GitHub username to validate

        Returns:
            Tuple of (is_valid, error_message)
            - (True, "") if valid
            - (False, error_message) if invalid
        """
        if not assignee or not assignee.strip():
            return False, "Assignee cannot be empty"

        assignee = assignee.strip()

        try:
            self._check_repository()
            # Check if the user exists and has access to the repository
            # We'll try to get the user info from GitHub
            response = self._make_request("GET", f"/users/{assignee}")

            if response.status_code == 200:
                # User exists, now check if they have access to the repository
                # Try to get their permission level in the repository
                perm_response = self._make_request(
                    "GET",
                    f"/repos/{self.owner}/{self.repo}/collaborators/{assignee}/permission",
                )

                if perm_response.status_code == 204:
                    # User has some level of access to the repository
                    return True, ""
                elif perm_response.status_code == 404:
                    # User exists but is not a collaborator - they can still be assigned
                    # to public repositories by maintainers, so return True
                    return True, ""
                else:
                    return False, f"Could not verify access for {assignee}"
            elif response.status_code == 404:
                return False, f"GitHub user '{assignee}' not found"
            else:
                return False, f"GitHub API error: {response.status_code}"

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                return False, f"GitHub user '{assignee}' not found"
            else:
                return False, f"GitHub API error: {e.response.status_code}"
        except requests.exceptions.RequestException as e:
            return False, f"GitHub API connection error: {str(e)}"
