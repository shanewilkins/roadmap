"""Shared utilities for archive and restore CLI commands.

Consolidates common error handling and validation patterns across
archive/restore commands for issues, milestones, and projects.
"""

from rich.console import Console

from roadmap.adapters.cli.cli_error_handlers import handle_cli_error
from roadmap.common.console import get_console


def handle_archive_parse_error(
    error: Exception,
    entity_type: str,
    entity_id: str,
    archive_dir: str,
    console: Console | None = None,
    extra_context: dict | None = None,
) -> None:
    """Handle errors when parsing archived entity files.

    Provides consistent error handling across archive/restore commands.

    Args:
        error: The exception that occurred
        entity_type: Type of entity ("issue", "milestone", "project")
        entity_id: ID or name of the entity
        archive_dir: Path to the archive directory
        console: Optional console instance (uses default if not provided)
        extra_context: Optional additional context dict to merge with base context
    """
    if console is None:
        console = get_console()

    context = {"archive_dir": str(archive_dir)}
    if extra_context:
        context.update(extra_context)

    handle_cli_error(
        error=error,
        operation=f"parse_archived_{entity_type}",
        entity_type=entity_type,
        entity_id=entity_id,
        context=context,
        fatal=False,
    )
    console.print(f"  • {entity_id} (parse error)", style="red")


def handle_restore_parse_error(
    error: Exception,
    entity_type: str,
    entity_id: str,
    archive_dir: str,
    console: Console | None = None,
    extra_context: dict | None = None,
) -> None:
    """Handle errors when parsing files during restore.

    Provides consistent error handling across restore commands.

    Args:
        error: The exception that occurred
        entity_type: Type of entity ("issue", "milestone", "project")
        entity_id: ID or name of the entity
        archive_dir: Path to the archive directory
        console: Optional console instance (uses default if not provided)
        extra_context: Optional additional context dict to merge with base context
    """
    if console is None:
        console = get_console()

    context = {"archive_dir": str(archive_dir)}
    if extra_context:
        context.update(extra_context)

    handle_cli_error(
        error=error,
        operation=f"restore_{entity_type}",
        entity_type=entity_type,
        entity_id=entity_id,
        context=context,
        fatal=False,
    )
    console.print(f"  • {entity_id} (restore error)", style="red")
