"""Create milestone command."""

from datetime import datetime

import click

from roadmap.presentation.cli.logging_decorators import log_command
from roadmap.shared.console import get_console

console = get_console()


@click.command("create")
@click.argument("name")
@click.option("--description", "-d", default="", help="Milestone description")
@click.option("--due-date", help="Due date for milestone (YYYY-MM-DD format)")
@click.pass_context
@log_command("milestone_create", entity_type="milestone", track_duration=True)
def create_milestone(ctx: click.Context, name: str, description: str, due_date: str):
    """Create a new milestone."""
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return

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
        milestone = core.create_milestone(
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
        console.print(f"❌ Failed to create milestone: {e}", style="bold red")
