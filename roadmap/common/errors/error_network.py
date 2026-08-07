"""Network and GitHub API related error classes."""

from roadmap.common.errors.error_base import ErrorCategory, ErrorSeverity, RoadmapError


class NetworkError(RoadmapError):
    """Errors related to network operations."""

    def __init__(
        self,
        message: str,
        url: str | None = None,
        status_code: int | None = None,
        **kwargs,
    ):
        """Initialize NetworkError.

        Args:
            message: Error message.
            url: URL where the network error occurred.
            status_code: HTTP status code from the response.
            **kwargs: Additional arguments passed to parent class.
        """
        context = kwargs.get("context", {})
        if url:
            context["url"] = url
        if status_code:
            context["status_code"] = status_code

        super().__init__(
            message,
            severity=kwargs.get("severity", ErrorSeverity.HIGH),
            category=ErrorCategory.NETWORK,
            context=context,
            cause=kwargs.get("cause"),
        )
        self.url = url
        self.status_code = status_code


class GitHubAPIError(NetworkError):
    """Errors specific to GitHub API operations."""

    def __init__(
        self,
        message: str,
        endpoint: str | None = None,
        rate_limit_remaining: int | None = None,
        **kwargs,
    ):
        """Initialize GitHubAPIError.

        Args:
            message: Error message.
            endpoint: GitHub API endpoint that was called.
            rate_limit_remaining: Number of remaining GitHub API requests.
            **kwargs: Additional arguments passed to parent class.
        """
        context = kwargs.get("context", {})
        if endpoint:
            context["endpoint"] = endpoint
        if rate_limit_remaining is not None:
            context["rate_limit_remaining"] = rate_limit_remaining

        super().__init__(
            message,
            severity=kwargs.get("severity", ErrorSeverity.HIGH),
            **kwargs,
        )
        self.endpoint = endpoint
        self.rate_limit_remaining = rate_limit_remaining


class AuthenticationError(RoadmapError):
    """Raised when authentication fails."""

    def __init__(self, message: str, **kwargs):
        """Initialize AuthenticationError.

        Args:
            message: Error message.
            **kwargs: Additional arguments passed to parent class.
        """
        super().__init__(
            message,
            severity=kwargs.get("severity", ErrorSeverity.HIGH),
            category=ErrorCategory.PERMISSION,
            context=kwargs.get("context", {}),
            cause=kwargs.get("cause"),
        )
