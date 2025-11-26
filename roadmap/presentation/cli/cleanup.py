"""Cleanup command - prune old backup files and optimize storage."""

from datetime import datetime, timedelta
from pathlib import Path

import click
from rich.console import Console

console = Console()


@click.command()
@click.option(
    "--keep",
    type=int,
    default=10,
    help="Number of most recent backups to keep per issue (default: 10)",
)
@click.option(
    "--days",
    type=int,
    help="Delete backups older than this many days (default: no age-based limit)",
)
@click.option(
    "--list",
    is_flag=True,
    help="List files that would be deleted without actually deleting",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Preview what would be deleted without actually doing it",
)
@click.option(
    "--force",
    is_flag=True,
    help="Skip confirmation prompt",
)
@click.pass_context
def cleanup(
    ctx: click.Context,
    keep: int,
    days: int | None,
    list: bool,
    dry_run: bool,
    force: bool,
):
    """Clean up old backup files to optimize storage.

    By default, keeps the 10 most recent backups per issue. You can also
    delete backups older than a specified number of days.

    Examples:
        roadmap cleanup                          # Keep 10 per issue
        roadmap cleanup --keep 5                 # Keep 5 per issue
        roadmap cleanup --days 30                # Delete backups > 30 days old
        roadmap cleanup --keep 5 --days 30       # Both constraints
        roadmap cleanup --dry-run                # Preview deletions
        roadmap cleanup --list                   # List what would be deleted
    """
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.",
            style="bold red",
        )
        ctx.exit(1)

    try:
        roadmap_dir = Path.cwd() / ".roadmap"
        backups_dir = roadmap_dir / "backups"

        if not backups_dir.exists():
            console.print("📋 No backup directory found.", style="yellow")
            return

        backup_files = list(backups_dir.glob("*.backup.md"))  # type: ignore[func-returns-value]
        if not backup_files:
            console.print("📋 No backup files found.", style="yellow")
            return

        # Group backups by issue ID
        backups_by_issue = {}
        for backup_file in backup_files:
            # Extract issue ID from filename (e.g., invalid_issue_TIMESTAMP.backup.md)
            # Assuming format: {issue_id}_{timestamp}.backup.md or similar
            parts = backup_file.stem.split("_")
            # Find the issue identifier - typically everything before the timestamp
            # Timestamps are typically 14+ digits (YYYYMMDDhhmmss format)
            issue_key = "_".join(parts[:-1])  # Everything except the timestamp part

            if issue_key not in backups_by_issue:
                backups_by_issue[issue_key] = []

            stat = backup_file.stat()
            backups_by_issue[issue_key].append(
                {
                    "path": backup_file,
                    "mtime": datetime.fromtimestamp(stat.st_mtime),
                    "size": stat.st_size,
                }
            )

        # Determine files to delete
        files_to_delete = []
        cutoff_date = datetime.now() - timedelta(days=days) if days else None

        for _issue_key, backups in backups_by_issue.items():
            # Sort by modification time (newest first)
            backups.sort(key=lambda x: x["mtime"], reverse=True)

            for idx, backup in enumerate(backups):
                should_delete = False

                # Check if beyond keep threshold
                if idx >= keep:
                    should_delete = True

                # Check if older than days threshold
                if cutoff_date and backup["mtime"] < cutoff_date:
                    should_delete = True

                if should_delete:
                    files_to_delete.append(backup)

        if not files_to_delete:
            console.print(
                "✅ No backup files need to be cleaned up.",
                style="green",
            )
            return

        # Calculate savings
        total_size = sum(f["size"] for f in files_to_delete)
        size_mb = total_size / (1024 * 1024)

        # Display list mode
        if list:
            console.print(
                f"\n📋 Backup files to be deleted ({len(files_to_delete)} files, {size_mb:.2f} MB):\n",
                style="bold blue",
            )
            for backup in files_to_delete:
                mtime_str = backup["mtime"].strftime("%Y-%m-%d %H:%M:%S")
                console.print(
                    f"  • {backup['path'].name} ({backup['size']} bytes, modified {mtime_str})",
                    style="cyan",
                )
            return

        # Dry run mode
        if dry_run:
            console.print(
                f"\n🔍 [DRY RUN] Would delete {len(files_to_delete)} backup file(s) ({size_mb:.2f} MB):\n",
                style="bold blue",
            )
            for backup in files_to_delete:
                mtime_str = backup["mtime"].strftime("%Y-%m-%d %H:%M:%S")
                console.print(
                    f"  • {backup['path'].name} ({backup['size']} bytes)",
                    style="cyan",
                )
            console.print(
                f"\nWould free approximately {size_mb:.2f} MB of disk space.",
                style="green",
            )
            return

        # Confirm deletion
        if not force:
            console.print(
                f"\n⚠️  About to delete {len(files_to_delete)} backup file(s) ({size_mb:.2f} MB):",
                style="bold yellow",
            )
            console.print(
                f"  This will free approximately {size_mb:.2f} MB of disk space.",
                style="yellow",
            )

            if not click.confirm("\nProceed with cleanup?", default=False):
                console.print("❌ Cancelled.", style="yellow")
                return

        # Perform deletion
        deleted_count = 0
        failed_count = 0

        for backup in files_to_delete:
            try:
                backup["path"].unlink()
                deleted_count += 1
            except Exception as e:
                console.print(
                    f"⚠️  Failed to delete {backup['path'].name}: {e}",
                    style="yellow",
                )
                failed_count += 1

        console.print(
            f"\n✅ Cleaned up {deleted_count} backup file(s), freed ~{size_mb:.2f} MB",
            style="bold green",
        )
        if failed_count > 0:
            console.print(f"⚠️  {failed_count} file(s) failed to delete", style="yellow")

    except Exception as e:
        console.print(f"❌ Cleanup failed: {e}", style="bold red")
        ctx.exit(1)
