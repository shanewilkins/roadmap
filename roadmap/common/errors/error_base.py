"""Base error classes and enums for Roadmap."""

from enum import Enum
from typing import Any


class ErrorSeverity(Enum):
    """Error severity levels for consistent classification."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    WARNING = "warning"
    INFO = "info"


class ErrorCategory(Enum):
    """Error categories for better organization and handling."""

    FILE_OPERATION = "file_operation"
    VALIDATION = "validation"
    NETWORK = "network"
    GIT_OPERATION = "git_operation"
    GITHUB_API = "github_api"
    PARSING = "parsing"
    CONFIGURATION = "configuration"
    PERMISSION = "permission"
    DEPENDENCY = "dependency"
    USER_INPUT = "user_input"


class RoadmapError(Exception):
    """Base exception for all roadmap-specific errors."""

    def __init__(
        self,
        message: str,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        category: ErrorCategory = ErrorCategory.VALIDATION,
        context: dict[str, Any] | None = None,
        cause: Exception | None = None,
    ):
        """Initialize RoadmapError.

        Args:
            message: Error message.
            severity: Error severity level.
            category: Error category.
            context: Additional context dictionary.
            cause: Underlying exception that caused this error.
        """
        super().__init__(message)
        self.message = message
        self.severity = severity
        self.category = category
        self.context = context or {}
        self.cause = cause

    def __str__(self) -> str:
        """Return string representation of error."""
        return self.message

    def get_context_info(self) -> str:
        """Get formatted context information."""
        if not self.context:
            return ""

        context_parts = []
        for key, value in self.context.items():
            context_parts.append(f"{key}: {value}")

        return f" ({', '.join(context_parts)})"
