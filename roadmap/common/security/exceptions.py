"""Security exceptions."""


class SecurityError(Exception):
    """Base exception for security-related errors."""

    pass


class PathValidationError(SecurityError):
    """Exception raised for path validation failures."""

    pass
