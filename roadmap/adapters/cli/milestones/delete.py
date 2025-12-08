"""Delete milestone command."""

import click

from roadmap.adapters.cli.helpers import require_initialized
from roadmap.common.console import get_console
from roadmap.infrastructure.logging import (
    log_command,
    log_error_with_context,
    track_database_operation,
)

console = get_console()


@click.command("delete")
@click.argument("milestone_name")
@click.option("--force", is_flag=True, help="Skip confirmation prompt")
@click.pass_context
@require_initialized
@log_command("milestone_delete", entity_type="milestone", track_duration=True)
def delete_milestone(ctx: click.Context, milestone_name: str, force: bool):
    """Delete a milestone."""
    core = ctx.obj["core"]

    try:
        if not force:
            if not click.confirm(
                f"Are you sure you want to delete milestone '{milestone_name}'?"
            ):
                console.print("❌ Milestone deletion cancelled.", style="yellow")
                return

        with track_database_operation("delete", "milestone"):
            success = core.milestones.delete(milestone_name)
        if success:
            console.print(f"✅ Deleted milestone: {milestone_name}", style="bold green")
        else:
            console.print(f"❌ Milestone not found: {milestone_name}", style="bold red")
    except Exception as e:
        log_error_with_context(
            e,
            operation="milestone_delete",
            entity_type="milestone",
            additional_context={"milestone_name": milestone_name},
        )
        console.print(f"❌ Failed to delete milestone: {e}", style="bold red")
