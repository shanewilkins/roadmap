"""Restore milestone command - move archived milestones back to active."""

from pathlib import Path

import click  # type: ignore[import-untyped]

from roadmap.adapters.cli.archive_utils import handle_restore_parse_error
from roadmap.adapters.cli.cli_confirmations import confirm_action
from roadmap.adapters.cli.cli_error_handlers import (
    handle_cli_error,
)
from roadmap.adapters.cli.helpers import require_initialized
from roadmap.adapters.persistence.parser import MilestoneParser
from roadmap.common.console import get_console
from roadmap.common.file_utils import ensure_directory_exists
from roadmap.infrastructure.logging import (
    log_command,
    verbose_output,
)

console = get_console()


def _validate_restore_arguments(milestone_name, all):
    """Validate restore arguments."""
    if not milestone_name and not all:
        console.print(
            "❌ Error: Specify a milestone name or use --all",
            style="bold red",
        )
        return False

    if milestone_name and all:
        console.print(
            "❌ Error: Cannot specify milestone name with --all",
            style="bold red",
        )
        return False

    return True


def _check_archive_exists(archive_dir):
    """Check if archive directory exists."""
    if not archive_dir.exists():
        console.print("📋 No archived milestones found.", style="yellow")
        return False
    return True


def _get_archived_milestones(archive_dir):
    """Get list of archived milestones."""
    archived_files = list(archive_dir.glob("*.md"))
    if not archived_files:
        console.print("📋 No archived milestones to restore.", style="yellow")
        return None

    milestones_info = []
    for file_path in archived_files:
        try:
            milestone = MilestoneParser.parse_milestone_file(file_path)
            milestones_info.append((file_path, milestone.name))
        except Exception as e:
            handle_restore_parse_error(
                error=e,
                entity_type="milestone",
                entity_id=file_path.stem,
                archive_dir=str(archive_dir),
                console=console,
            )
            continue

    return milestones_info if milestones_info else None


def _find_archived_milestone(archive_dir, milestone_name):
    """Find archived milestone file by name."""
    for file_path in archive_dir.glob("*.md"):
        try:
            milestone = MilestoneParser.parse_milestone_file(file_path)
            if milestone.name == milestone_name:
                return file_path
        except Exception as e:
            handle_cli_error(
                error=e,
                operation="find_archived_milestone",
                entity_type="milestone",
                entity_id=file_path.stem,
                context={"milestone_name": milestone_name},
                fatal=False,
            )
            continue
    return None


def _restore_milestone_file(core, archive_file, active_dir, milestone_name):
    """Restore a single milestone file."""
    dest_file = active_dir / archive_file.name
    archive_file.rename(dest_file)

    try:
        core.db.mark_milestone_archived(milestone_name, archived=False)
    except Exception as e:
        handle_cli_error(
            error=e,
            operation="mark_milestone_restored",
            entity_type="milestone",
            entity_id=milestone_name,
            context={"dest_file": str(dest_file)},
            fatal=False,
        )
        console.print(
            f"⚠️  Warning: Failed to mark milestone as restored: {e}",
            style="yellow",
        )


def _restore_multiple_milestones(
    core, archive_dir, active_dir, milestones_info, dry_run, force
):
    """Restore multiple archived milestones."""
    if dry_run:
        console.print(
            f"\n🔍 [DRY RUN] Would restore {len(milestones_info)} milestone(s):\n",
            style="bold blue",
        )
        for _, name in milestones_info:
            console.print(f"  • {name}", style="cyan")
        return True

    if not force:
        console.print(
            f"\n⚠️  About to restore {len(milestones_info)} archived milestone(s):",
            style="bold yellow",
        )
        for _, name in milestones_info:
            console.print(f"  • {name}", style="cyan")

        if not confirm_action("\nProceed with restore?", default=False):
            return False

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

            _restore_milestone_file(core, file_path, active_dir, name)
            restored_count += 1

    console.print(
        f"\n✅ Restored {restored_count} milestone(s) to .roadmap/milestones/",
        style="bold green",
    )
    return True


def _restore_single_milestone(
    core, archive_dir, active_dir, milestone_name, dry_run, force
):
    """Restore a single archived milestone."""
    archived_file = _find_archived_milestone(archive_dir, milestone_name)
    if not archived_file:
        console.print(
            f"❌ Archived milestone '{milestone_name}' not found.",
            style="bold red",
        )
        return False

    dest_file = active_dir / archived_file.name
    if dest_file.exists():
        console.print(
            f"❌ Milestone '{milestone_name}' already exists in active milestones.",
            style="bold red",
        )
        return False

    if dry_run:
        console.print(
            f"\n🔍 [DRY RUN] Would restore milestone: {milestone_name}",
            style="bold blue",
        )
        console.print(
            f"  Source: .roadmap/archive/milestones/{archived_file.name}",
            style="cyan",
        )
        console.print(
            f"  Destination: .roadmap/milestones/{archived_file.name}",
            style="cyan",
        )
        return True

    if not force and not confirm_action(
        f"Restore milestone '{milestone_name}'?", default=False
    ):
        return False

    ensure_directory_exists(active_dir)
    _restore_milestone_file(core, archived_file, active_dir, milestone_name)

    console.print(
        f"\n✅ Restored milestone '{milestone_name}' to .roadmap/milestones/",
        style="bold green",
    )
    return True


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
@require_initialized
@verbose_output
@log_command("milestone_restore", entity_type="milestone", track_duration=True)
def restore_milestone(
    ctx: click.Context,
    milestone_name: str | None,
    all: bool,
    dry_run: bool,
    force: bool,
    verbose: bool,  # noqa: F841
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

    if not _validate_restore_arguments(milestone_name, all):
        ctx.exit(1)

    try:
        roadmap_dir = Path.cwd() / ".roadmap"
        archive_dir = roadmap_dir / "archive" / "milestones"
        active_dir = roadmap_dir / "milestones"

        if not _check_archive_exists(archive_dir):
            return

        if all:
            milestones_info = _get_archived_milestones(archive_dir)
            if not milestones_info:
                return

            _restore_multiple_milestones(
                core, archive_dir, active_dir, milestones_info, dry_run, force
            )
        else:
            _restore_single_milestone(
                core, archive_dir, active_dir, milestone_name, dry_run, force
            )

    except Exception as e:
        handle_cli_error(
            error=e,
            operation="restore_milestone",
            entity_type="milestone",
            entity_id=milestone_name or "unknown",
            context={
                "all": all,
                "dry_run": dry_run,
                "force": force,
            },
            fatal=True,
        )
        ctx.exit(1)
