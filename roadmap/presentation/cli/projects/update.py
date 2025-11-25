"""Update project command."""

from datetime import datetime

import click

from roadmap.presentation.cli.error_logging import log_error_with_context
from roadmap.presentation.cli.logging_decorators import log_command
from roadmap.shared.console import get_console

console = get_console()


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

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return

    try:
        # Check if project exists
        project = core.get_project(project_id)
        if not project:
            console.print(f"❌ Project not found: {project_id}", style="bold red")
            return

        # Build update dict
        updates = {}

        if name:
            updates["name"] = name

        if description:
            updates["description"] = description

        if owner:
            updates["owner"] = owner

        if priority:
            from roadmap.domain import Priority

            try:
                updates["priority"] = Priority(priority.upper())
            except ValueError:
                console.print(
                    f"❌ Invalid priority: {priority}. Use: critical, high, medium, low",
                    style="bold red",
                )
                return

        if status:
            from roadmap.domain.project import ProjectStatus

            try:
                # Map status to enum
                status_map = {
                    "planning": ProjectStatus.PLANNING,
                    "active": ProjectStatus.ACTIVE,
                    "on-hold": ProjectStatus.ON_HOLD,
                    "completed": ProjectStatus.COMPLETED,
                    "cancelled": ProjectStatus.CANCELLED,
                }
                updates["status"] = status_map[status]
            except KeyError:
                console.print(
                    f"❌ Invalid status: {status}",
                    style="bold red",
                )
                return

        if estimated_hours is not None:
            updates["estimated_hours"] = estimated_hours

        # Handle date updates
        if clear_start_date:
            updates["start_date"] = None
        elif start_date:
            try:
                parsed_date = datetime.strptime(start_date, "%Y-%m-%d")
                updates["start_date"] = parsed_date
            except ValueError:
                console.print(
                    "❌ Invalid start date format. Use YYYY-MM-DD (e.g., 2025-12-31)",
                    style="bold red",
                )
                return

        if clear_target_date:
            updates["target_end_date"] = None
        elif target_end_date:
            try:
                parsed_date = datetime.strptime(target_end_date, "%Y-%m-%d")
                updates["target_end_date"] = parsed_date
            except ValueError:
                console.print(
                    "❌ Invalid target end date format. Use YYYY-MM-DD (e.g., 2025-12-31)",
                    style="bold red",
                )
                return

        # Handle milestone updates
        if add_milestone or remove_milestone:
            current_milestones = set(project.milestones)

            for milestone_name in add_milestone:
                # Verify milestone exists
                if not core.get_milestone(milestone_name):
                    console.print(
                        f"⚠️  Warning: Milestone '{milestone_name}' not found, adding anyway",
                        style="yellow",
                    )
                current_milestones.add(milestone_name)

            for milestone_name in remove_milestone:
                current_milestones.discard(milestone_name)

            updates["milestones"] = list(current_milestones)

        if not updates:
            console.print("❌ No updates specified", style="bold red")
            console.print(
                "\n💡 Use options like --name, --status, --priority, etc. See --help for details",
                style="dim",
            )
            return

        # Update the project
        updated_project = core.update_project(project_id, **updates)

        if not updated_project:
            console.print(
                f"❌ Failed to update project: {project_id}", style="bold red"
            )
            return

        # Display success message with updated values
        console.print(f"✅ Updated project: {updated_project.name}", style="bold green")

        if "description" in updates:
            console.print(
                f"   Description: {updated_project.description[:60]}...", style="cyan"
            )

        if "owner" in updates:
            console.print(f"   Owner: {updated_project.owner}", style="cyan")

        if "priority" in updates:
            console.print(
                f"   Priority: {updated_project.priority.value}", style="cyan"
            )

        if "status" in updates:
            console.print(f"   Status: {updated_project.status.value}", style="cyan")

        if "estimated_hours" in updates:
            console.print(
                f"   Estimated Hours: {updated_project.estimated_hours}", style="cyan"
            )

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

        if add_milestone or remove_milestone:
            console.print(
                f"   Milestones ({len(updated_project.milestones)}): {', '.join(updated_project.milestones)}",
                style="cyan",
            )

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
