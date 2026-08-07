"""Parsing and security related error classes."""

from pathlib import Path

from roadmap.common.errors.error_base import ErrorCategory, ErrorSeverity, RoadmapError


class ParseError(RoadmapError):
    """Raised when parsing fails."""

    def __init__(
        self,
        message: str,
        file_path: Path | None = None,
        line_number: int | None = None,
        **kwargs,
    ):
        """Initialize ParseError.

        Args:
            message: Error message.
            file_path: Path to the file that failed to parse.
            line_number: Line number where the parse error occurred.
            **kwargs: Additional arguments passed to parent class.
        """
        context = kwargs.get("context", {})
        if file_path:
            context["file_path"] = str(file_path)
        if line_number:
            context["line_number"] = line_number

        super().__init__(
            message,
            severity=kwargs.get("severity", ErrorSeverity.HIGH),
            category=ErrorCategory.PARSING,
            context=context,
            cause=kwargs.get("cause"),
        )
        self.file_path = file_path
        self.line_number = line_number


class SecurityError(RoadmapError):
    """Base class for security-related errors."""

    def __init__(self, message: str, **kwargs):
        """Initialize SecurityError.

        Args:
            message: Error message.
            **kwargs: Additional arguments passed to parent class.
        """
        super().__init__(
            message,
            severity=kwargs.get("severity", ErrorSeverity.CRITICAL),
            category=ErrorCategory.PERMISSION,
            context=kwargs.get("context", {}),
            cause=kwargs.get("cause"),
        )


class PathValidationError(SecurityError):
    """Raised when path validation fails (path traversal, etc.)."""

    def __init__(self, message: str, path: Path | str | None = None, **kwargs):
        """Initialize PathValidationError.

        Args:
            message: Error message.
            path: Path that failed validation.
            **kwargs: Additional arguments passed to parent class.
        """
        context = kwargs.get("context", {})
        if path:
            context["path"] = str(path)

        super().__init__(message, context=context, **kwargs)
        self.path = path
