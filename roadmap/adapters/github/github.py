"""GitHub API client for roadmap CLI."""

import os
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from roadmap.infrastructure.security.credentials import get_credential_manager


class GitHubAPIError(Exception):
    """Exception raised for GitHub API errors."""

    pass


class GitHubClient:
    """GitHub API client for managing issues and milestones."""

    BASE_URL = "https://api.github.com"

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

    def _check_repository(self) -> None:
        """Check if repository is set."""
        if not self.owner or not self.repo:
            raise GitHubAPIError(
                "Repository not set. Use set_repository() or provide owner/repo in constructor."
            )

    def _make_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """Make a request to the GitHub API."""
        url = f"{self.BASE_URL}{endpoint}"

        try:
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            return response
        except requests.exceptions.HTTPError as e:
            if response.status_code == 401:
                raise GitHubAPIError(
                    "Authentication failed. Check your GitHub token."
                ) from e
            elif response.status_code == 403:
                raise GitHubAPIError(
                    "Access forbidden. Check repository permissions and token scopes."
                ) from e
            elif response.status_code == 404:
                raise GitHubAPIError("Repository or resource not found.") from e
            elif response.status_code == 422:
                error_data = response.json() if response.content else {}
                error_msg = error_data.get("message", "Validation failed")
                raise GitHubAPIError(f"Validation error: {error_msg}") from e
            else:
                raise GitHubAPIError(
                    f"GitHub API error ({response.status_code}): {e}"
                ) from e
        except requests.exceptions.RequestException as e:
            raise GitHubAPIError(f"Request failed: {e}") from e

    def test_authentication(self) -> dict[str, Any]:
        """Test authentication and get user info."""
        response = self._make_request("GET", "/user")
        return response.json()

    def test_repository_access(self) -> dict[str, Any]:
        """Test repository access."""
        self._check_repository()
        response = self._make_request("GET", f"/repos/{self.owner}/{self.repo}")
        return response.json()
