"""Archive issue command - move completed issues to archive."""

import click

from roadmap.adapters.cli.helpers import require_initialized
from roadmap.adapters.cli.issues.archive_class import IssueArchive
from roadmap.common.console import get_console
from roadmap.infrastructure.logging import (
    log_command,
    verbose_output,
)


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
    verbose: bool,  # noqa: F841
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
    console = get_console()

    archive = IssueArchive(core, console)

    if list_archived:
        # List archived issues
        from pathlib import Path

        from roadmap.adapters.persistence.parser import IssueParser

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
                console.print(
                    f"  • {file_path.name} (error reading file)", style="yellow"
                )
        return

    # Validate arguments
    if not issue_id and not all_closed and not orphaned:
        console.print(
            "❌ Error: Specify an issue ID, --all-closed, or --orphaned",
            style="bold red",
        )
        ctx.exit(1)

    if sum([bool(issue_id), all_closed, orphaned]) > 1:
        console.print(
            "❌ Error: Specify only one of: issue ID, --all-closed, or --orphaned",
            style="bold red",
        )
        ctx.exit(1)

    try:
        archive.execute(
            entity_id=issue_id,
            all_closed=all_closed,
            orphaned=orphaned,
            dry_run=dry_run,
            force=force,
        )
    except Exception as e:
        console.print(f"❌ Archive operation failed: {str(e)}", style="bold red")
        ctx.exit(1)
