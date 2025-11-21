"""Archive issue command - move completed issues to archive."""

from pathlib import Path

import click
from rich.console import Console

from roadmap.infrastructure.persistence.parser import IssueParser

console = Console()


@click.command()
@click.argument("issue_id", required=False)
@click.option(
    "--all-done",
    is_flag=True,
    help="Archive all done/completed issues",
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
@click.pass_context
def archive_issue(
    ctx: click.Context,
    issue_id: str | None,
    all_done: bool,
    orphaned: bool,
    list_archived: bool,
    dry_run: bool,
    force: bool,
):
    """Archive an issue by moving it to .roadmap/archive/issues/.

    This is a non-destructive operation that preserves issue data while
    cleaning up the active workspace. Archived issues can be restored
    if needed.

    Examples:
        roadmap issue archive 8a00a17e
        roadmap issue archive --all-done
        roadmap issue archive --orphaned --dry-run
        roadmap issue archive --list
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
        archive_dir = roadmap_dir / "archive" / "issues"

        if not archive_dir.exists():
            console.print("📋 No archived issues.", style="yellow")
            return

        archived_files = list(archive_dir.glob("*.md"))
        if not archived_files:
            console.print("📋 No archived issues.", style="yellow")
            return

        console.print("\n📦 Archived Issues:\n", style="bold blue")
        for file_path in archived_files:
            try:
                issue = IssueParser.parse_issue_file(file_path)
                console.print(
                    f"  • {issue.id[:8]} - {issue.title} ({issue.status.value})",
                    style="cyan",
                )
            except Exception:
                console.print(f"  • {file_path.stem} (parse error)", style="red")
        return

    if not issue_id and not all_done and not orphaned:
        console.print(
            "❌ Error: Specify an issue ID, --all-done, or --orphaned",
            style="bold red",
        )
        ctx.exit(1)

    if sum([bool(issue_id), all_done, orphaned]) > 1:
        console.print(
            "❌ Error: Specify only one of: issue ID, --all-done, or --orphaned",
            style="bold red",
        )
        ctx.exit(1)

    try:
        roadmap_dir = Path.cwd() / ".roadmap"
        archive_dir = roadmap_dir / "archive" / "issues"

        if all_done or orphaned:
            # Get all issues
            all_issues = core.list_issues()

            if all_done:
                issues_to_archive = [i for i in all_issues if i.status.value == "done"]
                description = "done"
            else:  # orphaned
                issues_to_archive = [i for i in all_issues if not i.milestone]
                description = "orphaned (no milestone)"

            if not issues_to_archive:
                console.print(f"📋 No {description} issues to archive.", style="yellow")
                return

            if dry_run:
                console.print(
                    f"\n🔍 [DRY RUN] Would archive {len(issues_to_archive)} {description} issue(s):\n",
                    style="bold blue",
                )
                for issue in issues_to_archive:
                    console.print(f"  • {issue.id[:8]} - {issue.title}", style="cyan")
                return

            # Confirm
            if not force:
                console.print(
                    f"\n⚠️  About to archive {len(issues_to_archive)} {description} issue(s):",
                    style="bold yellow",
                )
                for issue in issues_to_archive:
                    console.print(f"  • {issue.id[:8]} - {issue.title}", style="cyan")

                if not click.confirm("\nProceed with archival?", default=False):
                    console.print("❌ Cancelled.", style="yellow")
                    return

            # Archive each issue
            archive_dir.mkdir(parents=True, exist_ok=True)
            archived_count = 0

            for issue in issues_to_archive:
                # Find the issue file
                issue_files = list((roadmap_dir / "issues").glob(f"{issue.id[:8]}*.md"))
                if issue_files:
                    issue_file = issue_files[0]
                    archive_file = archive_dir / issue_file.name
                    issue_file.rename(archive_file)
                    archived_count += 1

            console.print(
                f"\n✅ Archived {archived_count} issue(s) to .roadmap/archive/issues/",
                style="bold green",
            )

        else:
            # Archive single issue
            issue = core.get_issue(issue_id)
            if not issue:
                console.print(f"❌ Issue '{issue_id}' not found.", style="bold red")
                ctx.exit(1)

            if issue.status.value != "done":
                console.print(
                    f"⚠️  Warning: Issue '{issue_id}' is not done (status: {issue.status.value})",
                    style="bold yellow",
                )
                if not force and not click.confirm("Archive anyway?", default=False):
                    console.print("❌ Cancelled.", style="yellow")
                    return

            if dry_run:
                console.print(
                    f"\n🔍 [DRY RUN] Would archive issue: {issue_id}",
                    style="bold blue",
                )
                console.print(f"  Title: {issue.title}", style="cyan")
                console.print(f"  Status: {issue.status.value}", style="cyan")
                return

            # Confirm
            if not force:
                if not click.confirm(
                    f"Archive issue '{issue_id}' ({issue.title})?", default=False
                ):
                    console.print("❌ Cancelled.", style="yellow")
                    return

            # Perform archive
            archive_dir.mkdir(parents=True, exist_ok=True)

            # Find the issue file
            issue_files = list((roadmap_dir / "issues").glob(f"{issue_id[:8]}*.md"))
            if issue_files:
                issue_file = issue_files[0]
                archive_file = archive_dir / issue_file.name
                issue_file.rename(archive_file)
                console.print(
                    f"\n✅ Archived issue '{issue_id}' to .roadmap/archive/issues/",
                    style="bold green",
                )
            else:
                console.print(
                    f"❌ Issue file not found for: {issue_id}", style="bold red"
                )
                ctx.exit(1)

    except Exception as e:
        console.print(f"❌ Failed to archive issue: {e}", style="bold red")
        ctx.exit(1)
