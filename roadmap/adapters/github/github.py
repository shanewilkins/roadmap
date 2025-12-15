"""GitHub API client for roadmap CLI."""

import os
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from roadmap.adapters.github.handlers.base import (
    BaseGitHubHandler,
    GitHubAPIError,
)
from roadmap.adapters.github.handlers.labels import LabelHandler
from roadmap.infrastructure.security.credentials import get_credential_manager


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
        adapter = HTTPAdapter(max_retries=retry_strategy)
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
        except Exception:
            # Silently fail - credential manager issues shouldn't block functionality
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
        """Setup default labels for priority and status."""
        self._label_handler.owner = self.owner
        self._label_handler.repo = self.repo
        self._label_handler.setup_default_labels()
