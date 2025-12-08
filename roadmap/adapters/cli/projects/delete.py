"""Delete project command."""

import click

from roadmap.common.console import get_console
from roadmap.common.formatters import format_operation_failure, format_operation_success
from roadmap.infrastructure.logging import (
    log_command,
    log_error_with_context,
    track_file_operation,
)

console = get_console()


@click.command("delete")
@click.argument("project_id")
@click.option("--confirm", is_flag=True, help="Skip confirmation prompt")
@click.pass_context
@log_command("project_delete", entity_type="project", track_duration=True)
def delete_project(ctx: click.Context, project_id: str, confirm: bool):
    """Delete a project."""
    core = ctx.obj["core"]

    try:
        projects_dir = core.roadmap_dir / "projects"

        # Find project file
        project_file = None
        for file_path in projects_dir.rglob("*.md"):
            if file_path.name.startswith(project_id):
                project_file = file_path
                break

        if not project_file:
            lines = format_operation_failure("Delete", project_id, "Project not found")
            for line in lines:
                console.print(line, style="bold red")
            return

        # Get project name for confirmation
        content = project_file.read_text()
        project_name = "unknown"
        if content.startswith("---"):
            yaml_end = content.find("---", 3)
            if yaml_end != -1:
                import yaml

                yaml_content = content[3:yaml_end]
                metadata = yaml.safe_load(yaml_content)
                project_name = metadata.get("name", "unknown")

        # Confirmation
        if not confirm:
            response = click.confirm(
                f"Are you sure you want to delete project '{project_name}' ({project_id})?"
            )
            if not response:
                console.print("Deletion cancelled.", style="yellow")
                return

        # Delete file
        with track_file_operation("delete", str(project_file)):
            project_file.unlink()
        lines = format_operation_success("✅", "Deleted", project_name, project_id, None, None)
        for line in lines:
            console.print(line, style="green")

    except Exception as e:
        log_error_with_context(
            e,
            operation="project_delete",
            entity_type="project",
            entity_id=project_id,
        )
        lines = format_operation_failure("Delete", project_id, str(e))
        for line in lines:
            console.print(line, style="bold red")
