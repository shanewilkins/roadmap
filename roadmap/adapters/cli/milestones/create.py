"""Create milestone command."""

from datetime import datetime

import click

from roadmap.adapters.cli.helpers import require_initialized
from roadmap.common.console import get_console
from roadmap.infrastructure.logging import (
    log_command,
    log_error_with_context,
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
        console.print(f"✅ Created milestone: {milestone.name}", style="bold green")
        console.print(f"   Description: {milestone.description}", style="cyan")
        if milestone.due_date:
            console.print(
                f"   Due Date: {milestone.due_date.strftime('%Y-%m-%d')}",
                style="yellow",
            )
        console.print(f"   File: .roadmap/milestones/{milestone.filename}", style="dim")
    except Exception as e:
        log_error_with_context(
            e,
            operation="milestone_create",
            entity_type="milestone",
            additional_context={"name": name},
        )
        console.print(f"❌ Failed to create milestone: {e}", style="bold red")
