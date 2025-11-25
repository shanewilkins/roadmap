"""Restore issue command - move archived issues back to active."""

from pathlib import Path

import click  # type: ignore[import-untyped]
from rich.console import Console  # type: ignore[import-untyped]

from roadmap.infrastructure.persistence.parser import IssueParser
from roadmap.presentation.cli.logging_decorators import log_command

console = Console()


@click.command()
@click.argument("issue_id", required=False)
@click.option(
    "--all",
    is_flag=True,
    help="Restore all archived issues",
)
@click.option(
    "--status",
    type=click.Choice(["todo", "in-progress", "blocked", "review", "done"]),
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
@click.pass_context
@log_command("issue_restore", entity_type="issue", track_duration=True)
def restore_issue(
    ctx: click.Context,
    issue_id: str | None,
    all: bool,
    status: str | None,
    dry_run: bool,
    force: bool,
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

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.",
            style="bold red",
        )
        ctx.exit(1)

    if not issue_id and not all:
        console.print(
            "❌ Error: Specify an issue ID or use --all",
            style="bold red",
        )
        ctx.exit(1)

    if issue_id and all:
        console.print(
            "❌ Error: Cannot specify issue ID with --all",
            style="bold red",
        )
        ctx.exit(1)

    try:
        roadmap_dir = Path.cwd() / ".roadmap"
        archive_dir = roadmap_dir / "archive" / "issues"
        active_dir = roadmap_dir / "issues"

        if not archive_dir.exists():
            console.print(
                "📋 No archived issues found.",
                style="yellow",
            )
            return

        if all:
            # Get all archived issue files
            archived_files = list(archive_dir.glob("*.md"))

            if not archived_files:
                console.print("📋 No archived issues to restore.", style="yellow")
                return

            # Parse issue info
            issues_info = []
            for file_path in archived_files:
                try:
                    issue = IssueParser.parse_issue_file(file_path)
                    issues_info.append((file_path, issue.id, issue.title))
                except Exception:
                    continue

            if not issues_info:
                console.print("📋 No valid archived issues found.", style="yellow")
                return

            if dry_run:
                console.print(
                    f"\n🔍 [DRY RUN] Would restore {len(issues_info)} issue(s):\n",
                    style="bold blue",
                )
                for _, id, title in issues_info:
                    console.print(f"  • {id[:8]} - {title}", style="cyan")
                if status:
                    console.print(f"\n  Status would be set to: {status}", style="cyan")
                return

            # Confirm
            if not force:
                console.print(
                    f"\n⚠️  About to restore {len(issues_info)} archived issue(s):",
                    style="bold yellow",
                )
                for _, id, title in issues_info:
                    console.print(f"  • {id[:8]} - {title}", style="cyan")
                if status:
                    console.print(
                        f"\n  Status will be set to: {status}", style="yellow"
                    )

                if not click.confirm("\nProceed with restore?", default=False):
                    console.print("❌ Cancelled.", style="yellow")
                    return

            # Restore each issue
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

                    # Update status if requested
                    if status:
                        issue = IssueParser.parse_issue_file(file_path)
                        # Update via core to ensure proper handling
                        file_path.rename(dest_file)
                        # Re-load and update status
                        core.update_issue(id, status=status)
                    else:
                        file_path.rename(dest_file)

                    # Mark as unarchived in database
                    try:
                        core.db.mark_issue_archived(id, archived=False)
                    except Exception as e:
                        console.print(
                            f"⚠️  Warning: Failed to mark issue {id} as restored in database: {e}",
                            style="yellow",
                        )

                    restored_count += 1

            console.print(
                f"\n✅ Restored {restored_count} issue(s) to .roadmap/issues/",
                style="bold green",
            )
            if status:
                console.print(f"   Status set to: {status}", style="green")

        else:
            # Restore single issue - find it in archive using partial ID
            archived_file = None
            for file_path in archive_dir.glob(f"{issue_id[:8]}*.md"):  # type: ignore[index]
                archived_file = file_path
                break

            if not archived_file or not archived_file.exists():
                console.print(
                    f"❌ Archived issue '{issue_id}' not found.",
                    style="bold red",
                )
                ctx.exit(1)

            # Parse to get full info
            try:
                issue = IssueParser.parse_issue_file(archived_file)  # type: ignore[arg-type]
            except Exception as e:
                console.print(
                    f"❌ Failed to parse archived issue: {e}",
                    style="bold red",
                )
                ctx.exit(1)

            # Check if already exists in active
            dest_file = active_dir / archived_file.name  # type: ignore[union-attr]
            if dest_file.exists():
                console.print(
                    f"❌ Issue '{issue_id}' already exists in active issues.",
                    style="bold red",
                )
                ctx.exit(1)

            if dry_run:
                console.print(
                    f"\n🔍 [DRY RUN] Would restore issue: {issue.id[:8]} - {issue.title}",
                    style="bold blue",
                )
                console.print(
                    f"  Source: .roadmap/archive/issues/{archived_file.name}",  # type: ignore[union-attr]
                    style="cyan",
                )
                console.print(
                    f"  Destination: .roadmap/issues/{archived_file.name}",  # type: ignore[union-attr]
                    style="cyan",
                )
                if status:
                    console.print(
                        f"  Status would be set to: {status}",
                        style="cyan",
                    )
                return

            # Confirm
            if not force:
                msg = f"Restore issue '{issue.id[:8]} - {issue.title}'?"
                if status:
                    msg += f" (status will be set to '{status}')"
                if not click.confirm(msg, default=False):
                    console.print("❌ Cancelled.", style="yellow")
                    return

            # Perform restore
            active_dir.mkdir(parents=True, exist_ok=True)
            archived_file.rename(dest_file)  # type: ignore[union-attr]

            # Mark as unarchived in database
            try:
                core.db.mark_issue_archived(issue.id, archived=False)
            except Exception as e:
                console.print(
                    f"⚠️  Warning: Failed to mark in database: {e}", style="yellow"
                )

            # Update status if requested
            if status:
                core.update_issue(issue.id, status=status)

            console.print(
                f"\n✅ Restored issue '{issue.id[:8]}' to .roadmap/issues/",
                style="bold green",
            )
            if status:
                console.print(f"   Status set to: {status}", style="green")

    except Exception as e:
        console.print(f"❌ Failed to restore issue: {e}", style="bold red")
        ctx.exit(1)
