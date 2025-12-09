"""Create milestone command."""

from datetime import datetime

import click

from roadmap.adapters.cli.cli_error_handlers import handle_cli_error
from roadmap.adapters.cli.helpers import require_initialized
from roadmap.common.console import get_console
from roadmap.common.formatters import format_operation_failure, format_operation_success
from roadmap.infrastructure.logging import (
    log_command,
    track_database_operation,
    verbose_output,
)

console = get_console()


@click.command("create")
@click.argument("name")
@click.option("--description", "-d", default="", help="Milestone description")
@click.option("--due-date", help="Due date for milestone (YYYY-MM-DD format)")
@click.option("--verbose", "-v", is_flag=True, help="Show verbose output")
@click.pass_context
@require_initialized
@verbose_output
@log_command("milestone_create", entity_type="milestone", track_duration=True)
def create_milestone(
    ctx: click.Context, name: str, description: str, due_date: str, verbose: bool
):
    """Create a new milestone."""
    core = ctx.obj["core"]

    # Parse due date if provided
    parsed_due_date = None
    if due_date:
        try:
            parsed_due_date = datetime.strptime(due_date, "%Y-%m-%d")
        except ValueError:
            console.print(
                "❌ Invalid due date format. Use YYYY-MM-DD (e.g., 2024-12-31)",
                style="bold red",
            )
            return

    try:
        with track_database_operation("create", "milestone", warn_threshold_ms=2000):
            milestone = core.milestones.create(
                name=name, description=description, due_date=parsed_due_date
            )
        extra_details = {"Description": milestone.description}
        if milestone.due_date:
            extra_details["Due Date"] = milestone.due_date.strftime("%Y-%m-%d")
        extra_details["File"] = f".roadmap/milestones/{milestone.filename}"

        lines = format_operation_success(
            emoji="✅",
            action="Created",
            entity_title=milestone.name,
            entity_id=milestone.id,
            extra_details=extra_details,
        )
        for line in lines:
            console.print(line, style="bold green" if "Created" in line else "cyan")
    except Exception as e:
        handle_cli_error(
            error=e,
            operation="create_milestone",
            entity_type="milestone",
            entity_id="new",
            context={"name": name, "due_date": due_date},
            fatal=True,
        )
        lines = format_operation_failure(
            action="create",
            entity_id=name,
            error=str(e),
        )
        for line in lines:
            console.print(line, style="bold red")
