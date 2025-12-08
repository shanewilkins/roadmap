"""Archive issue command - move completed issues to archive."""

from pathlib import Path

import click
from rich.console import Console

from roadmap.adapters.cli.helpers import require_initialized
from roadmap.adapters.persistence.parser import IssueParser
from roadmap.infrastructure.logging import (
    log_command,
    log_error_with_context,
    verbose_output,
)

console = Console()


def _determine_archive_path(
    archive_dir: Path, issue_file: Path, issues_dir: Path
) -> Path:
    """Determine archive path preserving folder structure.

    If issue is in a subfolder (e.g., backlog, v.0.6.0), preserve that structure
    in the archive. Otherwise, place in root archive directory.

    Args:
        archive_dir: The archive root directory
        issue_file: The issue file path
        issues_dir: The active issues directory

    Returns:
        The destination path for archiving
    """
    # Get relative path from issues_dir to issue_file
    try:
        rel_path = issue_file.relative_to(issues_dir)
    except ValueError:
        # File is not under issues_dir, put in root
        return archive_dir / issue_file.name

    # If file is directly in issues_dir (no parent folder), put in archive root
    if len(rel_path.parts) == 1:
        return archive_dir / issue_file.name

    # Preserve the parent folder structure
    # e.g., backlog/c0850c90-fix.md -> archive/issues/backlog/c0850c90-fix.md
    dest_dir = archive_dir / rel_path.parent
    dest_dir.mkdir(parents=True, exist_ok=True)
    return dest_dir / issue_file.name


def _show_archived_issues():
    """Display list of archived issues."""
    roadmap_dir = Path.cwd() / ".roadmap"
    archive_dir = roadmap_dir / "archive" / "issues"

    if not archive_dir.exists():
        console.print("📋 No archived issues.", style="yellow")
        return

    archived_files = list(archive_dir.rglob("*.md"))
    if not archived_files:
        console.print("📋 No archived issues.", style="yellow")
        return

    console.print("\n📦 Archived Issues:\n", style="bold blue")
    for file_path in sorted(archived_files):
        try:
            issue = IssueParser.parse_issue_file(file_path)
            milestone = issue.milestone or "No milestone"
            console.print(
                f"  • {issue.id[:8]} - {issue.title} [{milestone}] ({issue.status.value})",
                style="cyan",
            )
        except Exception:
            console.print(f"  • {file_path.stem} (parse error)", style="red")


def _validate_archive_arguments(issue_id, all_closed, orphaned):
    """Validate archive arguments."""
    if not issue_id and not all_closed and not orphaned:
        console.print(
            "❌ Error: Specify an issue ID, --all-closed, or --orphaned",
            style="bold red",
        )
        return False

    if sum([bool(issue_id), all_closed, orphaned]) > 1:
        console.print(
            "❌ Error: Specify only one of: issue ID, --all-closed, or --orphaned",
            style="bold red",
        )
        return False

    return True


def _get_issues_to_archive(core, all_closed, orphaned):
    """Get list of issues to archive and description."""
    all_issues = core.issues.list()

    if all_closed:
        return [i for i in all_issues if i.status.value == "closed"], "closed"
    else:  # orphaned
        return [i for i in all_issues if not i.milestone], "orphaned (no milestone)"


def _find_issue_file(roadmap_dir, issue_id):
    """Find issue file by ID."""
    issue_files = list((roadmap_dir / "issues").rglob(f"{issue_id[:8]}*.md"))
    return issue_files[0] if issue_files else None


def _archive_issue_file(core, archive_dir, issue_file, roadmap_dir, issue_id):
    """Archive a single issue file."""
    archive_file = _determine_archive_path(
        archive_dir, issue_file, roadmap_dir / "issues"
    )
    issue_file.rename(archive_file)

    try:
        core.db.mark_issue_archived(issue_id, archived=True)
    except Exception as e:
        console.print(
            f"⚠️  Warning: Failed to mark issue {issue_id} as archived: {e}",
            style="yellow",
        )


