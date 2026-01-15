"""Restore milestone command - move archived milestones back to active."""

import click

from roadmap.adapters.cli.cli_command_helpers import require_initialized
from roadmap.adapters.cli.milestones.restore_class import MilestoneRestore
from roadmap.common.console import get_console
from roadmap.infrastructure.logging import (
    log_command,
    verbose_output,
)


@click.command()
@click.argument("milestone_name", required=False)
@click.option(
    "--all",
    is_flag=True,
    help="Restore all archived milestones",
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
@log_command("milestone_restore", entity_type="milestone", track_duration=True)
@require_initialized
def restore_milestone(
    ctx: click.Context,
    milestone_name: str | None,
    all: bool,
    dry_run: bool,
    force: bool,
    verbose: bool,  # noqa: F841
):
    """Restore an archived milestone back to active milestones.

    This moves a milestone from .roadmap/archive/milestones/ back to
    .roadmap/milestones/, making it active again.

    Examples:
        roadmap milestone restore "v1.0"
        roadmap milestone restore --all
        roadmap milestone restore "v1.0" --dry-run
    """
    core = ctx.obj["core"]
    console = get_console()

    restore = MilestoneRestore(core, console)

    if not milestone_name and not all:
        console.print(
            "❌ Error: Specify a milestone name or use --all",
            style="bold red",
        )
        ctx.exit(1)

    if milestone_name and all:
        console.print(
            "❌ Error: Cannot specify milestone name with --all",
            style="bold red",
        )
        ctx.exit(1)

    try:
        restore.execute(
            entity_id=milestone_name,
            all=all,
            dry_run=dry_run,
            force=force,
        )
    except Exception as e:
        console.print(f"❌ Restore operation failed: {str(e)}", style="bold red")
        ctx.exit(1)
