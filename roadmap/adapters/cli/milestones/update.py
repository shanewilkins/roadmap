"""Update milestone command."""

from datetime import datetime

import click

from roadmap.common.console import get_console
from roadmap.infrastructure.logging import (
    log_command,
    log_error_with_context,
    track_database_operation,
)

console = get_console()


def _parse_due_date(due_date_str):
    """Parse due date string in YYYY-MM-DD format."""
    if due_date_str.lower() == "clear":
        return None
    try:
        return datetime.strptime(due_date_str, "%Y-%m-%d")
    except ValueError:
        console.print(
            "❌ Invalid due date format. Use YYYY-MM-DD (e.g., 2024-12-31)",
            style="bold red",
        )
        return "invalid"


def _convert_status_to_enum(status_str):
    """Convert CLI status string to MilestoneStatus enum."""
    try:
        from roadmap.core.domain import MilestoneStatus

        return MilestoneStatus(status_str)
    except Exception:
        return status_str


def _build_updates_dict(name, description, due_date, status, clear_due_date):
    """Build dictionary of updates from options."""
    updates = {}

    if name:
        updates["name"] = name
    if description:
        updates["description"] = description

    if clear_due_date:
        updates["due_date"] = None
    elif due_date:
        parsed_date = _parse_due_date(due_date)
        if parsed_date == "invalid":
            return None
        updates["due_date"] = parsed_date

    if status:
        updates["status"] = _convert_status_to_enum(status)

    return updates if updates else None


def _display_update_results(updated_milestone, updates, clear_due_date):
    """Display formatted results of milestone update."""
    console.print(f"✅ Updated milestone: {updated_milestone.name}", style="bold green")
    if "description" in updates:
        console.print(f"   Description: {updated_milestone.description}", style="cyan")
    if "due_date" in updates:
        if updated_milestone.due_date:
            console.print(
                f"   Due Date: {updated_milestone.due_date.strftime('%Y-%m-%d')}",
                style="yellow",
            )
        elif clear_due_date:
            console.print("   Due Date: Cleared", style="dim")


@click.command("update")
@click.argument("milestone_name")
@click.option("--name", help="Update milestone name")
@click.option("--description", "-d", help="Update milestone description")
@click.option("--due-date", help="Update due date (YYYY-MM-DD format)")
@click.option(
    "--status",
    type=click.Choice(["open", "closed"]),
    help="Set milestone status (open|closed)",
)
@click.option("--clear-due-date", is_flag=True, help="Clear the due date")
@click.pass_context
@log_command("milestone_update", entity_type="milestone", track_duration=True)
def update_milestone(
    ctx: click.Context,
    milestone_name: str,
    name: str,
    description: str,
    due_date: str,
    status: str,
    clear_due_date: bool,
):
    """Update an existing milestone."""
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return

    try:
        milestone = core.milestones.get(milestone_name)
        if not milestone:
            console.print(f"❌ Milestone not found: {milestone_name}", style="bold red")
            return

        updates = _build_updates_dict(
            name, description, due_date, status, clear_due_date
        )
        if updates is None:
            return

        if not updates:
            console.print("❌ No updates specified", style="bold red")
            return

        with track_database_operation("update", "milestone", warn_threshold_ms=2000):
            success = core.milestones.update(milestone_name, **updates)

        if not success:
            console.print(
                f"❌ Failed to update milestone: {milestone_name}", style="bold red"
            )
            return

        updated_milestone = core.milestones.get(updates.get("name", milestone_name))
        _display_update_results(updated_milestone, updates, clear_due_date)

    except Exception as e:
        log_error_with_context(
            e,
            operation="milestone_update",
            entity_type="milestone",
            additional_context={"milestone_name": milestone_name},
        )
        console.print(f"❌ Failed to update milestone: {e}", style="bold red")
