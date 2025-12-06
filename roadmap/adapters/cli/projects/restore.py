"""Restore project command - move archived projects back to active."""

from pathlib import Path

import click  # type: ignore[import-untyped]
from rich.console import Console  # type: ignore[import-untyped]

from roadmap.adapters.cli.error_logging import log_error_with_context
from roadmap.adapters.cli.logging_decorators import log_command, verbose_output
from roadmap.adapters.persistence.parser import ProjectParser
from roadmap.common.file_utils import ensure_directory_exists

console = Console()


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

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.",
            style="bold red",
        )
        ctx.exit(1)

    if not project_name and not all:
        console.print(
            "❌ Error: Specify a project name or use --all",
            style="bold red",
        )
        ctx.exit(1)

    if project_name and all:
        console.print(
            "❌ Error: Cannot specify project name with --all",
            style="bold red",
        )
        ctx.exit(1)

    try:
        roadmap_dir = Path.cwd() / ".roadmap"
        archive_dir = roadmap_dir / "archive" / "projects"
        active_dir = roadmap_dir / "projects"

        if not archive_dir.exists():
            console.print(
                "📋 No archived projects found.",
                style="yellow",
            )
            return

        if all:
            # Get all archived project files
            archived_files = list(archive_dir.rglob("*.md"))

            if not archived_files:
                console.print("📋 No archived projects to restore.", style="yellow")
                return

            # Parse project names
            projects_info = []
            for file_path in archived_files:
                try:
                    project = ProjectParser.parse_project_file(file_path)
                    projects_info.append((file_path, project.id, project.name))
                except Exception:
                    continue

            if not projects_info:
                console.print("📋 No valid archived projects found.", style="yellow")
                return

            if dry_run:
                console.print(
                    f"\n🔍 [DRY RUN] Would restore {len(projects_info)} project(s):\n",
                    style="bold blue",
                )
                for _, _, name in projects_info:
                    console.print(f"  • {name}", style="cyan")
                return

            # Confirm
            if not force:
                console.print(
                    f"\n⚠️  About to restore {len(projects_info)} archived project(s):",
                    style="bold yellow",
                )
                for _, _, name in projects_info:
                    console.print(f"  • {name}", style="cyan")

                if not click.confirm("\nProceed with restore?", default=False):
                    console.print("❌ Cancelled.", style="yellow")
                    return

            # Restore each project
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
                    file_path.rename(dest_file)

                    # Mark as unarchived in database
                    try:
                        core.db.mark_project_archived(project_id, archived=False)
                    except Exception as e:
                        console.print(
                            f"⚠️  Warning: Failed to mark project {name} as restored in database: {e}",
                            style="yellow",
                        )

                    restored_count += 1

            console.print(
                f"\n✅ Restored {restored_count} project(s) to .roadmap/projects/",
                style="bold green",
            )

        else:
            # Restore single project - find it in archive
            archived_file = None
            for file_path in archive_dir.glob("*.md"):
                try:
                    project = ProjectParser.parse_project_file(file_path)
                    if project.name == project_name:
                        archived_file = file_path
                        break
                except Exception:
                    continue

            if not archived_file or not archived_file.exists():
                console.print(
                    f"❌ Archived project '{project_name}' not found.",
                    style="bold red",
                )
                ctx.exit(1)

            # Parse to get full info
            try:
                project = ProjectParser.parse_project_file(archived_file)  # type: ignore[arg-type]
            except Exception as e:
                console.print(
                    f"❌ Failed to parse archived project: {e}",
                    style="bold red",
                )
                ctx.exit(1)

            # Check if already exists in active
            dest_file = active_dir / archived_file.name  # type: ignore[union-attr]
            if dest_file.exists():
                console.print(
                    f"❌ Project '{project_name}' already exists in active projects.",
                    style="bold red",
                )
                ctx.exit(1)

            if dry_run:
                console.print(
                    f"\n🔍 [DRY RUN] Would restore project: {project_name}",
                    style="bold blue",
                )
                console.print(
                    f"  Source: .roadmap/archive/projects/{archived_file.name}",  # type: ignore[union-attr]
                    style="cyan",
                )
                console.print(
                    f"  Destination: .roadmap/projects/{archived_file.name}",  # type: ignore[union-attr]
                    style="cyan",
                )
                return

            # Confirm
            if not force:
                if not click.confirm(
                    f"Restore project '{project_name}'?", default=False
                ):
                    console.print("❌ Cancelled.", style="yellow")
                    return

            # Perform restore
            ensure_directory_exists(active_dir)
            archived_file.rename(dest_file)  # type: ignore[union-attr]

            # Mark as unarchived in database
            try:
                core.db.mark_project_archived(project.id, archived=False)
            except Exception as e:
                console.print(
                    f"⚠️  Warning: Failed to mark in database: {e}", style="yellow"
                )

            console.print(
                f"\n✅ Restored project '{project_name}' to .roadmap/projects/",
                style="bold green",
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
