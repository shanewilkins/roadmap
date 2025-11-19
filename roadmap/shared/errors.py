"""
Exception Definitions and Error Enums for Roadmap

This module contains all custom exception classes and error categorization enums.
"""

import logging
import sys
from contextlib import contextmanager
from enum import Enum
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.panel import Panel


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


class ErrorHandler:
    """Centralized error handling utilities."""

    def __init__(
        self, logger: logging.Logger | None = None, console: Console | None = None
    ):
        self.logger = logger or logging.getLogger(__name__)
        self.console = console or Console(stderr=True)
        self.error_counts: dict[ErrorCategory, int] = {}

    def handle_error(
        self,
        error: Exception | RoadmapError,
        context: dict[str, Any] | None = None,
        show_traceback: bool = False,
        exit_on_critical: bool = True,
    ) -> bool:
        """Handle an error with consistent logging and display.

        Args:
            error: The error to handle
            context: Additional context information
            show_traceback: Whether to show full traceback
            exit_on_critical: Whether to exit on critical errors

        Returns:
            bool: True if error was handled successfully, False if should propagate
        """
        # Convert to RoadmapError if needed
        if not isinstance(error, RoadmapError):
            error = RoadmapError(
                str(error),
                severity=ErrorSeverity.MEDIUM,
                category=ErrorCategory.VALIDATION,
                context=context,
                cause=error,
            )

        # Update error counts
        self.error_counts[error.category] = self.error_counts.get(error.category, 0) + 1

        # Log the error
        self._log_error(error, show_traceback)

        # Display to user
        self._display_error(error, show_traceback)

        # Handle critical errors
        if error.severity == ErrorSeverity.CRITICAL and exit_on_critical:
            sys.exit(1)

        return True

    def _log_error(self, error: RoadmapError, show_traceback: bool = False):
        """Log error with appropriate level."""
        log_message = (
            f"{error.category.value}: {error.message}{error.get_context_info()}"
        )

        if error.severity in [ErrorSeverity.CRITICAL, ErrorSeverity.HIGH]:
            self.logger.error(log_message)
        elif error.severity == ErrorSeverity.MEDIUM:
            self.logger.warning(log_message)
        else:
            self.logger.info(log_message)

        # Log traceback if requested or for critical errors
        if show_traceback or error.severity == ErrorSeverity.CRITICAL:
            if error.cause:
                self.logger.error("Caused by:", exc_info=error.cause)
            else:
                self.logger.error("Traceback:", exc_info=True)

    def _display_error(self, error: RoadmapError, show_traceback: bool = False):
        """Display error to user with rich formatting."""
        # Choose color based on severity
        color_map = {
            ErrorSeverity.CRITICAL: "red",
            ErrorSeverity.HIGH: "red",
            ErrorSeverity.MEDIUM: "yellow",
            ErrorSeverity.LOW: "blue",
            ErrorSeverity.WARNING: "yellow",
            ErrorSeverity.INFO: "blue",
        }

        color = color_map.get(error.severity, "white")

        # Create error message
        title = f"{error.severity.value.upper()}: {error.category.value.replace('_', ' ').title()}"
        message = error.message

        if error.context:
            context_info = error.get_context_info()
            message += f"\n[dim]{context_info}[/dim]"

        if show_traceback and error.cause:
            message += f"\n\n[dim]Caused by: {str(error.cause)}[/dim]"

        # Display panel
        panel = Panel(message, title=title, border_style=color, expand=False)

        self.console.print(panel)

    def get_error_summary(self) -> dict[str, int]:
        """Get summary of error counts by category."""
        return {category.value: count for category, count in self.error_counts.items()}


# Context Manager for Error Handling
@contextmanager
def handle_errors(
    error_handler: ErrorHandler | None = None,
    ignore_errors: bool = False,
    show_traceback: bool = False,
    exit_on_critical: bool = True,
    context: dict[str, Any] | None = None,
):
    """Context manager for consistent error handling.

    Args:
        error_handler: Custom error handler instance
        ignore_errors: Whether to suppress all errors
        show_traceback: Whether to show tracebacks
        exit_on_critical: Whether to exit on critical errors
        context: Additional context for errors
    """
    handler = error_handler or ErrorHandler()

    try:
        yield handler
    except RoadmapError as e:
        if not ignore_errors:
            handler.handle_error(e, context, show_traceback, exit_on_critical)
        if not ignore_errors and e.severity == ErrorSeverity.CRITICAL:
            raise
    except Exception as e:
        if not ignore_errors:
            roadmap_error = RoadmapError(
                str(e), severity=ErrorSeverity.HIGH, context=context, cause=e
            )
            handler.handle_error(
                roadmap_error, context, show_traceback, exit_on_critical
            )
        if not ignore_errors:
            raise


__all__ = [
    "ErrorSeverity",
    "ErrorCategory",
    "RoadmapError",
    "FileOperationError",
    "ValidationError",
    "NetworkError",
    "GitOperationError",
    "ConfigurationError",
    "ErrorHandler",
    "handle_errors",
]
