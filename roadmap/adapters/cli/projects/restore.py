"""Restore project command - move archived projects back to active."""

from pathlib import Path

import click  # type: ignore[import-untyped]

from roadmap.adapters.cli.cli_confirmations import confirm_action
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


def _validate_restore_arguments(project_name, all):
    """Validate restore arguments."""
    if not project_name and not all:
        console.print(
            "❌ Error: Specify a project name or use --all",
            style="bold red",
        )
        return False

    if project_name and all:
        console.print(
            "❌ Error: Cannot specify project name with --all",
            style="bold red",
        )
        return False

    return True


def _check_archive_exists(archive_dir):
    """Check if archive directory exists."""
    if not archive_dir.exists():
        console.print("📋 No archived projects found.", style="yellow")
        return False
    return True


def _get_archived_projects(archive_dir):
    """Get list of archived projects."""
    archived_files = list(archive_dir.rglob("*.md"))
    if not archived_files:
        console.print("📋 No archived projects to restore.", style="yellow")
        return None

    projects_info = []
    for file_path in archived_files:
        try:
            project = ProjectParser.parse_project_file(file_path)
            projects_info.append((file_path, project.id, project.name))
        except Exception:
            continue

    return projects_info if projects_info else None


def _find_archived_project(archive_dir, project_name):
    """Find archived project file by name."""
    for file_path in archive_dir.glob("*.md"):
        try:
            project = ProjectParser.parse_project_file(file_path)
            if project.name == project_name:
                return file_path
        except Exception:
            continue
    return None


def _restore_project_file(core, archive_file, active_dir, project_id):
    """Restore a single project file."""
    dest_file = active_dir / archive_file.name
    archive_file.rename(dest_file)

    try:
        core.db.mark_project_archived(project_id, archived=False)
    except Exception as e:
        console.print(
            f"⚠️  Warning: Failed to mark project as restored: {e}",
            style="yellow",
        )


def _restore_multiple_projects(
    core, archive_dir, active_dir, projects_info, dry_run, force
):
    """Restore multiple archived projects."""
    if dry_run:
        console.print(
            f"\n🔍 [DRY RUN] Would restore {len(projects_info)} project(s):\n",
            style="bold blue",
        )
        for _, _, name in projects_info:
            console.print(f"  • {name}", style="cyan")
        return True

    if not force:
        console.print(
            f"\n⚠️  About to restore {len(projects_info)} archived project(s):",
            style="bold yellow",
        )
        for _, _, name in projects_info:
            console.print(f"  • {name}", style="cyan")

        if not confirm_action("\nProceed with restore?", default=False):
            return False

    ensure_directory_exists(active_dir)
    restored_count = 0

    for file_path, project_id, name in projects_info:
        if file_path.exists():
            dest_file = active_dir / file_path.name
            if dest_file.exists():
                console.print(
                    f"⚠️  Skipping {name} - already exists in active projects",
                    style="yellow",
                )
                continue

            _restore_project_file(core, file_path, active_dir, project_id)
            restored_count += 1

    console.print(
        f"\n✅ Restored {restored_count} project(s) to .roadmap/projects/",
        style="bold green",
    )
    return True


def _restore_single_project(
    core, archive_dir, active_dir, project_name, dry_run, force
):
    """Restore a single archived project."""
    archived_file = _find_archived_project(archive_dir, project_name)
    if not archived_file:
        console.print(
            f"❌ Archived project '{project_name}' not found.",
            style="bold red",
        )
        return False

    try:
        project = ProjectParser.parse_project_file(archived_file)  # type: ignore[arg-type]
    except Exception as e:
        console.print(f"❌ Failed to parse archived project: {e}", style="bold red")
        return False

    dest_file = active_dir / archived_file.name
    if dest_file.exists():
        console.print(
            f"❌ Project '{project_name}' already exists in active projects.",
            style="bold red",
        )
        return False

    if dry_run:
        console.print(
            f"\n🔍 [DRY RUN] Would restore project: {project_name}",
            style="bold blue",
        )
        console.print(
            f"  Source: .roadmap/archive/projects/{archived_file.name}",
            style="cyan",
        )
        console.print(
            f"  Destination: .roadmap/projects/{archived_file.name}",
            style="cyan",
        )
        return True

    if not force and not confirm_action(
        f"Restore project '{project_name}'?", default=False
    ):
        return False

    ensure_directory_exists(active_dir)
    _restore_project_file(core, archived_file, active_dir, project.id)

    console.print(
        f"\n✅ Restored project '{project_name}' to .roadmap/projects/",
        style="bold green",
    )
    return True


@click.command()
@click.argument("project_name", required=False)
@click.option(
    "--all",
    is_flag=True,
    help="Restore all archived projects",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Preview what would be restored without actually doing it",
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
@log_command("project_restore", entity_type="project", track_duration=True)
def restore_project(
    ctx: click.Context,
    project_name: str | None,
    all: bool,
    dry_run: bool,
    force: bool,
    verbose: bool,
):
    """Restore an archived project back to active projects.

    This moves a project from .roadmap/archive/projects/ back to
    .roadmap/projects/, making it active again.

    Examples:
        roadmap project restore "my-project"
        roadmap project restore --all
        roadmap project restore "my-project" --dry-run
    """
    core = ctx.obj["core"]

    if not _validate_restore_arguments(project_name, all):
        ctx.exit(1)

    try:
        roadmap_dir = Path.cwd() / ".roadmap"
        archive_dir = roadmap_dir / "archive" / "projects"
        active_dir = roadmap_dir / "projects"

        if not _check_archive_exists(archive_dir):
            return

        if all:
            projects_info = _get_archived_projects(archive_dir)
            if not projects_info:
                return

            _restore_multiple_projects(
                core, archive_dir, active_dir, projects_info, dry_run, force
            )
        else:
            _restore_single_project(
                core, archive_dir, active_dir, project_name, dry_run, force
            )

    except Exception as e:
        log_error_with_context(
            e,
            operation="project_restore",
            entity_type="project",
            additional_context={"project_name": project_name},
        )
        console.print(f"❌ Failed to restore project: {e}", style="bold red")
        ctx.exit(1)
