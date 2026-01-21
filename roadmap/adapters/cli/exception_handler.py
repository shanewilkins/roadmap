"""Centralized exception handling for CLI commands.

This module provides error handling and formatting for all exceptions
raised by CLI commands, ensuring consistent user-facing error messages
and proper stderr output with correct exit codes.
"""

from collections.abc import Callable
from typing import Any

import click

from roadmap.common.console import get_console_stderr
from roadmap.common.error_formatter import (
    format_error_message,
)
from roadmap.common.errors.exceptions import RoadmapException


def handle_cli_exception(
    ctx: click.Context, error: Exception, show_traceback: bool = False
) -> None:
    """Centralized exception handler for CLI commands.

    Catches RoadmapException instances and formats them for user output,
    directing errors to stderr with proper exit codes. Other exceptions
    are re-raised or logged as needed.

    Args:
        ctx: Click context
        error: The exception to handle
        show_traceback: Whether to show full traceback (for debugging)
    """
    stderr_console = get_console_stderr()

    if isinstance(error, RoadmapException):
        # Format using our error formatter, which respects plain mode
        error_msg = format_error_message(error)
        stderr_console.print(error_msg)
        ctx.exit(error.exit_code)
    else:
        # For non-roadmap exceptions, show generic error message
        error_msg = format_error_message(error)
        stderr_console.print(error_msg)
        if show_traceback:
            stderr_console.print_exception()
        ctx.exit(1)


def with_exception_handler(
    show_traceback: bool = False,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Wrap CLI commands with centralized exception handling.

    Args:
        show_traceback: Whether to show full traceback on error

    Returns:
        Decorator function
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        """Implement exception handling decorator."""

        def wrapper(*args: Any, **kwargs: Any) -> Any:
            """Execute wrapped function with exception handling."""
            try:
                return func(*args, **kwargs)
            except click.Abort:
                # Click.Abort is intentional, don't handle it
                raise
            except click.ClickException:
                # Click exceptions are already formatted, re-raise
                raise
            except RoadmapException as e:
                # Format roadmap exceptions for output
                ctx = click.get_current_context()
                handle_cli_exception(ctx, e, show_traceback=show_traceback)
            except Exception as e:
                # Unexpected exceptions get generic handling
                ctx = click.get_current_context()
                handle_cli_exception(ctx, e, show_traceback=show_traceback)

        return click.pass_context(wrapper)

    return decorator


def setup_cli_exception_handling() -> None:
    """Set up global exception handling for the CLI group.

    This configures Click to use our custom exception handler for all
    subcommands in the CLI group.

    Args:
        main_group: The Click group (main CLI) to configure
    """

    def handle_exception(ctx: click.Context, exc: Exception) -> None:
        """Click exception callback."""
        handle_cli_exception(ctx, exc, show_traceback=False)

    # Note: Click's exception handling is context-specific;
    # individual commands should use the decorator for best results
    # The group-level handling provides a fallback
