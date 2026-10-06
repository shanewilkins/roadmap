"""Centralized exception handling for CLI commands.

This module provides error handling and formatting for all exceptions
raised by CLI commands, ensuring consistent user-facing error messages
and proper stderr output with correct exit codes.
"""

import click

from roadmap.adapters.inbound.cli.console import get_console_stderr
from roadmap.application.failures import ApplicationFailure
from roadmap.domain.failures import DomainFailure


def handle_cli_exception(
    ctx: click.Context, error: Exception, show_traceback: bool = False
) -> None:
    """Centralized exception handler for CLI commands.

    Expected failures receive concise messages. Unexpected failures include
    a traceback only when explicitly requested. All failures exit nonzero.

    Args:
        ctx: Click context
        error: The exception to handle
        show_traceback: Whether to show full traceback (for debugging)
    """
    stderr_console = get_console_stderr()

    if isinstance(error, ApplicationFailure | DomainFailure | ValueError):
        click.echo(f"Error: {error}", err=True)
    else:
        click.echo(f"Error: {error}", err=True)
        if show_traceback:
            stderr_console.print_exception(show_locals=False)
        else:
            click.echo("Run with 'roadmap --debug' for a traceback.", err=True)
    ctx.exit(1)
