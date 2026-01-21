"""Error handling utilities and context managers."""

import logging
import sys
from contextlib import contextmanager
from typing import Any

from rich.console import Console
from rich.panel import Panel

from roadmap.common.errors.error_base import ErrorCategory, ErrorSeverity, RoadmapError


class ErrorHandler:
    """Centralized error handling utilities."""

    def __init__(
        self, logger: logging.Logger | None = None, console: Console | None = None
    ):
        """Initialize ErrorHandler.

        Args:
            logger: Logger instance for error logging. Defaults to module logger.
            console: Console instance for error display. Defaults to stderr console.
        """
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
