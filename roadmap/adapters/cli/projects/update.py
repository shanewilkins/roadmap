"""Update project command."""

from datetime import datetime

import click

from roadmap.adapters.cli.helpers import require_initialized
from roadmap.common.console import get_console
from roadmap.infrastructure.logging import (
    log_command,
    log_error_with_context,
    track_database_operation,
)

console = get_console()


def _validate_priority(priority):
    """Validate and convert priority string to enum."""
    from roadmap.core.domain import Priority

    try:
        return Priority(priority.upper())
    except ValueError:
        console.print(
            f"❌ Invalid priority: {priority}. Use: critical, high, medium, low",
            style="bold red",
        )
        return None


def _validate_status(status):
    """Validate and convert status string to enum."""
    from roadmap.core.domain.project import ProjectStatus

    status_map = {
        "planning": ProjectStatus.PLANNING,
        "active": ProjectStatus.ACTIVE,
        "on-hold": ProjectStatus.ON_HOLD,
        "completed": ProjectStatus.COMPLETED,
        "cancelled": ProjectStatus.CANCELLED,
    }

    if status not in status_map:
        console.print(
            f"❌ Invalid status: {status}",
            style="bold red",
        )
        return None

    return status_map[status]


def _parse_date(date_str, field_name):
    """Parse date string in YYYY-MM-DD format."""
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        console.print(
            f"❌ Invalid {field_name} format. Use YYYY-MM-DD (e.g., 2025-12-31)",
            style="bold red",
        )
        return None


def _add_basic_updates(updates, name, description, owner, estimated_hours):
    """Add basic field updates to updates dict."""
    if name:
        updates["name"] = name
    if description:
        updates["description"] = description
    if owner:
        updates["owner"] = owner
    if estimated_hours is not None:
        updates["estimated_hours"] = estimated_hours


def _add_priority_status_updates(updates, priority, status):
    """Add priority and status updates with validation."""
    if priority:
        priority_enum = _validate_priority(priority)
        if priority_enum is None:
            return False
        updates["priority"] = priority_enum

    if status:
        status_enum = _validate_status(status)
        if status_enum is None:
            return False
        updates["status"] = status_enum

    return True


def _add_date_updates(
    updates, start_date, target_end_date, clear_start_date, clear_target_date
):
    """Add date updates with validation and clearing."""
    if clear_start_date:
        updates["start_date"] = None
    elif start_date:
        parsed_date = _parse_date(start_date, "start date")
        if parsed_date is None:
            return False
        updates["start_date"] = parsed_date

    if clear_target_date:
        updates["target_end_date"] = None
    elif target_end_date:
        parsed_date = _parse_date(target_end_date, "target end date")
        if parsed_date is None:
            return False
        updates["target_end_date"] = parsed_date

    return True


def _add_milestone_updates(updates, add_milestone, remove_milestone, project, core):
    """Add milestone updates to project."""
    if not (add_milestone or remove_milestone):
        return

    current_milestones = set(project.milestones)

    for milestone_name in add_milestone:
        if not core.get_milestone(milestone_name):
            console.print(
                f"⚠️  Warning: Milestone '{milestone_name}' not found, adding anyway",
                style="yellow",
            )
        current_milestones.add(milestone_name)

    for milestone_name in remove_milestone:
        current_milestones.discard(milestone_name)

    updates["milestones"] = list(current_milestones)


def _build_updates_dict(
    name,
    description,
    owner,
    priority,
    status,
    start_date,
    target_end_date,
    estimated_hours,
    clear_start_date,
    clear_target_date,
    project,
    core,
    add_milestone,
    remove_milestone,
):
    """Build dictionary of updates from provided options."""
    updates = {}

    _add_basic_updates(updates, name, description, owner, estimated_hours)

    if not _add_priority_status_updates(updates, priority, status):
        return None

    if not _add_date_updates(
        updates, start_date, target_end_date, clear_start_date, clear_target_date
    ):
        return None

    _add_milestone_updates(updates, add_milestone, remove_milestone, project, core)

    return updates


def _display_basic_updates(updated_project, updates):
    """Display basic field updates."""
    if "description" in updates:
        console.print(
            f"   Description: {updated_project.description[:60]}...", style="cyan"
        )

    if "owner" in updates:
        console.print(f"   Owner: {updated_project.owner}", style="cyan")

    if "priority" in updates:
        console.print(f"   Priority: {updated_project.priority.value}", style="cyan")

    if "status" in updates:
        console.print(f"   Status: {updated_project.status.value}", style="cyan")

    if "estimated_hours" in updates:
        console.print(
            f"   Estimated Hours: {updated_project.estimated_hours}", style="cyan"
        )


