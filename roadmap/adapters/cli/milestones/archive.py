"""Archive milestone command - move closed milestones to archive."""

import shutil
from pathlib import Path

import click  # type: ignore[import-not-found]

from roadmap.adapters.cli.cli_confirmations import confirm_action, confirm_override_warning
from roadmap.adapters.cli.helpers import require_initialized
from roadmap.adapters.persistence.parser import MilestoneParser
from roadmap.common.console import get_console
from roadmap.common.file_utils import ensure_directory_exists
from roadmap.infrastructure.logging import (
    log_command,
    log_error_with_context,
    verbose_output,
)

console = get_console()


def _show_archived_milestones():
    """Display list of archived milestones."""
    roadmap_dir = Path.cwd() / ".roadmap"
    archive_dir = roadmap_dir / "archive" / "milestones"

    if not archive_dir.exists():
        console.print("📋 No archived milestones.", style="yellow")
        return

    archived_files = list(archive_dir.glob("*.md"))
    if not archived_files:
        console.print("📋 No archived milestones.", style="yellow")
        return

    console.print("\n📦 Archived Milestones:\n", style="bold blue")
    for file_path in archived_files:
        try:
            milestone = MilestoneParser.parse_milestone_file(file_path)
            console.print(
                f"  • {milestone.name} ({milestone.status.value})", style="cyan"
            )
        except Exception:
            console.print(f"  • {file_path.stem} (parse error)", style="red")


def _validate_archive_arguments(milestone_name, all_closed):
    """Validate archive command arguments."""
    if not milestone_name and not all_closed:
        console.print(
            "❌ Error: Specify a milestone name or use --all-closed",
            style="bold red",
        )
        return False

    if milestone_name and all_closed:
        console.print(
            "❌ Error: Cannot specify milestone name with --all-closed",
            style="bold red",
        )
        return False

    return True


def _find_milestone_file(roadmap_dir, milestone_name):
    """Find milestone file by parsing and matching name."""
    for md_file in (roadmap_dir / "milestones").glob("*.md"):
        try:
            test_milestone = MilestoneParser.parse_milestone_file(md_file)
            if test_milestone.name == milestone_name:
                return md_file
        except Exception:
            continue
    return None


def _move_milestone_issues(roadmap_dir, milestone_name):
    """Move associated issues folder to archive."""
    issues_dir = roadmap_dir / "issues" / milestone_name
    if not issues_dir.exists():
        return

    archive_issues_dir = roadmap_dir / "archive" / "issues"
    ensure_directory_exists(archive_issues_dir)
    dest_issues_dir = archive_issues_dir / milestone_name

    if dest_issues_dir.exists():
        shutil.rmtree(dest_issues_dir)

    issues_dir.rename(dest_issues_dir)
    console.print(
        f"  Moved issues to .roadmap/archive/issues/{milestone_name}/",
        style="dim",
    )


def _validate_single_milestone(core, milestone_name):
    """Validate and get single milestone for archival."""
    milestone = core.milestones.get(milestone_name)
    if not milestone:
        console.print(f"❌ Milestone '{milestone_name}' not found.", style="bold red")
        return None
    return milestone


def _check_milestone_closed_status(milestone_name, milestone, force):
    """Check if milestone is closed, prompt if not."""
    if milestone.status.value == "closed":
        return True

    console.print(
        f"⚠️  Warning: Milestone '{milestone_name}' is not closed (status: {milestone.status.value})",
        style="bold yellow",
    )
    return force or confirm_override_warning()


def _archive_single_milestone(core, roadmap_dir, milestone_name, dry_run, force):
    """Archive a single milestone."""
    milestone = _validate_single_milestone(core, milestone_name)
    if not milestone:
        return False

    if not _check_milestone_closed_status(milestone_name, milestone, force):
        return False

    if dry_run:
        console.print(
            f"\n🔍 [DRY RUN] Would archive milestone: {milestone_name}",
            style="bold blue",
        )
        console.print(
            f"  Source: .roadmap/milestones/{milestone_name}.md",
            style="cyan",
        )
        console.print(
            f"  Destination: .roadmap/archive/milestones/{milestone_name}.md",
            style="cyan",
        )
        return True

    if not force and not confirm_action(
        f"Archive milestone '{milestone_name}'?", default=False
    ):
        return False

    archive_dir = roadmap_dir / "archive" / "milestones"
    archive_dir.mkdir(parents=True, exist_ok=True)

    milestone_file = _find_milestone_file(roadmap_dir, milestone_name)
    if not milestone_file or not milestone_file.exists():
        console.print(
            f"❌ Milestone file not found for: {milestone_name}",
            style="bold red",
        )
        return False

    archive_file = archive_dir / milestone_file.name
    milestone_file.rename(archive_file)
    _move_milestone_issues(roadmap_dir, milestone_name)

    try:
        core.db.mark_milestone_archived(milestone_name, archived=True)
    except Exception as e:
        console.print(f"⚠️  Warning: Failed to mark in database: {e}", style="yellow")

    console.print(
        f"\n✅ Archived milestone '{milestone_name}' to .roadmap/archive/milestones/",
        style="bold green",
    )
    return True


