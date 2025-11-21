"""
Unified error handling for CLI commands.

Provides consistent error handling, logging, and user feedback across all CLI commands.
"""

import functools
import sys
import time
import traceback
from collections.abc import Callable
from typing import Any, TypeVar, cast

import click
from rich.console import Console

from roadmap.shared.console import get_console
from roadmap.shared.errors import RoadmapError
from roadmap.shared.logging import (
    clear_correlation_id,
    get_logger,
    set_correlation_id,
)

logger = get_logger(__name__)
console = get_console()

# Type variable for decorator
F = TypeVar("F", bound=Callable[..., Any])


class CLIErrorHandler:
    """Unified CLI error handling with consistent formatting and logging."""

    @staticmethod
    def handle_error(
        error: Exception,
        console_instance: Console | None = None,
        command_name: str | None = None,
        show_traceback: bool = False,
    ) -> None:
        """
        Handle CLI errors with consistent formatting and logging.

        Args:
            error: The exception to handle
            console_instance: Console for output (uses default if None)
            command_name: Name of the command that raised the error
            show_traceback: Whether to show full traceback (for debugging)
        """
        console_output = console_instance or console

        # Log the full error details
        error_context = {
            "error_type": type(error).__name__,
            "error_message": str(error),
            "command": command_name,
        }

        if isinstance(error, RoadmapError):
            # Application-level errors (expected)
            logger.error(
                f"Application error in {command_name}: {error.message}",
                extra=error_context,
            )
            console_output.print(f"[red]❌ {error.message}[/red]")

        elif isinstance(error, click.ClickException):
            # Click-specific errors (expected)
            logger.info(
                f"CLI error in {command_name}: {error.format_message()}",
                extra=error_context,
            )
            console_output.print(f"[red]❌ {error.format_message()}[/red]")

        elif isinstance(error, FileNotFoundError | PermissionError | OSError):
            # File system errors
            logger.error(
                f"File system error in {command_name}: {error}", extra=error_context
            )
            console_output.print(f"[red]❌ File error: {error}[/red]")

        elif isinstance(error, ValueError | TypeError):
            # Validation errors
            logger.error(
                f"Validation error in {command_name}: {error}", extra=error_context
            )
            console_output.print(f"[red]❌ Invalid input: {error}[/red]")

        else:
            # Unexpected errors
            logger.exception(f"Unexpected error in {command_name}", extra=error_context)
            console_output.print(f"[red]❌ Unexpected error: {error}[/red]")

            if show_traceback:
                console_output.print("\n[dim]Traceback:[/dim]")
                console_output.print(f"[dim]{traceback.format_exc()}[/dim]")

        # Always abort after error
        raise click.Abort() from error

    @staticmethod
    def handle_keyboard_interrupt(
        console_instance: Console | None = None,
        command_name: str | None = None,
    ) -> None:
        """
        Handle Ctrl+C keyboard interrupts gracefully.

        Args:
            console_instance: Console for output (uses default if None)
            command_name: Name of the command that was interrupted
        """
        console_output = console_instance or console
        logger.info(f"Command interrupted by user: {command_name}")
        console_output.print("\n[yellow]⚠️  Operation cancelled by user[/yellow]")
        sys.exit(130)  # Standard exit code for SIGINT

    @staticmethod
    def handle_success(
        message: str,
        console_instance: Console | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        """
        Display success message with optional details.

        Args:
            message: Success message to display
            console_instance: Console for output (uses default if None)
            details: Optional dictionary of details to display
        """
        console_output = console_instance or console
        console_output.print(f"[green]✅ {message}[/green]")

        if details:
            for key, value in details.items():
                console_output.print(f"   {key}: {value}", style="dim")

    @staticmethod
    def handle_warning(
        message: str,
        console_instance: Console | None = None,
    ) -> None:
        """
        Display warning message.

        Args:
            message: Warning message to display
            console_instance: Console for output (uses default if None)
        """
        console_output = console_instance or console
        console_output.print(f"[yellow]⚠️  {message}[/yellow]")
        logger.warning(message)


def handle_cli_errors(
    command_name: str | None = None, show_traceback: bool = False, log_args: bool = True
) -> Callable[[F], F]:
    """
    Decorator to add unified error handling to CLI commands with timing and correlation tracking.

    Args:
        command_name: Name of the command (for logging)
        show_traceback: Whether to show full traceback on errors
        log_args: Whether to log function arguments (filtered to remove sensitive data)

    Example:
        @click.command()
        @handle_cli_errors(command_name="issue create")
        def create_issue(...):
            # Your command logic here
            pass
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            cmd_name = command_name or func.__name__
            start_time = time.perf_counter()

            # Set correlation ID for this command invocation
            correlation_id = set_correlation_id()

            # Filter sensitive data from arguments
            if log_args:
                filtered_kwargs = {
                    k: "***REDACTED***"
                    if any(s in k.lower() for s in ["token", "password", "secret"])
                    else v
                    for k, v in kwargs.items()
                }
                logger.info(
                    f"Command invoked: {cmd_name}",
                    operation=cmd_name,
                    correlation_id=correlation_id,
                    args=filtered_kwargs,
                )
            else:
                logger.info(
                    f"Command invoked: {cmd_name}",
                    operation=cmd_name,
                    correlation_id=correlation_id,
                )

            try:
                result = func(*args, **kwargs)

                # Log successful completion with timing
                duration = time.perf_counter() - start_time
                logger.info(
                    f"Command completed: {cmd_name}",
                    operation=cmd_name,
                    correlation_id=correlation_id,
                    duration_ms=round(duration * 1000, 2),
                    success=True,
                )

                return result

            except KeyboardInterrupt:
                duration = time.perf_counter() - start_time
                logger.warning(
                    "Operation cancelled by user",
                    operation=cmd_name,
                    correlation_id=correlation_id,
                    duration_ms=round(duration * 1000, 2),
                )
                CLIErrorHandler.handle_keyboard_interrupt(command_name=cmd_name)

            except click.Abort:
                # Already handled, just re-raise
                raise

            except Exception as e:
                duration = time.perf_counter() - start_time
                logger.error(
                    f"Command failed: {cmd_name}",
                    operation=cmd_name,
                    correlation_id=correlation_id,
                    duration_ms=round(duration * 1000, 2),
                    error_type=type(e).__name__,
                    error_message=str(e),
                )
                CLIErrorHandler.handle_error(
                    e, command_name=cmd_name, show_traceback=show_traceback
                )

            finally:
                # Clear correlation ID after command completes
                clear_correlation_id()

        return cast(F, wrapper)

    return decorator


def validate_required_args(**kwargs: Any) -> None:
    """
    Validate that required arguments are provided.

    Args:
        **kwargs: Dictionary of argument names and values to validate

    Raises:
        click.UsageError: If any required argument is missing

    Example:
        validate_required_args(title=title, assignee=assignee)
    """
    missing = [name for name, value in kwargs.items() if value is None or value == ""]
    if missing:
        missing_args = ", ".join(f"--{name.replace('_', '-')}" for name in missing)
        raise click.UsageError(f"Missing required arguments: {missing_args}")
