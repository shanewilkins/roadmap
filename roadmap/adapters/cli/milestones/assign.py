"""Assign issue to milestone command."""

import click

from roadmap.adapters.cli.helpers import require_initialized
from roadmap.common.console import get_console
from roadmap.infrastructure.logging import (
    log_command,
    log_error_with_context,
    track_database_operation,
)

console = get_console()


@click.command("assign")
@click.argument("issue_id")
@click.argument("milestone_name")
@click.pass_context
@require_initialized
@log_command("milestone_assign", entity_type="milestone", track_duration=True)
def assign_milestone(ctx: click.Context, issue_id: str, milestone_name: str):
    """Assign an issue to a milestone."""
    core = ctx.obj["core"]

    try:
        with track_database_operation("update", "milestone", warn_threshold_ms=2000):
            success = core.issues.assign_to_milestone(issue_id, milestone_name)

        if success:
            console.print(
                f"✅ Assigned issue {issue_id} to milestone '{milestone_name}'",
                style="bold green",
            )
        else:
            console.print(
                f"❌ Failed to assign issue {issue_id} to milestone '{milestone_name}' - issue or milestone not found",
                style="bold red",
            )
    except Exception as e:
        log_error_with_context(
            e,
            operation="milestone_assign",
            entity_type="milestone",
            additional_context={"issue_id": issue_id, "milestone_name": milestone_name},
        )
        console.print(f"❌ Failed to assign issue: {e}", style="bold red")