def _get_closed_milestones(core):
    """Get list of closed milestones."""
    all_milestones = core.milestones.list()
    return [m for m in all_milestones if m.status.value == "closed"]


def _confirm_archive_all(milestones, force):
    """Confirm archival of multiple milestones."""
    if force:
        return True

    console.print(
        f"\n⚠️  About to archive {len(milestones)} closed milestone(s):",
        style="bold yellow",
    )
    for m in milestones:
        console.print(f"  • {m.name}", style="cyan")
    return confirm_action("\nProceed with archival?", default=False)


def _archive_all_closed_milestones(core, roadmap_dir, dry_run, force):
    """Archive all closed milestones."""
    milestones = _get_closed_milestones(core)

    if not milestones:
        console.print("📋 No closed milestones to archive.", style="yellow")
        return True

    if dry_run:
        console.print(
            f"\n🔍 [DRY RUN] Would archive {len(milestones)} milestone(s):\n",
            style="bold blue",
        )
        for m in milestones:
            console.print(f"  • {m.name}", style="cyan")
        return True

    if not _confirm_archive_all(milestones, force):
        return False

    archive_dir = roadmap_dir / "archive" / "milestones"
    ensure_directory_exists(archive_dir)
    archived_count = 0

    for milestone in milestones:
        milestone_file = _find_milestone_file(roadmap_dir, milestone.name)

        if milestone_file and milestone_file.exists():
            archive_file = archive_dir / milestone_file.name
            milestone_file.rename(archive_file)
            _move_milestone_issues(roadmap_dir, milestone.name)

            try:
                core.db.mark_milestone_archived(milestone.name, archived=True)
            except Exception as e:
                console.print(
                    f"⚠️  Warning: Failed to mark {milestone.name} as archived: {e}",
                    style="yellow",
                )

            archived_count += 1

    console.print(
        f"\n✅ Archived {archived_count} milestone(s) to .roadmap/archive/milestones/",
        style="bold green",
    )
    return True


@click.command()
@click.argument("milestone_name", required=False)
@click.option(
    "--all-closed",
    is_flag=True,
    help="Archive all closed milestones",
)
@click.option(
    "--list",
    "list_archived",
    is_flag=True,
    help="List archived milestones",
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
@log_command("milestone_archive", entity_type="milestone", track_duration=True)
def archive_milestone(
    ctx: click.Context,
    milestone_name: str | None,
    all_closed: bool,
    list_archived: bool,
    dry_run: bool,
    force: bool,
    verbose: bool,
):
    """Archive a milestone by moving it to .roadmap/archive/milestones/.

    This is a non-destructive operation that preserves milestone data while
    cleaning up the active workspace. Archived milestones can be restored
    if needed.

    Examples:
        roadmap milestone archive "v1.0"
        roadmap milestone archive --all-closed
        roadmap milestone archive --all-closed --dry-run
        roadmap milestone archive --list
    """
    core = ctx.obj["core"]

    if list_archived:
        _show_archived_milestones()
        return

    if not _validate_archive_arguments(milestone_name, all_closed):
        ctx.exit(1)

    try:
        roadmap_dir = Path.cwd() / ".roadmap"

        if all_closed:
            _archive_all_closed_milestones(core, roadmap_dir, dry_run, force)
        else:
            _archive_single_milestone(core, roadmap_dir, milestone_name, dry_run, force)

    except Exception as e:
        log_error_with_context(
            e,
            operation="milestone_archive",
            entity_type="milestone",
            additional_context={"milestone_name": milestone_name},
        )
        console.print(f"❌ Failed to archive milestone: {e}", style="bold red")
        ctx.exit(1)
