"""Archive project command - move completed projects to archive."""

from pathlib import Path

import click
from rich.console import Console

from roadmap.infrastructure.persistence.parser import ProjectParser
from roadmap.presentation.cli.error_logging import log_error_with_context
from roadmap.presentation.cli.logging_decorators import log_command, verbose_output
from roadmap.shared.file_utils import ensure_directory_exists

console = Console()


@click.command()
@click.argument("project_name", required=False)
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
def archive_project(
    ctx: click.Context,
    project_name: str | None,
    list_archived: bool,
    dry_run: bool,
    force: bool,
    verbose: bool,
):
    """Archive a project by moving it to .roadmap/archive/projects/.

    This is a non-destructive operation that preserves project data while
    cleaning up the active workspace. Archived projects can be restored
    if needed.

    Examples:
        roadmap project archive "my-project"
        roadmap project archive --list
        roadmap project archive "my-project" --dry-run
    """
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.",
            style="bold red",
        )
        ctx.exit(1)

    # Handle --list option
    if list_archived:
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
        for file_path in archived_files:
            try:
                project = ProjectParser.parse_project_file(file_path)
                console.print(f"  • {project.name} ({project.status})", style="cyan")
            except Exception:
                console.print(f"  • {file_path.stem} (parse error)", style="red")
        return

    if not project_name:
        console.print(
            "❌ Error: Specify a project name or use --list",
            style="bold red",
        )
        ctx.exit(1)

    try:
        roadmap_dir = Path.cwd() / ".roadmap"
        archive_dir = roadmap_dir / "archive" / "projects"

        # Archive single project
        project = core.get_project(project_name)
        if not project:
            console.print(f"❌ Project '{project_name}' not found.", style="bold red")
            ctx.exit(1)

        if dry_run:
            console.print(
                f"\n🔍 [DRY RUN] Would archive project: {project_name}",
                style="bold blue",
            )
            console.print(
                f"  Source: .roadmap/projects/{project_name}.md",
                style="cyan",
            )
            console.print(
                f"  Destination: .roadmap/archive/projects/{project_name}.md",
                style="cyan",
            )
            return

        # Confirm
        if not force:
            if not click.confirm(f"Archive project '{project_name}'?", default=False):
                console.print("❌ Cancelled.", style="yellow")
                return

        # Perform archive
        ensure_directory_exists(archive_dir)

        # Find the project file by searching all .md files
        project_file = None
        for md_file in (roadmap_dir / "projects").rglob("*.md"):
            # Read and check if this is the right project
            try:
                test_project = ProjectParser.parse_project_file(md_file)
                if test_project.name == project_name:
                    project_file = md_file
                    break
            except Exception:
                continue

        if not project_file or not project_file.exists():
            console.print(
                f"❌ Project file not found for: {project_name}",
                style="bold red",
            )
            ctx.exit(1)

        archive_file = archive_dir / project_file.name
        project_file.rename(archive_file)

        # Mark as archived in database
        try:
            core.db.mark_project_archived(project.id, archived=True)
        except Exception as e:
            console.print(
                f"⚠️  Warning: Failed to mark in database: {e}", style="yellow"
            )

        console.print(
            f"\n✅ Archived project '{project_name}' to .roadmap/archive/projects/",
            style="bold green",
        )

    except Exception as e:
        log_error_with_context(
            e,
            operation="project_archive",
            entity_type="project",
            additional_context={"project_name": project_name},
        )
        console.print(f"❌ Failed to archive project: {e}", style="bold red")
        ctx.exit(1)
