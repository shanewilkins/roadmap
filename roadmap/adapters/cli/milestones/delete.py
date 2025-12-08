"""Delete milestone command."""

import click

from roadmap.adapters.cli.helpers import require_initialized
from roadmap.common.console import get_console
from roadmap.common.formatters import format_operation_failure, format_operation_success
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
            lines = format_operation_success(
                emoji="✅",
                action="Deleted",
                entity_title=milestone_name,
            )
            for line in lines:
                console.print(line, style="bold green" if "Deleted" in line else "cyan")
        else:
            lines = format_operation_failure(
                action="delete",
                entity_id=milestone_name,
                error="Milestone not found",
            )
            for line in lines:
                console.print(line, style="bold red")
    except Exception as e:
        log_error_with_context(
            e,
            operation="milestone_delete",
            entity_type="milestone",
            additional_context={"milestone_name": milestone_name},
        )
        lines = format_operation_failure(
            action="delete",
            entity_id=milestone_name,
            error=str(e),
        )
        for line in lines:
            console.print(line, style="bold red")
