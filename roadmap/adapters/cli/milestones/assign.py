"""Assign issue to milestone command."""

import click

from roadmap.adapters.cli.cli_error_handlers import handle_cli_error
from roadmap.adapters.cli.helpers import require_initialized
from roadmap.common.console import get_console
from roadmap.common.formatters import format_operation_failure, format_operation_success
from roadmap.infrastructure.logging import (
    log_command,
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
            extra_details = {"Milestone": milestone_name}
            lines = format_operation_success(
                "✅", "Assigned", "", issue_id, None, extra_details
            )
            for line in lines:
                console.print(line, style="green")
        else:
            lines = format_operation_failure(
                "Assign", issue_id, "Issue or milestone not found"
            )
            for line in lines:
                console.print(line, style="bold red")
            raise click.Abort()
    except Exception as e:
        handle_cli_error(
            error=e,
            operation="milestone_assign",
            entity_type="milestone",
            entity_id=milestone_name,
            context={"issue_id": issue_id, "milestone_name": milestone_name},
            fatal=True,
        )
        lines = format_operation_failure("Assign", issue_id, str(e))
        for line in lines:
            console.print(line, style="bold red")