def _archive_multiple_issues(
    core, roadmap_dir, issues_to_archive, description, dry_run, force
):
    """Archive multiple issues by criteria."""
    if not issues_to_archive:
        console.print(f"📋 No {description} issues to archive.", style="yellow")
        return True

    if dry_run:
        console.print(
            f"\n🔍 [DRY RUN] Would archive {len(issues_to_archive)} {description} issue(s):\n",
            style="bold blue",
        )
        for issue in issues_to_archive:
            console.print(f"  • {issue.id[:8]} - {issue.title}", style="cyan")
        return True

    if not force:
        console.print(
            f"\n⚠️  About to archive {len(issues_to_archive)} {description} issue(s):",
            style="bold yellow",
        )
        for issue in issues_to_archive:
            console.print(f"  • {issue.id[:8]} - {issue.title}", style="cyan")

        if not click.confirm("\nProceed with archival?", default=False):
            console.print("❌ Cancelled.", style="yellow")
            return False

    archive_dir = roadmap_dir / "archive" / "issues"
    archive_dir.mkdir(parents=True, exist_ok=True)
    archived_count = 0

    for issue in issues_to_archive:
        issue_file = _find_issue_file(roadmap_dir, issue.id)
        if issue_file:
            _archive_issue_file(core, archive_dir, issue_file, roadmap_dir, issue.id)
            archived_count += 1

    console.print(
        f"\n✅ Archived {archived_count} issue(s) to .roadmap/archive/issues/",
        style="bold green",
    )
    return True


def _archive_single_issue(core, roadmap_dir, issue_id, dry_run, force):
    """Archive a single issue."""
    issue = core.issues.get(issue_id)
    if not issue:
        console.print(f"❌ Issue '{issue_id}' not found.", style="bold red")
        return False

    if issue.status.value != "closed":
        console.print(
            f"⚠️  Warning: Issue '{issue_id}' is not closed (status: {issue.status.value})",
            style="bold yellow",
        )
        if not force and not click.confirm("Archive anyway?", default=False):
            console.print("❌ Cancelled.", style="yellow")
            return False

    if dry_run:
        console.print(
            f"\n🔍 [DRY RUN] Would archive issue: {issue_id}",
            style="bold blue",
        )
        console.print(f"  Title: {issue.title}", style="cyan")
        console.print(f"  Status: {issue.status.value}", style="cyan")
        return True

    if not force and not click.confirm(
        f"Archive issue '{issue_id}' ({issue.title})?", default=False
    ):
        console.print("❌ Cancelled.", style="yellow")
        return False

    archive_dir = roadmap_dir / "archive" / "issues"
    archive_dir.mkdir(parents=True, exist_ok=True)

    issue_file = _find_issue_file(roadmap_dir, issue_id)
    if not issue_file:
        console.print(f"❌ Issue file not found for: {issue_id}", style="bold red")
        return False

    _archive_issue_file(core, archive_dir, issue_file, roadmap_dir, issue.id)
    console.print(
        f"\n✅ Archived issue '{issue_id}' to .roadmap/archive/issues/",
        style="bold green",
    )
    return True


@click.command()
@click.argument("issue_id", required=False)
@click.option(
    "--all-closed",
    is_flag=True,
    help="Archive all closed issues",
)
@click.option(
    "--orphaned",
    is_flag=True,
    help="Archive issues with no milestone assigned",
)
@click.option(
    "--list",
    "list_archived",
    is_flag=True,
    help="List archived issues",
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
@log_command("issue_archive", entity_type="issue", track_duration=True)
@require_initialized
def archive_issue(
    ctx: click.Context,
    issue_id: str | None,
    all_closed: bool,
    orphaned: bool,
    list_archived: bool,
    dry_run: bool,
    force: bool,
    verbose: bool,
):
    """Archive an issue by moving it to .roadmap/archive/issues/.

    This is a non-destructive operation that preserves issue data while
    cleaning up the active workspace. Archived issues can be restored
    if needed.

    Examples:
        roadmap issue archive 8a00a17e
        roadmap issue archive --all-closed
        roadmap issue archive --orphaned --dry-run
        roadmap issue archive --list
    """
    core = ctx.obj["core"]

    if list_archived:
        _show_archived_issues()
        return

    if not _validate_archive_arguments(issue_id, all_closed, orphaned):
        ctx.exit(1)

    try:
        roadmap_dir = Path.cwd() / ".roadmap"

        if all_closed or orphaned:
            issues_to_archive, description = _get_issues_to_archive(
                core, all_closed, orphaned
            )
            _archive_multiple_issues(
                core, roadmap_dir, issues_to_archive, description, dry_run, force
            )
        else:
            _archive_single_issue(core, roadmap_dir, issue_id, dry_run, force)

    except Exception as e:
        log_error_with_context(
            e,
            operation="issue_archive",
            entity_type="issue",
            entity_id=issue_id,
        )
        console.print(f"❌ Failed to archive issue: {e}", style="bold red")
        ctx.exit(1)
