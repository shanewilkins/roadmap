"""Update milestone command."""

from datetime import datetime

import click

from roadmap.adapters.cli.cli_validators import parse_date, validate_milestone_status
from roadmap.adapters.cli.helpers import require_initialized
from roadmap.common.console import get_console
from roadmap.common.formatters import format_operation_failure, format_operation_success
from roadmap.infrastructure.logging import (
    log_command,
    log_error_with_context,
    track_database_operation,
)

console = get_console()


def _parse_due_date(due_date_str):
    """Parse due date string in YYYY-MM-DD format or 'clear' to remove."""
    if due_date_str.lower() == "clear":
        return None
    return parse_date(due_date_str, "due date")


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
        status_enum = validate_milestone_status(status)
        if status_enum is None:
            return False
        updates["status"] = status_enum

    return updates if updates else None


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
@require_initialized
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

    try:
        milestone = core.milestones.get(milestone_name)
        if not milestone:
            lines = format_operation_failure(
                action="update",
                entity_id=milestone_name,
                error="Milestone not found",
            )
            for line in lines:
                console.print(line, style="bold red")
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
            lines = format_operation_failure(
                action="update",
                entity_id=milestone_name,
                error="Failed to update milestone",
            )
            for line in lines:
                console.print(line, style="bold red")
            return

        updated_milestone = core.milestones.get(updates.get("name", milestone_name))

        # Build extra details for display
        extra_details = {}
        if "description" in updates:
            extra_details["Description"] = updated_milestone.description
        if "due_date" in updates:
            if updated_milestone.due_date:
                extra_details["Due Date"] = updated_milestone.due_date.strftime(
                    "%Y-%m-%d"
                )
            elif clear_due_date:
                extra_details["Due Date"] = "Cleared"

        lines = format_operation_success(
            emoji="✅",
            action="Updated",
            entity_title=updated_milestone.name,
            entity_id=updated_milestone.id,
            extra_details=extra_details if extra_details else None,
        )
        for line in lines:
            console.print(line, style="bold green" if "Updated" in line else "cyan")

    except Exception as e:
        log_error_with_context(
            e,
            operation="milestone_update",
            entity_type="milestone",
            additional_context={"milestone_name": milestone_name},
        )
        lines = format_operation_failure(
            action="update",
            entity_id=milestone_name,
            error=str(e),
        )
        for line in lines:
            console.print(line, style="bold red")
