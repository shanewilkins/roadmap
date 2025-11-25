"""Close milestone command."""

import click

from roadmap.presentation.cli.error_logging import log_error_with_context
from roadmap.presentation.cli.logging_decorators import log_command
from roadmap.presentation.cli.performance_tracking import track_database_operation
from roadmap.shared.console import get_console

console = get_console()


@click.command("close")
@click.argument("milestone_name")
@click.option("--force", is_flag=True, help="Skip confirmation prompt")
@click.pass_context
@log_command("milestone_close", entity_type="milestone", track_duration=True)
def close_milestone(ctx: click.Context, milestone_name: str, force: bool):
    """Convenience command to mark a milestone as closed."""
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return

    try:
        if not force:
            if not click.confirm(
                f"Are you sure you want to close milestone '{milestone_name}'?"
            ):
                console.print("❌ Milestone close cancelled.", style="yellow")
                return

        from roadmap.domain import MilestoneStatus

        with track_database_operation("update", "milestone"):
            success = core.update_milestone(
                milestone_name, status=MilestoneStatus.CLOSED
            )
        if success:
            console.print(f"✅ Closed milestone: {milestone_name}", style="bold green")
        else:
            console.print(f"❌ Milestone not found: {milestone_name}", style="bold red")
    except Exception as e:
        log_error_with_context(
            e,
            operation="milestone_close",
            entity_type="milestone",
            additional_context={"milestone_name": milestone_name},
        )
        console.print(f"❌ Failed to close milestone: {e}", style="bold red")
