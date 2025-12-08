"""Archive project command - move completed projects to archive."""

from pathlib import Path

import click  # type: ignore[import-not-found]

from roadmap.adapters.cli.cli_confirmations import confirm_action, confirm_override_warning
from roadmap.adapters.cli.helpers import require_initialized
from roadmap.adapters.persistence.parser import ProjectParser
from roadmap.common.console import get_console
from roadmap.common.file_utils import ensure_directory_exists
from roadmap.infrastructure.logging import (
    log_command,
    log_error_with_context,
    verbose_output,
)

console = get_console()


def _handle_list_archived_projects(archive_dir: Path):
    """List all archived projects and return True if handled."""
    if not archive_dir.exists():
        console.print("📋 No archived projects.", style="yellow")
        return True

    archived_files = list(archive_dir.glob("*.md"))
    if not archived_files:
        console.print("📋 No archived projects.", style="yellow")
        return True

    console.print("\n📦 Archived Projects:\n", style="bold blue")
    for file_path in archived_files:
        try:
            project = ProjectParser.parse_project_file(file_path)
            console.print(f"  • {project.name} ({project.status})", style="cyan")
        except Exception:
            console.print(f"  • {file_path.stem} (parse error)", style="red")
    return True


def _find_project_file(roadmap_dir: Path, project_name: str) -> Path | None:
    """Find project file by name, searching through all .md files."""
    for md_file in (roadmap_dir / "projects").rglob("*.md"):
        try:
            project = ProjectParser.parse_project_file(md_file)
            if project.name == project_name:
                return md_file
        except Exception:
            continue
    return None


def _print_dry_run_preview(project_name: str):
    """Print preview of what would be archived."""
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


def _confirm_archive(project_name: str, force: bool) -> bool:
    """Get user confirmation to archive project."""
    if force:
        return True
    return click.confirm(f"Archive project '{project_name}'?", default=False)


def _perform_archive(
    project_file: Path, archive_dir: Path, project_id: str, core
) -> bool:
    """Perform the archive operation. Returns True on success."""
    archive_file = archive_dir / project_file.name
    project_file.rename(archive_file)

    # Mark as archived in database
    try:
        core.db.mark_project_archived(project_id, archived=True)
    except Exception as e:
        console.print(f"⚠️  Warning: Failed to mark in database: {e}", style="yellow")

    return True


def _check_roadmap_initialized(core) -> bool:
    """Check if roadmap is initialized.

    Args:
        core: RoadmapCore instance

    Returns:
        True if initialized
    """
    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.",
            style="bold red",
        )
        return False
    return True


def _validate_and_get_project(core, project_name: str):
    """Validate and retrieve project.

    Args:
        core: RoadmapCore instance
        project_name: Project name

    Returns:
        Project object or None
    """
    project = core.projects.get(project_name)
    if not project:
        console.print(f"❌ Project '{project_name}' not found.", style="bold red")
        return None
    return project


def _validate_project_file(roadmap_dir: Path, project_name: str):
    """Validate project file exists.

    Args:
        roadmap_dir: Roadmap directory
        project_name: Project name

    Returns:
        Project file path or None
    """
    project_file = _find_project_file(roadmap_dir, project_name)
    if not project_file or not project_file.exists():
        console.print(
            f"❌ Project file not found for: {project_name}",
            style="bold red",
        )
        return None
    return project_file


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
@require_initialized
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

    # Handle --list option
    if list_archived:
        roadmap_dir = Path.cwd() / ".roadmap"
        archive_dir = roadmap_dir / "archive" / "projects"
        _handle_list_archived_projects(archive_dir)
        return

    if not project_name:
        console.print(
            "❌ Error: Specify a project name or use --list",
            style="bold red",
        )
        ctx.exit(1)

    # Type guard: ensure project_name is not None after check above
    assert project_name is not None

    try:
        roadmap_dir = Path.cwd() / ".roadmap"
        archive_dir = roadmap_dir / "archive" / "projects"

        # Validate project exists
        project = _validate_and_get_project(core, project_name)
        if not project:
            ctx.exit(1)

        if dry_run:
            _print_dry_run_preview(project_name)
            return

        # Confirm
        if not _confirm_archive(project_name, force):
            console.print("❌ Cancelled.", style="yellow")
            return

        # Perform archive
        ensure_directory_exists(archive_dir)

        # Validate project file exists
        project_file = _validate_project_file(roadmap_dir, project_name)
        if not project_file:
            ctx.exit(1)

        # Type guard: ensure project_file is not None after check above
        assert project_file is not None

        _perform_archive(project_file, archive_dir, project.id, core)

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
