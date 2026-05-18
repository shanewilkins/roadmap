"""Close project command - sets status to closed without archiving."""

import click

from roadmap.adapters.cli.cli_command_helpers import require_initialized
from roadmap.adapters.cli.cli_error_handlers import handle_cli_error
from roadmap.common.console import get_console
from roadmap.common.formatters.text.operations import (
    format_operation_failure,
    format_operation_success,
)
from roadmap.common.logging import (
    log_command,
    track_database_operation,
)
from roadmap.core.domain import ProjectStatus

console = get_console()


@click.command("close")
@click.argument("project_id")
@click.option("--force", is_flag=True, help="Skip confirmation prompt")
@click.pass_context
@require_initialized
@log_command("project_close", entity_type="project", track_duration=True)
def close_project(ctx: click.Context, project_id: str, force: bool):
    """Close a project (sets status to closed).

    This command marks a project as completed while keeping its file active.
    Use `roadmap project archive` as the separate cleanup step when the
    project file should move under `.roadmap/archive/projects/`.
    """
    core = ctx.obj["core"]

    try:
        # Check if project exists
        project = core.projects.get(project_id)
        if not project:
            lines = format_operation_failure("Close", project_id, "Project not found")
            for line in lines:
                console.print(line, style="bold red")
            raise click.Abort()

        # Confirm closure
        if not force:
            if not click.confirm(f"Close project '{project.name}'?"):
                console.print("❌ Project close cancelled.", style="yellow")
                return

        # Close project in database
        with track_database_operation(
            "update", "project", entity_id=project_id, warn_threshold_ms=2000
        ):
            updated_project = core.projects.update(
                project_id, status=ProjectStatus.COMPLETED
            )

        if updated_project:
            extra_details = {"Status": "Closed"}
            lines = format_operation_success(
                emoji="✅",
                action="Closed",
                entity_title=updated_project.name,
                entity_id=project_id,
                extra_details=extra_details,
            )
            for line in lines:
                console.print(line, style="bold green" if "Closed" in line else "cyan")
        else:
            lines = format_operation_failure(
                action="close",
                entity_id=project_id,
                error="Failed to update status",
            )
            for line in lines:
                console.print(line, style="bold red")

    except Exception as e:
        handle_cli_error(
            error=e,
            operation="close_project",
            entity_type="project",
            entity_id=project_id,
            context={"force": force},
            fatal=True,
        )
        lines = format_operation_failure(
            action="close",
            entity_id=project_id,
            error=str(e),
        )
        for line in lines:
            console.print(line, style="bold red")
