"""
Unified error handling for CLI commands.

Provides consistent error handling, logging, and user feedback across all CLI commands.
"""

import functools
import sys
import time
from collections.abc import Callable
from typing import Any, TypeVar, cast

import click

from roadmap.common.console import get_console
from roadmap.common.logging import (
    clear_correlation_id,
    get_logger,
    set_correlation_id,
)

logger = get_logger(__name__)
console = get_console()

# Type variable for decorator
F = TypeVar("F", bound=Callable[..., Any])


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
                console.print("\n[yellow]⚠️  Operation cancelled by user[/yellow]")
                sys.exit(130)

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
                if show_traceback:
                    console.print(f"\n[red]❌ Error: {e}[/red]")
                    import traceback

                    console.print(f"[dim]{traceback.format_exc()}[/dim]")
                raise

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