def _display_date_updates(updated_project, updates):
    """Display date field updates."""
    if "start_date" in updates:
        if updated_project.start_date:
            console.print(
                f"   Start Date: {updated_project.start_date.strftime('%Y-%m-%d')}",
                style="cyan",
            )
        else:
            console.print("   Start Date: Cleared", style="dim")

    if "target_end_date" in updates:
        if updated_project.target_end_date:
            console.print(
                f"   Target End Date: {updated_project.target_end_date.strftime('%Y-%m-%d')}",
                style="cyan",
            )
        else:
            console.print("   Target End Date: Cleared", style="dim")


def _display_milestone_updates(updated_project, updates):
    """Display milestone updates."""
    if "milestones" in updates:
        console.print(
            f"   Milestones ({len(updated_project.milestones)}): {', '.join(updated_project.milestones)}",
            style="cyan",
        )


def _display_update_results(updated_project, updates):
    """Display formatted results of project update."""
    console.print(f"✅ Updated project: {updated_project.name}", style="bold green")
    _display_basic_updates(updated_project, updates)
    _display_date_updates(updated_project, updates)
    _display_milestone_updates(updated_project, updates)


@click.command("update")
@click.argument("project_id")
@click.option("--name", help="Update project name")
@click.option("--description", "-d", help="Update project description")
@click.option("--owner", "-o", help="Update project owner")
@click.option(
    "--priority",
    "-p",
    type=click.Choice(["critical", "high", "medium", "low"]),
    help="Update project priority",
)
@click.option(
    "--status",
    "-s",
    type=click.Choice(["planning", "active", "on-hold", "completed", "cancelled"]),
    help="Update project status",
)
@click.option(
    "--start-date",
    help="Update start date (YYYY-MM-DD format)",
)
@click.option(
    "--target-end-date",
    help="Update target end date (YYYY-MM-DD format)",
)
@click.option(
    "--estimated-hours",
    "-e",
    type=float,
    help="Update estimated hours",
)
@click.option(
    "--add-milestone",
    "-m",
    multiple=True,
    help="Add milestone(s) to project (can be specified multiple times)",
)
@click.option(
    "--remove-milestone",
    multiple=True,
    help="Remove milestone(s) from project (can be specified multiple times)",
)
@click.option("--clear-start-date", is_flag=True, help="Clear the start date")
@click.option("--clear-target-date", is_flag=True, help="Clear the target end date")
@click.pass_context
@require_initialized
@log_command("project_update", entity_type="project", track_duration=True)
def update_project(
    ctx: click.Context,
    project_id: str,
    name: str,
    description: str,
    owner: str,
    priority: str,
    status: str,
    start_date: str,
    target_end_date: str,
    estimated_hours: float,
    add_milestone: tuple,
    remove_milestone: tuple,
    clear_start_date: bool,
    clear_target_date: bool,
):
    """Update an existing project.

    Examples:
        roadmap project update abc123 --name "New Project Name"
        roadmap project update abc123 --status active --priority high
        roadmap project update abc123 --add-milestone "v1.0" --add-milestone "v2.0"
        roadmap project update abc123 --owner jane --estimated-hours 120
    """
    core = ctx.obj["core"]

    try:
        project = core.get_project(project_id)
        if not project:
            console.print(f"❌ Project not found: {project_id}", style="bold red")
            return

        updates = _build_updates_dict(
            name,
            description,
            owner,
            priority,
            status,
            start_date,
            target_end_date,
            estimated_hours,
            clear_start_date,
            clear_target_date,
            project,
            core,
            add_milestone,
            remove_milestone,
        )

        if updates is None:
            return

        if not updates:
            console.print("❌ No updates specified", style="bold red")
            console.print(
                "\n💡 Use options like --name, --status, --priority, etc. See --help for details",
                style="dim",
            )
            return

        with track_database_operation(
            "update", "project", entity_id=project_id, warn_threshold_ms=2000
        ):
            updated_project = core.update_project(project_id, **updates)

        if not updated_project:
            console.print(
                f"❌ Failed to update project: {project_id}", style="bold red"
            )
            return

        _display_update_results(updated_project, updates)

    except Exception as e:
        log_error_with_context(
            e,
            operation="project_update",
            entity_type="project",
            entity_id=project_id,
        )
        console.print(f"❌ Failed to update project: {e}", style="bold red")
        import traceback

        console.print(traceback.format_exc(), style="dim")
