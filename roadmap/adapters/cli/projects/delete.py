"""Delete project command."""

import click

from roadmap.adapters.cli.error_logging import log_error_with_context
from roadmap.adapters.cli.logging_decorators import log_command
from roadmap.adapters.cli.performance_tracking import (
    track_file_operation,
)
from roadmap.common.console import get_console

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
            console.print(f"❌ Project {project_id} not found", style="bold red")
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
        console.print(
            f"✅ Deleted project: {project_name} ({project_id})", style="bold green"
        )

    except Exception as e:
        log_error_with_context(
            e,
            operation="project_delete",
            entity_type="project",
            entity_id=project_id,
        )
        console.print(f"❌ Failed to delete project: {e}", style="bold red")
