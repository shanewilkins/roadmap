"""Base handler for GitHub API operations."""

from typing import Any

import requests


class GitHubAPIError(Exception):
    """Exception raised for GitHub API errors."""

    pass


class BaseGitHubHandler:
    """Base class for GitHub API handlers."""

    BASE_URL = "https://api.github.com"

    def __init__(self, session: requests.Session, owner: str | None = None, repo: str | None = None):
        """Initialize handler with GitHub API session.

        Args:
            session: Requests session with authentication headers
            owner: Repository owner (username or organization)
            repo: Repository name
        """
        self.session = session
        self.owner = owner
        self.repo = repo

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
        """Make a request to the GitHub API.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            **kwargs: Additional arguments to pass to requests

        Returns:
            Response object

        Raises:
            GitHubAPIError: If the request fails
        """
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
