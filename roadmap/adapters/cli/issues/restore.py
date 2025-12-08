"""Restore issue command - move archived issues back to active."""

from pathlib import Path

import click  # type: ignore[import-untyped]
from rich.console import Console  # type: ignore[import-untyped]

from roadmap.adapters.cli.helpers import require_initialized
from roadmap.adapters.persistence.parser import IssueParser
from roadmap.common.formatters import (
    format_operation_success,
)
from roadmap.infrastructure.logging import (
    log_command,
    log_error_with_context,
    verbose_output,
)

console = Console()


def _validate_restore_arguments(issue_id, all):
    """Validate restore command arguments."""
    if not issue_id and not all:
        console.print(
            "❌ Error: Specify an issue ID or use --all",
            style="bold red",
        )
        return False

    if issue_id and all:
        console.print(
            "❌ Error: Cannot specify issue ID with --all",
            style="bold red",
        )
        return False

    return True


def _check_archive_exists(archive_dir):
    """Check if archive directory exists."""
    if not archive_dir.exists():
        console.print("📋 No archived issues found.", style="yellow")
        return False
    return True


def _get_archived_issues(archive_dir):
    """Get list of archived issues with metadata."""
    archived_files = list(archive_dir.glob("*.md"))
    if not archived_files:
        console.print("📋 No archived issues to restore.", style="yellow")
        return None

    issues_info = []
    for file_path in archived_files:
        try:
            issue = IssueParser.parse_issue_file(file_path)
            issues_info.append((file_path, issue.id, issue.title))
        except Exception:
            continue

    return issues_info if issues_info else None


def _find_archived_issue(archive_dir, issue_id):
    """Find archived issue file by partial ID."""
    for file_path in archive_dir.glob(f"{issue_id[:8]}*.md"):  # type: ignore[index]
        return file_path
    return None


def _parse_and_validate_issue(archive_file):
    """Parse archived issue and return parsed object."""
    try:
        return IssueParser.parse_issue_file(archive_file)  # type: ignore[arg-type]
    except Exception as e:
        console.print(f"❌ Failed to parse archived issue: {e}", style="bold red")
        return None


def _check_not_in_active(active_dir, archive_file):
    """Check that issue doesn't already exist in active."""
    dest_file = active_dir / archive_file.name
    return not dest_file.exists()


def _confirm_restore_all(issues_info, status, force):
    """Confirm restore of all issues."""
    if force:
        return True

    console.print(
        f"\n⚠️  About to restore {len(issues_info)} archived issue(s):",
        style="bold yellow",
    )
    for _, id, title in issues_info:
        console.print(f"  • {id[:8]} - {title}", style="cyan")
    if status:
        console.print(f"\n  Status will be set to: {status}", style="yellow")

    return click.confirm("\nProceed with restore?", default=False)


def _restore_issue_file(core, archive_file, active_dir, issue_id, status):
    """Restore a single issue file."""
    dest_file = active_dir / archive_file.name

    if status:
        archive_file.rename(dest_file)
        core.issues.update(issue_id, status=status)
    else:
        archive_file.rename(dest_file)

    try:
        core.db.mark_issue_archived(issue_id, archived=False)
    except Exception as e:
        console.print(
            f"⚠️  Warning: Failed to mark issue {issue_id} as restored: {e}",
            style="yellow",
        )


def _restore_multiple_issues(
    core, archive_dir, active_dir, issues_info, status, dry_run, force
):
    """Restore multiple archived issues."""
    if dry_run:
        console.print(
            f"\n🔍 [DRY RUN] Would restore {len(issues_info)} issue(s):\n",
            style="bold blue",
        )
        for _, id, title in issues_info:
            console.print(f"  • {id[:8]} - {title}", style="cyan")
        if status:
            console.print(f"\n  Status would be set to: {status}", style="cyan")
        return True

    if not _confirm_restore_all(issues_info, status, force):
        console.print("❌ Cancelled.", style="yellow")
        return False

    active_dir.mkdir(parents=True, exist_ok=True)
    restored_count = 0

    for file_path, id, _title in issues_info:
        if file_path.exists():
            dest_file = active_dir / file_path.name
            if dest_file.exists():
                console.print(
                    f"⚠️  Skipping {id[:8]} - already exists in active issues",
                    style="yellow",
                )
                continue

            _restore_issue_file(core, file_path, active_dir, id, status)
            restored_count += 1

    console.print(
        f"✅ Restored {restored_count} issue(s) to .roadmap/issues/",
        style="bold green",
    )
    if status:
        console.print(f"   Status set to: {status}", style="green")

    return True


