"""Base handler for GitHub API operations."""

from typing import Any, TypedDict

import requests

from roadmap.adapters.base_paginated_adapter import BasePaginatedAdapter
from roadmap.common.logging import get_logger, log_external_service_error


class GitHubAPIError(Exception):
    """Exception raised for GitHub API errors."""

    pass


class _ExternalLogKwargs(TypedDict):
    service_name: str
    operation: str
    retry_count: int


class BaseGitHubHandler(BasePaginatedAdapter):
    """Base class for GitHub API handlers.

    Inherits pagination support from BasePaginatedAdapter for handling
    GitHub's paginated API responses.
    """

    BASE_URL = "https://api.github.com"

    def __init__(
        self,
        session: requests.Session,
        owner: str | None = None,
        repo: str | None = None,
    ):
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

    def _raise_http_error(
        self,
        status_code: int,
        response: requests.Response,
        method: str,
        endpoint: str,
        e: requests.exceptions.HTTPError,
    ) -> None:
        """Log and raise a GitHubAPIError for the given HTTP status code."""
        retry_count = getattr(self.session, "retry_count", 0)
        if not isinstance(retry_count, int):
            retry_count = 0

        log_kwargs: _ExternalLogKwargs = {
            "service_name": "GitHub API",
            "operation": f"{method} {endpoint}",
            "retry_count": retry_count,
        }

        if status_code == 400:
            log_external_service_error(error=e, **log_kwargs)
            get_logger().warning(
                "github_api_bad_request",
                status_code=status_code,
                operation=f"{method} {endpoint}",
                severity="data_error",
            )
            raise GitHubAPIError("Bad Request: Invalid request payload") from e

        if status_code == 401:
            log_external_service_error(error=e, **log_kwargs)
            get_logger().warning(
                "github_api_authentication_failed",
                status_code=status_code,
                severity="config",
            )
            raise GitHubAPIError(
                "Authentication failed. Check your GitHub token."
            ) from e

        if status_code == 403:
            response_message = None
            try:
                if response.content:
                    response_message = response.json().get("message")
            except Exception as parse_error:
                get_logger().warning(
                    "github_api_forbidden_response_parse_failed",
                    error=str(parse_error),
                    severity="operational",
                )
            get_logger().warning(
                "github_api_access_forbidden",
                status_code=status_code,
                operation=f"{method} {endpoint}",
                owner=self.owner,
                repo=self.repo,
                rate_limit_remaining=response.headers.get("X-RateLimit-Remaining"),
                rate_limit_reset=response.headers.get("X-RateLimit-Reset"),
                response_message=response_message,
                severity="config",
            )
            raise GitHubAPIError(
                "Access forbidden. Check repository permissions and token scopes."
            ) from e

        if status_code == 404:
            log_external_service_error(error=e, **log_kwargs)
            get_logger().warning(
                "github_api_resource_not_found",
                status_code=status_code,
                operation=f"{method} {endpoint}",
                severity="operational",
            )
            raise GitHubAPIError("Repository or resource not found.") from e

        if status_code == 410:
            get_logger().info(
                "github_api_resource_gone",
                status_code=status_code,
                operation=f"{method} {endpoint}",
                severity="operational",
            )
            raise GitHubAPIError("Resource has been deleted (410 Gone)") from e

        if status_code == 422:
            error_data = response.json() if response.content else {}
            error_details = [
                f"{err.get('field', 'unknown')}:{err.get('code', 'unknown')} {err.get('message', '')}"
                for err in error_data.get("errors", [])
                if isinstance(err, dict)
            ]
            error_msg = error_data.get("message", "Validation failed")
            if error_details:
                error_msg = f"{error_msg} - {'; '.join(error_details)}"
            get_logger().warning(
                "github_api_validation_error",
                status_code=status_code,
                validation_errors=error_details,
                severity="data_error",
            )
            raise GitHubAPIError(f"Validation error: {error_msg}") from e

        if status_code == 429:
            retry_after = response.headers.get("Retry-After", "unknown")
            get_logger().warning(
                "github_api_rate_limited",
                status_code=status_code,
                retry_after=retry_after,
                severity="operational",
            )
            raise GitHubAPIError("Rate limit exceeded. Please try again later.") from e

        if 500 <= status_code < 600:
            log_external_service_error(error=e, **log_kwargs)
            get_logger().warning(
                "github_api_server_error",
                status_code=status_code,
                operation=f"{method} {endpoint}",
                severity="infrastructure",
            )
            raise GitHubAPIError(f"GitHub API server error ({status_code})") from e

        # Unknown status code
        log_external_service_error(error=e, **log_kwargs)
        get_logger().warning(
            "github_api_unknown_error",
            status_code=status_code,
            operation=f"{method} {endpoint}",
            severity="operational",
        )
        raise GitHubAPIError(f"GitHub API error ({status_code}): {e}") from e

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
            self._raise_http_error(response.status_code, response, method, endpoint, e)
            raise  # unreachable but satisfies type checkers
        except requests.exceptions.RequestException as e:
            log_external_service_error(
                error=e,
                service_name="GitHub API",
                operation=f"{method} {endpoint}",
                retry_count=0,
            )
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
