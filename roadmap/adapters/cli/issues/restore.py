"""Restore issue command - move archived issues back to active."""

import click

from roadmap.adapters.cli.cli_command_helpers import require_initialized
from roadmap.adapters.cli.issues.restore_class import IssueRestore
from roadmap.common.console import get_console
from roadmap.infrastructure.logging import (
    log_command,
    verbose_output,
)


@click.command()
@click.argument("issue_id", required=False)
@click.option(
    "--all",
    is_flag=True,
    help="Restore all archived issues",
)
@click.option(
    "--status",
    type=click.Choice(["todo", "in-progress", "blocked", "review", "closed"]),
    help="Set status when restoring (default: keep current status)",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Preview what would be restored without actually doing it",
)
@click.option(
    "--force",
    is_flag=True,
    help="Skip confirmation prompt",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Show detailed debug information",
)
@click.pass_context
@verbose_output
@log_command("issue_restore", entity_type="issue", track_duration=True)
@require_initialized
def restore_issue(
    ctx: click.Context,
    issue_id: str | None,
    all: bool,
    status: str | None,
    dry_run: bool,
    force: bool,
    verbose: bool,  # noqa: F841
):
    """Restore an archived issue back to active issues.

    This moves an issue from .roadmap/archive/issues/ back to
    .roadmap/issues/, making it active again. Optionally update
    the status when restoring.

    Examples:
        roadmap issue restore 8a00a17e
        roadmap issue restore 8a00a17e --status todo
        roadmap issue restore --all
        roadmap issue restore 8a00a17e --dry-run
    """
    core = ctx.obj["core"]
    console = get_console()

    restore = IssueRestore(core, console)

    if not issue_id and not all:
        console.print(
            "❌ Error: Specify an issue ID or use --all",
            style="bold red",
        )
        ctx.exit(1)

    if issue_id and all:
        console.print(
            "❌ Error: Cannot specify issue ID with --all",
            style="bold red",
        )
        ctx.exit(1)

    try:
        restore.execute(
            entity_id=issue_id,
            all=all,
            status=status,
            dry_run=dry_run,
            force=force,
        )
    except Exception as e:
        console.print(f"❌ Restore operation failed: {str(e)}", style="bold red")
        ctx.exit(1)
