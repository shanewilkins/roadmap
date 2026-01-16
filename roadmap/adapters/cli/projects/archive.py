"""Archive project command - move completed projects to archive."""

import click

from roadmap.adapters.cli.cli_command_helpers import require_initialized
from roadmap.adapters.cli.projects.archive_class import ProjectArchive
from roadmap.common.console import get_console
from roadmap.common.logging import (
    log_command,
    verbose_output,
)


@click.command()
@click.argument("project_name", required=False)
@click.option(
    "--all-closed",
    is_flag=True,
    help="Archive all closed projects",
)
@click.option(
    "--list",
    "list_archived",
    is_flag=True,
    help="List archived projects",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Preview what would be archived without actually doing it",
)
@click.option(
    "--force",
    is_flag=True,
    help="Skip confirmation prompt",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Show detailed debug information",
)
@click.pass_context
@verbose_output
@log_command("project_archive", entity_type="project", track_duration=True)
@require_initialized
def archive_project(
    ctx: click.Context,
    project_name: str | None,
    all_closed: bool,
    list_archived: bool,
    dry_run: bool,
    force: bool,
    verbose: bool,  # noqa: F841
):
    """Archive a project by moving it to .roadmap/archive/projects/.

    This is a non-destructive operation that preserves project data while
    cleaning up the active workspace.

    Examples:
        roadmap project archive "Project Name"
        roadmap project archive --all-closed
        roadmap project archive --list
    """
    core = ctx.obj["core"]
    console = get_console()

    archive = ProjectArchive(core, console)

    if list_archived:
        from pathlib import Path

        from roadmap.adapters.persistence.parser import ProjectParser

        roadmap_dir = Path.cwd() / ".roadmap"
        archive_dir = roadmap_dir / "archive" / "projects"

        if not archive_dir.exists():
            console.print("📋 No archived projects.", style="yellow")
            return

        archived_files = list(archive_dir.glob("*.md"))
        if not archived_files:
            console.print("📋 No archived projects.", style="yellow")
            return

        console.print("\n📦 Archived Projects:\n", style="bold blue")
        for file_path in sorted(archived_files):
            try:
                project = ProjectParser.parse_project_file(file_path)
                console.print(f"  • {project.name} ({project.status})", style="cyan")
            except Exception:
                console.print(
                    f"  • {file_path.name} (error reading file)", style="yellow"
                )
        return

    # Validate arguments
    if not project_name and not all_closed:
        console.print(
            "❌ Error: Specify a project name or use --all-closed",
            style="bold red",
        )
        ctx.exit(1)

    if project_name and all_closed:
        console.print(
            "❌ Error: Specify only one of: project name or --all-closed",
            style="bold red",
        )
        ctx.exit(1)

    try:
        archive.execute(
            entity_id=project_name,
            all_closed=all_closed,
            dry_run=dry_run,
            force=force,
        )
    except Exception as e:
        console.print(f"❌ Archive operation failed: {str(e)}", style="bold red")
        ctx.exit(1)
