"""Close project command - sets status to closed."""

import shutil
from pathlib import Path

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

    This command marks a project as completed and moves its file to the archive.
    All issues in the project should be closed before closing the project.
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
            # Move project file to archive directory
            try:
                # Build source and target paths
                projects_dir = Path(".roadmap/projects").resolve()
                archive_dir = Path(".roadmap/archive/projects/closed").resolve()

                # Create archive directory if it doesn't exist
                archive_dir.mkdir(parents=True, exist_ok=True)

                # Find the project file
                project_filename = updated_project.filename
                source_path = projects_dir / project_filename

                # Move to archive if file exists
                if source_path.exists():
                    target_path = archive_dir / project_filename
                    shutil.move(str(source_path), str(target_path))
            except Exception as archive_error:
                # Log archive error but don't fail the operation
                console.print(
                    f"⚠️  Warning: Could not move project file to archive: {archive_error}",
                    style="yellow",
                )

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