def _restore_single_issue(
    core, archive_dir, active_dir, issue_id, status, dry_run, force
):
    """Restore a single archived issue."""
    archive_file = _find_archived_issue(archive_dir, issue_id)
    if not archive_file:
        console.print(
            f"❌ Archived issue '{issue_id}' not found.",
            style="bold red",
        )
        return False

    issue = _parse_and_validate_issue(archive_file)
    if not issue:
        return False

    if not _check_not_in_active(active_dir, archive_file):
        console.print(
            f"❌ Issue '{issue_id}' already exists in active issues.",
            style="bold red",
        )
        return False

    if dry_run:
        console.print(
            f"\n🔍 [DRY RUN] Would restore issue: {issue.id[:8]} - {issue.title}",
            style="bold blue",
        )
        console.print(
            f"  Source: .roadmap/archive/issues/{archive_file.name}",
            style="cyan",
        )
        console.print(
            f"  Destination: .roadmap/issues/{archive_file.name}",
            style="cyan",
        )
        if status:
            console.print(f"  Status would be set to: {status}", style="cyan")
        return True

    msg = f"Restore issue '{issue.id[:8]} - {issue.title}'?"
    if status:
        msg += f" (status will be set to '{status}')"

    if not force and not click.confirm(msg, default=False):
        console.print("❌ Cancelled.", style="yellow")
        return False

    active_dir.mkdir(parents=True, exist_ok=True)
    _restore_issue_file(core, archive_file, active_dir, issue.id, status)

    extra_details = {}
    if status:
        extra_details["Status"] = status

    lines = format_operation_success(
        emoji="✅",
        action="Restored",
        entity_title=issue.title,
        entity_id=issue.id,
        extra_details=extra_details if extra_details else None,
    )
    for line in lines:
        console.print(line, style="bold green" if "Restored" in line else "cyan")

    return True


@click.command()
@click.argument("issue_id", required=False)
@click.option(
    "--all",
    is_flag=True,
    help="Restore all archived issues",
)
@click.option(
    "--status",
    type=click.Choice(["todo", "in-progress", "blocked", "review", "closed"]),
    help="Set status when restoring (default: keep current status)",
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
@log_command("issue_restore", entity_type="issue", track_duration=True)
@require_initialized
def restore_issue(
    ctx: click.Context,
    issue_id: str | None,
    all: bool,
    status: str | None,
    dry_run: bool,
    force: bool,
    verbose: bool,
):
    """Restore an archived issue back to active issues.

    This moves an issue from .roadmap/archive/issues/ back to
    .roadmap/issues/, making it active again. Optionally update
    the status when restoring.

    Examples:
        roadmap issue restore 8a00a17e
        roadmap issue restore 8a00a17e --status todo
        roadmap issue restore --all
        roadmap issue restore 8a00a17e --dry-run
    """
    core = ctx.obj["core"]

    if not _validate_restore_arguments(issue_id, all):
        ctx.exit(1)

    try:
        roadmap_dir = Path.cwd() / ".roadmap"
        archive_dir = roadmap_dir / "archive" / "issues"
        active_dir = roadmap_dir / "issues"

        if not _check_archive_exists(archive_dir):
            return

        if all:
            issues_info = _get_archived_issues(archive_dir)
            if not issues_info:
                return

            _restore_multiple_issues(
                core, archive_dir, active_dir, issues_info, status, dry_run, force
            )
        else:
            _restore_single_issue(
                core, archive_dir, active_dir, issue_id, status, dry_run, force
            )

    except Exception as e:
        log_error_with_context(
            e,
            operation="issue_restore",
            entity_type="issue",
            entity_id=issue_id,
        )
        console.print(f"❌ Failed to restore issue: {e}", style="bold red")
        ctx.exit(1)
