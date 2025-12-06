"""Restore milestone command - move archived milestones back to active."""

from pathlib import Path

import click  # type: ignore[import-untyped]
from rich.console import Console  # type: ignore[import-untyped]

from roadmap.adapters.cli.error_logging import log_error_with_context
from roadmap.adapters.cli.logging_decorators import log_command, verbose_output
from roadmap.adapters.persistence.parser import MilestoneParser
from roadmap.common.file_utils import ensure_directory_exists

console = Console()


@click.command()
@click.argument("milestone_name", required=False)
@click.option(
    "--all",
    is_flag=True,
    help="Restore all archived milestones",
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
@log_command("milestone_restore", entity_type="milestone", track_duration=True)
def restore_milestone(
    ctx: click.Context,
    milestone_name: str | None,
    all: bool,
    dry_run: bool,
    force: bool,
    verbose: bool,
):
    """Restore an archived milestone back to active milestones.

    This moves a milestone from .roadmap/archive/milestones/ back to
    .roadmap/milestones/, making it active again.

    Examples:
        roadmap milestone restore "v1.0"
        roadmap milestone restore --all
        roadmap milestone restore "v1.0" --dry-run
    """
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.",
            style="bold red",
        )
        ctx.exit(1)

    if not milestone_name and not all:
        console.print(
            "❌ Error: Specify a milestone name or use --all",
            style="bold red",
        )
        ctx.exit(1)

    if milestone_name and all:
        console.print(
            "❌ Error: Cannot specify milestone name with --all",
            style="bold red",
        )
        ctx.exit(1)

    try:
        roadmap_dir = Path.cwd() / ".roadmap"
        archive_dir = roadmap_dir / "archive" / "milestones"
        active_dir = roadmap_dir / "milestones"

        if not archive_dir.exists():
            console.print(
                "📋 No archived milestones found.",
                style="yellow",
            )
            return

        if all:
            # Get all archived milestone files
            archived_files = list(archive_dir.glob("*.md"))

            if not archived_files:
                console.print("📋 No archived milestones to restore.", style="yellow")
                return

            # Parse milestone names
            milestones_info = []
            for file_path in archived_files:
                try:
                    milestone = MilestoneParser.parse_milestone_file(file_path)
                    milestones_info.append((file_path, milestone.name))
                except Exception:
                    continue

            if not milestones_info:
                console.print("📋 No valid archived milestones found.", style="yellow")
                return

            if dry_run:
                console.print(
                    f"\n🔍 [DRY RUN] Would restore {len(milestones_info)} milestone(s):\n",
                    style="bold blue",
                )
                for _, name in milestones_info:
                    console.print(f"  • {name}", style="cyan")
                return

            # Confirm
            if not force:
                console.print(
                    f"\n⚠️  About to restore {len(milestones_info)} archived milestone(s):",
                    style="bold yellow",
                )
                for _, name in milestones_info:
                    console.print(f"  • {name}", style="cyan")

                if not click.confirm("\nProceed with restore?", default=False):
                    console.print("❌ Cancelled.", style="yellow")
                    return

            # Restore each milestone
            ensure_directory_exists(active_dir)
            restored_count = 0

            for file_path, name in milestones_info:
                if file_path.exists():
                    dest_file = active_dir / file_path.name
                    if dest_file.exists():
                        console.print(
                            f"⚠️  Skipping {name} - already exists in active milestones",
                            style="yellow",
                        )
                        continue
                    file_path.rename(dest_file)

                    # Mark as unarchived in database
                    try:
                        core.db.mark_milestone_archived(name, archived=False)
                    except Exception as e:
                        console.print(
                            f"⚠️  Warning: Failed to mark milestone {name} as restored in database: {e}",
                            style="yellow",
                        )

                    restored_count += 1

            console.print(
                f"\n✅ Restored {restored_count} milestone(s) to .roadmap/milestones/",
                style="bold green",
            )

        else:
            # Restore single milestone - find it in archive
            archived_file = None
            for file_path in archive_dir.glob("*.md"):
                try:
                    milestone = MilestoneParser.parse_milestone_file(file_path)
                    if milestone.name == milestone_name:
                        archived_file = file_path
                        break
                except Exception:
                    continue

            if not archived_file or not archived_file.exists():
                console.print(
                    f"❌ Archived milestone '{milestone_name}' not found.",
                    style="bold red",
                )
                ctx.exit(1)

            # Check if already exists in active
            dest_file = active_dir / archived_file.name  # type: ignore[union-attr]
            if dest_file.exists():
                console.print(
                    f"❌ Milestone '{milestone_name}' already exists in active milestones.",
                    style="bold red",
                )
                ctx.exit(1)

            if dry_run:
                console.print(
                    f"\n🔍 [DRY RUN] Would restore milestone: {milestone_name}",
                    style="bold blue",
                )
                console.print(
                    f"  Source: .roadmap/archive/milestones/{archived_file.name}",  # type: ignore[union-attr]
                    style="cyan",
                )
                console.print(
                    f"  Destination: .roadmap/milestones/{archived_file.name}",  # type: ignore[union-attr]
                    style="cyan",
                )
                return

            # Confirm
            if not force:
                if not click.confirm(
                    f"Restore milestone '{milestone_name}'?", default=False
                ):
                    console.print("❌ Cancelled.", style="yellow")
                    return

            # Perform restore
            ensure_directory_exists(active_dir)
            archived_file.rename(dest_file)  # type: ignore[union-attr]

            # Mark as unarchived in database
            try:
                core.db.mark_milestone_archived(milestone_name, archived=False)
            except Exception as e:
                console.print(
                    f"⚠️  Warning: Failed to mark in database: {e}", style="yellow"
                )

            console.print(
                f"\n✅ Restored milestone '{milestone_name}' to .roadmap/milestones/",
                style="bold green",
            )

    except Exception as e:
        log_error_with_context(
            e,
            operation="milestone_restore",
            entity_type="milestone",
            additional_context={"milestone_name": milestone_name},
        )
        console.print(f"❌ Failed to restore milestone: {e}", style="bold red")
        ctx.exit(1)
