"""Cleanup command - prune old backup files and optimize storage."""

from datetime import datetime, timedelta
from pathlib import Path

import click
from rich.console import Console

from roadmap.application.health import (
    scan_for_duplicate_issues,
    scan_for_folder_structure_issues,
)

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
    "list_files",
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
@click.option(
    "--check-duplicates",
    is_flag=True,
    help="Scan for duplicate issues across folders",
)
@click.option(
    "--check-folders",
    is_flag=True,
    help="Verify issues are in correct milestone folders",
)
@click.option(
    "--resolve-duplicates",
    type=click.Choice(
        ["keep-latest", "keep-milestone", "keep-largest"], case_sensitive=False
    ),
    help="Resolve duplicate issues using specified strategy",
)
@click.option(
    "--resolve-folders",
    is_flag=True,
    help="Move issues to correct milestone folders",
)
@click.pass_context
def cleanup(
    ctx: click.Context,
    keep: int,
    days: int | None,
    list_files: bool,
    dry_run: bool,
    force: bool,
    check_duplicates: bool,
    check_folders: bool,
    resolve_duplicates: str | None,
    resolve_folders: bool,
):
    """Clean up old backup files to optimize storage.

    By default, keeps the 10 most recent backups per issue. You can also
    delete backups older than a specified number of days.

    Use --check-duplicates to scan for issues with the same ID in multiple
    folders (conservative - lists for manual review).

    Use --check-folders to verify issues are in correct milestone folders
    (conservative - lists potential misplacements for manual review).

    Examples:
        roadmap cleanup                          # Keep 10 per issue
        roadmap cleanup --keep 5                 # Keep 5 per issue
        roadmap cleanup --days 30                # Delete backups > 30 days old
        roadmap cleanup --check-duplicates       # List duplicate issues
        roadmap cleanup --check-folders          # List folder structure issues
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

    roadmap_dir = Path.cwd() / ".roadmap"
    issues_dir = roadmap_dir / "issues"

    # Handle duplicate detection
    if check_duplicates:
        if not issues_dir.exists():
            console.print("📋 No issues directory found.", style="yellow")
            return

        duplicates = scan_for_duplicate_issues(issues_dir)

        if not duplicates:
            console.print(
                "✅ No duplicate issues found.",
                style="green",
            )
            return

        console.print(
            f"\n⚠️  Found {len(duplicates)} issue(s) with multiple copies:\n",
            style="bold yellow",
        )

        for issue_id, files in sorted(duplicates.items()):
            console.print(f"  Issue ID: {issue_id}", style="cyan")
            for file_path in sorted(files):
                console.print(
                    f"    • {file_path.relative_to(roadmap_dir)}", style="dim"
                )
            console.print()

        console.print(
            "💡 Review these manually to determine which copy should be kept.",
            style="yellow",
        )
        return

    # Handle folder verification
    if check_folders:
        if not issues_dir.exists():
            console.print("📋 No issues directory found.", style="yellow")
            return

        issues = scan_for_folder_structure_issues(issues_dir, core)

        if not issues:
            console.print(
                "✅ All issues appear to be in correct folders.",
                style="green",
            )
            return

        if "misplaced" in issues and issues["misplaced"]:
            console.print(
                f"\n⚠️  Found {len(issues['misplaced'])} issue(s) in root that belong in milestone folders:\n",
                style="bold yellow",
            )
            for item in issues["misplaced"]:
                console.print(f"  • {item['issue_id']}: {item['title']}", style="cyan")
                console.print(f"    Current: {item['current_location']}", style="dim")
                console.print(f"    Expected: {item['expected_location']}", style="dim")
            console.print()

        if "orphaned" in issues and issues["orphaned"]:
            console.print(
                f"\n⚠️  Found {len(issues['orphaned'])} issue(s) in milestone folders without milestone assignments:\n",
                style="bold yellow",
            )
            for item in issues["orphaned"]:
                console.print(f"  • {item['issue_id']}: {item['title']}", style="cyan")
                console.print(f"    Location: {item['location']}", style="dim")
                console.print(f"    In folder: {item['folder']}", style="dim")
            console.print()

        console.print(
            "💡 Review these manually and use 'roadmap issue update' to move if needed.",
            style="yellow",
        )
        return

    # Handle duplicate resolution
    if resolve_duplicates:
        if not issues_dir.exists():
            console.print("📋 No issues directory found.", style="yellow")
            return

        duplicates = scan_for_duplicate_issues(issues_dir)

        if not duplicates:
            console.print("✅ No duplicate issues found.", style="green")
            return

        console.print(
            f"\n🔧 Resolving {len(duplicates)} duplicate issue(s) using '{resolve_duplicates}' strategy:\n",
            style="bold blue",
        )

        files_to_delete = []

        for issue_id, files in sorted(duplicates.items()):
            console.print(f"  Issue ID: {issue_id}", style="cyan")

            # Sort files by strategy
            if resolve_duplicates.lower() == "keep-latest":
                # Keep file with newest modification time
                sorted_files = sorted(
                    files, key=lambda f: f.stat().st_mtime, reverse=True
                )
            elif resolve_duplicates.lower() == "keep-milestone":
                # Prefer milestone folder version
                milestone_files = [
                    f
                    for f in files
                    if ".roadmap/issues/"
                    not in str(f).replace(".roadmap/issues/", "").split("/")[0]
                ]
                sorted_files = milestone_files if milestone_files else files
                sorted_files = sorted(
                    sorted_files, key=lambda f: f.stat().st_mtime, reverse=True
                )
            elif resolve_duplicates.lower() == "keep-largest":
                # Keep file with larger size
                sorted_files = sorted(
                    files, key=lambda f: f.stat().st_size, reverse=True
                )
            else:
                sorted_files = files

            keeper = sorted_files[0]
            to_remove = sorted_files[1:]

            console.print(
                f"    Keeping: {keeper.relative_to(roadmap_dir)}", style="green"
            )
            for f in to_remove:
                console.print(
                    f"    Removing: {f.relative_to(roadmap_dir)}", style="red"
                )
                files_to_delete.append(f)

        if not files_to_delete:
            console.print("\n✅ No files to remove.", style="green")
            return

        # Dry run mode
        if dry_run:
            console.print(
                f"\n🔍 [DRY RUN] Would delete {len(files_to_delete)} file(s):\n",
                style="bold blue",
            )
            for f in files_to_delete:
                console.print(f"  • {f.relative_to(roadmap_dir)}", style="cyan")
            return

        # Confirm deletion
        if not force:
            console.print(
                f"\n⚠️  About to delete {len(files_to_delete)} file(s):",
                style="bold yellow",
            )

            if not click.confirm("\nProceed with deletion?", default=False):
                console.print("❌ Cancelled.", style="yellow")
                return

        # Perform deletion
        deleted_count = 0
        failed_count = 0

        for f in files_to_delete:
            try:
                f.unlink()
                deleted_count += 1
            except Exception as e:
                console.print(
                    f"⚠️  Failed to delete {f.name}: {e}",
                    style="yellow",
                )
                failed_count += 1

        console.print(
            f"\n✅ Deleted {deleted_count} duplicate file(s)",
            style="bold green",
        )
        if failed_count > 0:
            console.print(f"⚠️  {failed_count} file(s) failed to delete", style="yellow")
        return

    # Handle folder resolution
    if resolve_folders:
        if not issues_dir.exists():
            console.print("📋 No issues directory found.", style="yellow")
            return

        issues = scan_for_folder_structure_issues(issues_dir, core)

        if not issues:
            console.print("✅ All issues are in correct folders.", style="green")
            return

        misplaced_count = len(issues.get("misplaced", []))
        orphaned_count = len(issues.get("orphaned", []))
        total = misplaced_count + orphaned_count

        console.print(
            f"\n🔧 Resolving {total} issue(s) with folder structure problems:\n",
            style="bold blue",
        )

        moves_to_make = []

        # Handle misplaced issues
        if misplaced_count:
            console.print(
                f"  Moving {misplaced_count} issue(s) to milestone folders:",
                style="yellow",
            )
            for item in issues["misplaced"]:
                console.print(
                    f"    {item['issue_id']}: {item['current_location']} → {item['expected_location']}",
                    style="cyan",
                )
                moves_to_make.append(
                    {
                        "from": Path(item["current_location"]),
                        "to": Path(item["expected_location"]),
                        "issue_id": item["issue_id"],
                    }
                )

        # Handle orphaned issues
        if orphaned_count:
            console.print(
                f"  Moving {orphaned_count} issue(s) to backlog:", style="yellow"
            )
            for item in issues["orphaned"]:
                backlog_dest = issues_dir / "backlog" / Path(item["location"]).name
                console.print(
                    f"    {item['issue_id']}: {item['location']} → {backlog_dest}",
                    style="cyan",
                )
                moves_to_make.append(
                    {
                        "from": Path(item["location"]),
                        "to": backlog_dest,
                        "issue_id": item["issue_id"],
                    }
                )

        if not moves_to_make:
            console.print("\n✅ No moves to make.", style="green")
            return

        # Dry run mode
        if dry_run:
            console.print(
                f"\n🔍 [DRY RUN] Would move {len(moves_to_make)} file(s)",
                style="bold blue",
            )
            return

        # Confirm moves
        if not force:
            console.print(
                f"\n⚠️  About to move {len(moves_to_make)} file(s):",
                style="bold yellow",
            )

            if not click.confirm("\nProceed with moves?", default=False):
                console.print("❌ Cancelled.", style="yellow")
                return

        # Perform moves
        moved_count = 0
        failed_count = 0

        for move in moves_to_make:
            try:
                # Create destination directory if needed
                move["to"].parent.mkdir(parents=True, exist_ok=True)
                # Move the file
                move["from"].rename(move["to"])
                moved_count += 1
            except Exception as e:
                console.print(
                    f"⚠️  Failed to move {move['from'].name}: {e}",
                    style="yellow",
                )
                failed_count += 1

        console.print(
            f"\n✅ Moved {moved_count} issue file(s) to correct folders",
            style="bold green",
        )
        if failed_count > 0:
            console.print(f"⚠️  {failed_count} file(s) failed to move", style="yellow")
        return

    # Handle backup cleanup (original functionality)
    try:
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
        if list_files:
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
