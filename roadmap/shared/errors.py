"""
Exception Definitions and Error Enums for Roadmap

This module contains all custom exception classes and error categorization enums.
"""

from enum import Enum
from pathlib import Path
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


# Custom Exception Hierarchy
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
        super().__init__(message)
        self.message = message
        self.severity = severity
        self.category = category
        self.context = context or {}
        self.cause = cause

    def __str__(self) -> str:
        return self.message

    def get_context_info(self) -> str:
        """Get formatted context information."""
        if not self.context:
            return ""

        context_parts = []
        for key, value in self.context.items():
            context_parts.append(f"{key}: {value}")

        return f" ({', '.join(context_parts)})"


class FileOperationError(RoadmapError):
    """Errors related to file operations."""

    def __init__(
        self,
        message: str,
        file_path: Path | None = None,
        operation: str | None = None,
        **kwargs,
    ):
        context = kwargs.get("context", {})
        if file_path:
            context["file_path"] = str(file_path)
        if operation:
            context["operation"] = operation

        super().__init__(
            message,
            severity=kwargs.get("severity", ErrorSeverity.HIGH),
            category=ErrorCategory.FILE_OPERATION,
            context=context,
            cause=kwargs.get("cause"),
        )
        self.file_path = file_path
        self.operation = operation


class ValidationError(RoadmapError):
    """Errors related to data validation."""

    def __init__(
        self, message: str, field: str | None = None, value: Any | None = None, **kwargs
    ):
        context = kwargs.get("context", {})
        if field:
            context["field"] = field
        if value is not None:
            context["value"] = str(value)

        super().__init__(
            message,
            severity=kwargs.get("severity", ErrorSeverity.MEDIUM),
            category=ErrorCategory.VALIDATION,
            context=context,
            cause=kwargs.get("cause"),
        )
        self.field = field
        self.value = value


class NetworkError(RoadmapError):
    """Errors related to network operations."""

    def __init__(
        self,
        message: str,
        url: str | None = None,
        status_code: int | None = None,
        **kwargs,
    ):
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


class GitOperationError(RoadmapError):
    """Errors related to Git operations."""

    def __init__(
        self,
        message: str,
        command: str | None = None,
        exit_code: int | None = None,
        **kwargs,
    ):
        context = kwargs.get("context", {})
        if command:
            context["command"] = command
        if exit_code is not None:
            context["exit_code"] = exit_code

        super().__init__(
            message,
            severity=kwargs.get("severity", ErrorSeverity.HIGH),
            category=ErrorCategory.GIT_OPERATION,
            context=context,
            cause=kwargs.get("cause"),
        )
        self.command = command
        self.exit_code = exit_code


class ConfigurationError(RoadmapError):
    """Errors related to configuration."""

    def __init__(self, message: str, config_file: Path | None = None, **kwargs):
        context = kwargs.get("context", {})
        if config_file:
            context["config_file"] = str(config_file)

        super().__init__(
            message,
            severity=kwargs.get("severity", ErrorSeverity.HIGH),
            category=ErrorCategory.CONFIGURATION,
            context=context,
            cause=kwargs.get("cause"),
        )
        self.config_file = config_file


__all__ = [
    "ErrorSeverity",
    "ErrorCategory",
    "RoadmapError",
    "FileOperationError",
    "ValidationError",
    "NetworkError",
    "GitOperationError",
    "ConfigurationError",
]
