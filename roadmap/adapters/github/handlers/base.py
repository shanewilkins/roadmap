"""Base handler for GitHub API operations."""

from typing import Any

import requests

from roadmap.common.logging import get_logger, log_external_service_error


class GitHubAPIError(Exception):
    """Exception raised for GitHub API errors."""

    pass


class BaseGitHubHandler:
    """Base class for GitHub API handlers."""

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
            status_code = response.status_code
            
            # Don't log expected/recoverable errors at ERROR level to external_service_error
            # We'll handle logging at appropriate levels below based on status code
            
            # Handle different HTTP status codes with specific error messages and logging
            if status_code == 400:
                error_msg = "Bad Request: Invalid request payload"
                logger = get_logger()
                # Log external service error for unexpected client errors
                log_external_service_error(
                    error=e,
                    service_name="GitHub API",
                    operation=f"{method} {endpoint}",
                    retry_count=getattr(self.session, "retry_count", 0),
                )
                logger.warning(
                    "github_api_bad_request",
                    status_code=status_code,
                    operation=f"{method} {endpoint}",
                    severity="data_error",
                )
                raise GitHubAPIError(error_msg) from e
                
            elif status_code == 401:
                error_msg = "Authentication failed. Check your GitHub token."
                logger = get_logger()
                log_external_service_error(
                    error=e,
                    service_name="GitHub API",
                    operation=f"{method} {endpoint}",
                    retry_count=getattr(self.session, "retry_count", 0),
                )
                logger.warning(
                    "github_api_authentication_failed",
                    status_code=status_code,
                    severity="config",
                )
                raise GitHubAPIError(error_msg) from e
                
            elif status_code == 403:
                error_msg = "Access forbidden. Check repository permissions and token scopes."
                logger = get_logger()
                # 403 is often expected (token scope), don't log as external error
                logger.debug(
                    "github_api_access_forbidden",
                    status_code=status_code,
                    operation=f"{method} {endpoint}",
                    severity="config",
                )
                raise GitHubAPIError(error_msg) from e
                
            elif status_code == 404:
                error_msg = "Repository or resource not found."
                logger = get_logger()
                log_external_service_error(
                    error=e,
                    service_name="GitHub API",
                    operation=f"{method} {endpoint}",
                    retry_count=getattr(self.session, "retry_count", 0),
                )
                logger.warning(
                    "github_api_resource_not_found",
                    status_code=status_code,
                    operation=f"{method} {endpoint}",
                    severity="operational",
                )
                raise GitHubAPIError(error_msg) from e
                
            elif status_code == 410:
                # Gone - resource was deleted (expected, don't log as external error)
                error_msg = "Resource has been deleted (410 Gone)"
                logger = get_logger()
                logger.info(
                    "github_api_resource_gone",
                    status_code=status_code,
                    operation=f"{method} {endpoint}",
                    severity="operational",
                )
                raise GitHubAPIError(error_msg) from e
                
            elif status_code == 422:
                # Validation error - most common for issue creation/update
                error_data = response.json() if response.content else {}
                # GitHub validation errors have detailed field information
                error_details = []
                if "errors" in error_data:
                    for error in error_data.get("errors", []):
                        if isinstance(error, dict):
                            field = error.get("field", "unknown")
                            code = error.get("code", "unknown")
                            msg = error.get("message", "")
                            error_details.append(f"{field}:{code} {msg}")
                error_msg = error_data.get("message", "Validation failed")
                if error_details:
                    error_msg = f"{error_msg} - {'; '.join(error_details)}"
                logger = get_logger()
                logger.warning(
                    "github_api_validation_error",
                    status_code=status_code,
                    validation_errors=error_details,
                    severity="data_error",
                )
                raise GitHubAPIError(f"Validation error: {error_msg}") from e
                
            elif status_code == 429:
                # Rate limited (expected for heavy usage)
                error_msg = "Rate limit exceeded. Please try again later."
                retry_after = response.headers.get("Retry-After", "unknown")
                logger = get_logger()
                logger.warning(
                    "github_api_rate_limited",
                    status_code=status_code,
                    retry_after=retry_after,
                    severity="operational",
                )
                raise GitHubAPIError(error_msg) from e
                
            elif 500 <= status_code < 600:
                # Server error
                error_msg = f"GitHub API server error ({status_code})"
                logger = get_logger()
                log_external_service_error(
                    error=e,
                    service_name="GitHub API",
                    operation=f"{method} {endpoint}",
                    retry_count=getattr(self.session, "retry_count", 0),
                )
                logger.warning(
                    "github_api_server_error",
                    status_code=status_code,
                    operation=f"{method} {endpoint}",
                    severity="infrastructure",
                )
                raise GitHubAPIError(error_msg) from e
                
            else:
                # Unknown error
                error_msg = f"GitHub API error ({status_code}): {e}"
                logger = get_logger()
                log_external_service_error(
                    error=e,
                    service_name="GitHub API",
                    operation=f"{method} {endpoint}",
                    retry_count=getattr(self.session, "retry_count", 0),
                )
                logger.warning(
                    "github_api_unknown_error",
                    status_code=status_code,
                    operation=f"{method} {endpoint}",
                    severity="operational",
                )
                raise GitHubAPIError(error_msg) from e
        except requests.exceptions.RequestException as e:
            # Log external service error for request failures
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

    def _paginate_request(
        self,
        method: str,
        endpoint: str,
        params: dict | None = None,
        per_page: int = 100,
    ) -> list[dict[str, Any]]:
        """Make a paginated request to GitHub API.

        Automatically handles pagination by checking the Link header
        for next page references. Returns all items across all pages.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            params: Query parameters (will add page and per_page)
            per_page: Items per page (max 100 for GitHub)

        Returns:
            List of all items from all pages

        Raises:
            GitHubAPIError: If any request fails
        """
        logger = get_logger()
        all_items = []
        page = 1
        params = params or {}

        while True:
            # Add pagination params
            page_params = {**params, "page": page, "per_page": per_page}

            response = self._make_request(method, endpoint, params=page_params)
            items_page = response.json()

            if not items_page:
                # No more items on this page
                logger.debug(
                    "pagination_complete",
                    endpoint=endpoint,
                    total_pages=page - 1,
                    total_items=len(all_items),
                )
                break

            all_items.extend(items_page)
            logger.debug(
                "pagination_page_fetched",
                endpoint=endpoint,
                page=page,
                page_count=len(items_page),
                total_so_far=len(all_items),
            )

            # Check if there are more pages by looking at the Link header
            link_header = response.headers.get("Link", "")
            if 'rel="next"' not in link_header:
                # No next page link, we're done
                logger.debug(
                    "pagination_no_next_link",
                    endpoint=endpoint,
                    final_page=page,
                    total_items=len(all_items),
                )
                break

            page += 1

        return all_items

