"""Presenter for cleanup command output."""

from pathlib import Path
from typing import Any

import click

from roadmap.core.services.health.backup_cleanup_service import (
    BackupCleanupResult as BackupResult,
)
from roadmap.core.services.health.file_repair_service import FileRepairResult


class CleanupPresenter:
    """Handles all console output for cleanup operations."""

    def __init__(self):
        """Initialize presenter."""
        pass

    def present_no_roadmap(self) -> None:
        """Show message that roadmap is not initialized."""
        click.secho(
            "❌ Roadmap not initialized. Run 'roadmap init' first.",
            fg="red",
            bold=True,
        )

    def present_no_issues_dir(self) -> None:
        """Show message that issues directory not found."""
        click.secho("📋 No issues directory found.", fg="yellow")

    def present_folder_check_clean(self) -> None:
        """Show message that all issues are in correct folders."""
        click.secho(
            "✅ All issues appear to be in correct folders.",
            fg="green",
        )

    def present_folder_issues(self, issues: dict[str, Any]) -> None:
        """Show folder structure issues found."""
        if "misplaced" in issues and issues["misplaced"]:
            click.secho(
                f"\n⚠️  Found {len(issues['misplaced'])} issue(s) in wrong folders:\n",
                fg="yellow",
                bold=True,
            )
            for item in issues["misplaced"]:
                click.secho(f"  • {item['issue_id']}: {item['title']}", fg="cyan")
                click.echo(f"    Current: {item['current_location']}")
                click.echo(f"    Expected: {item['expected_location']}")
            click.echo()

        if "orphaned" in issues and issues["orphaned"]:
            click.secho(
                f"\n⚠️  Found {len(issues['orphaned'])} orphaned issue(s):\n",
                fg="yellow",
                bold=True,
            )
            for item in issues["orphaned"]:
                click.secho(f"  • {item['issue_id']}: {item['title']}", fg="cyan")
                click.echo(f"    Location: {item['location']}")
            click.echo()

    def present_duplicates_check_clean(self) -> None:
        """Show message that no duplicates found."""
        click.secho(
            "✅ No duplicate issues found.",
            fg="green",
        )

    def present_duplicate_issues(
        self, duplicates: dict[str, list[Path]], roadmap_dir: Path
    ) -> None:
        """Show duplicate issues found."""
        click.secho(
            f"\n⚠️  Found {len(duplicates)} issue(s) with multiple copies:\n",
            fg="yellow",
            bold=True,
        )

        for issue_id, files in sorted(duplicates.items()):
            click.secho(f"  Issue ID: {issue_id}", fg="cyan")
            for file_path in sorted(files):
                click.echo(f"    • {file_path.relative_to(roadmap_dir)}")
            click.echo()

    def present_malformed_check_clean(self) -> None:
        """Show message that no malformed files found."""
        click.secho(
            "✅ No malformed YAML files found.",
            fg="green",
        )

    def present_malformed_files(self, malformed_files: list[str]) -> None:
        """Show malformed files found."""
        click.secho(
            f"\n⚠️  Found {len(malformed_files)} malformed file(s):\n",
            fg="yellow",
            bold=True,
        )

        for file_rel in malformed_files:
            click.secho(f"  • {file_rel}", fg="cyan")
        click.echo()

    def present_backup_cleanup_dry_run(
        self, files_to_delete: list[dict[str, Any]]
    ) -> None:
        """Show what backups would be deleted in dry-run mode."""
        total_size = sum(f["size"] for f in files_to_delete)
        size_mb = total_size / (1024 * 1024)

        click.secho(
            f"\n🔍 [DRY RUN] Would delete {len(files_to_delete)} backup file(s) ({size_mb:.2f} MB):\n",
            fg="blue",
            bold=True,
        )
        for backup in files_to_delete:
            click.secho(
                f"  • {backup['path'].name} ({backup['size']} bytes)",
                fg="cyan",
            )
        click.secho(
            f"\nWould free approximately {size_mb:.2f} MB of disk space.",
            fg="green",
        )

    def present_backup_cleanup_result(self, result: BackupResult) -> None:
        """Show backup cleanup results."""
        click.secho(
            f"✅ Cleaned up {result.deleted_count} backup file(s), freed ~{result.freed_mb:.2f} MB",
            fg="green",
            bold=True,
        )
        if result.failed_count > 0:
            click.secho(
                f"⚠️  {result.failed_count} file(s) failed to delete", fg="yellow"
            )

    def present_malformed_repair_result(self, result: FileRepairResult) -> None:
        """Show malformed file repair results."""
        if result.fixed_files:
            click.secho(
                f"✅ Fixed {len(result.fixed_files)} file(s)",
                fg="green",
            )
            for file_rel in result.fixed_files:
                click.echo(f"  • {file_rel}")

        if result.errors:
            click.secho(
                f"⚠️  Could not fix {len(result.errors)} file(s)",
                fg="yellow",
            )
            for file_rel in result.errors:
                click.echo(f"  • {file_rel}")

    def present_folder_moves(self, moves_to_make: list[dict[str, Any]]) -> None:
        """Show folder moves that will be made."""
        click.secho(
            f"\n🔧 Resolving {len(moves_to_make)} issue(s) with folder structure problems:\n",
            fg="blue",
            bold=True,
        )

        for move in moves_to_make:
            click.secho(
                f"    {move['issue_id']}: {move['from']} → {move['to']}",
                fg="cyan",
            )

    def present_folder_moves_result(self, moved_count: int, failed_count: int) -> None:
        """Show folder move results."""
        click.secho(
            f"✅ Moved {moved_count} issue file(s) to correct folders",
            fg="green",
            bold=True,
        )
        if failed_count > 0:
            click.secho(f"⚠️  {failed_count} file(s) failed to move", fg="yellow")

    def present_duplicate_resolution(
        self, duplicates: dict[str, list[Path]], roadmap_dir: Path
    ) -> None:
        """Show duplicate issue resolution."""
        click.secho(
            f"\n�� Resolving {len(duplicates)} duplicate issue(s) (keeping latest):\n",
            fg="blue",
            bold=True,
        )

        for issue_id, files in sorted(duplicates.items()):
            click.secho(f"  Issue ID: {issue_id}", fg="cyan")

            sorted_files = sorted(files, key=lambda f: f.stat().st_mtime, reverse=True)
            keeper = sorted_files[0]
            to_remove = sorted_files[1:]

            click.secho(f"    Keeping: {keeper.relative_to(roadmap_dir)}", fg="green")
            for f in to_remove:
                click.secho(f"    Removing: {f.relative_to(roadmap_dir)}", fg="red")

    def present_duplicate_resolution_result(
        self, deleted_count: int, failed_count: int
    ) -> None:
        """Show duplicate resolution results."""
        click.secho(
            f"✅ Deleted {deleted_count} duplicate file(s)",
            fg="green",
            bold=True,
        )
        if failed_count > 0:
            click.secho(f"⚠️  {failed_count} file(s) failed to delete", fg="yellow")

    def present_cleanup_error(self, error: str) -> None:
        """Show cleanup error."""
        click.secho(f"❌ Cleanup failed: {error}", fg="red", bold=True)

    def present_dry_run_skipped(self) -> None:
        """Show message about dry-run skipping certain operations."""
        click.echo(
            "\n[DRY RUN] Folder and duplicate resolution skipped in preview mode"
        )

    def present_no_backups(self) -> None:
        """Show message that no backups found."""
        click.secho("📋 No backup files found.", fg="yellow")

    def present_no_cleanup_needed(self) -> None:
        """Show message that no cleanup is needed."""
        click.secho(
            "✅ No backup files need to be cleaned up.",
            fg="green",
        )
