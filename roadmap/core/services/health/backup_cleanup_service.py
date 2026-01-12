"""Service for cleaning up old backup files."""

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TypedDict

from roadmap.common.logging import get_logger

logger = get_logger(__name__)


class BackupInfo(TypedDict):
    """Information about a backup file."""

    path: Path
    mtime: datetime
    size: int


class BackupCleanupResult:
    """Result of backup cleanup operation."""

    def __init__(self):
        self.deleted_count: int = 0
        self.failed_count: int = 0
        self.total_freed_bytes: int = 0
        self.files_deleted: list[Path] = []
        self.files_failed: list[tuple[Path, str]] = []

    def add_deleted(self, path: Path, size: int) -> None:
        """Record a deleted file."""
        self.deleted_count += 1
        self.total_freed_bytes += size
        self.files_deleted.append(path)

    def add_failed(self, path: Path, error: str) -> None:
        """Record a file that failed to delete."""
        self.failed_count += 1
        self.files_failed.append((path, error))

    @property
    def freed_mb(self) -> float:
        """Get freed space in MB."""
        return self.total_freed_bytes / (1024 * 1024)


class BackupCleanupService:
    """Cleans up old backup files based on age and count."""

    def cleanup_backups(
        self,
        roadmap_dir: Path,
        keep: int = 10,
        days: int | None = None,
        dry_run: bool = False,
    ) -> BackupCleanupResult:
        """Clean up old backup files.

        Args:
            roadmap_dir: Roadmap directory
            keep: Number of most recent backups to keep per issue
            days: Delete backups older than this many days
            dry_run: If True, don't delete files

        Returns:
            BackupCleanupResult with deletion statistics
        """
        backups_dir = roadmap_dir / "backups"
        result = BackupCleanupResult()

        if not backups_dir.exists():
            logger.info("No backups directory found")
            return result

        # Get files to delete
        files_to_delete = self._select_backups_for_deletion(backups_dir, keep, days)

        if not files_to_delete:
            logger.info("No backups to clean up")
            return result

        # Dry run: just record what would be deleted
        if dry_run:
            for backup in files_to_delete:
                result.add_deleted(backup["path"], backup["size"])
            logger.info(
                "Dry run: would delete backups",
                count=len(files_to_delete),
                freed_mb=result.freed_mb,
            )
            return result

        # Actually delete files
        for backup in files_to_delete:
            try:
                backup["path"].unlink()
                result.add_deleted(backup["path"], backup["size"])
                logger.info("Deleted backup file", file=backup["path"].name)
            except Exception as e:
                result.add_failed(backup["path"], str(e))
                logger.warning(
                    "Failed to delete backup", file=backup["path"].name, error=str(e)
                )

        return result

    @staticmethod
    @staticmethod
    def _group_backups_by_issue(
        backup_files: list[Path],
    ) -> dict[str, list[BackupInfo]]:
        """Group backup files by issue ID.

        Args:
            backup_files: List of backup file paths

        Returns:
            Dict of issue_key -> list of BackupInfo
        """
        backups_by_issue: dict[str, list[BackupInfo]] = {}
        for backup_file in backup_files:
            parts = backup_file.stem.split("_")
            issue_key = "_".join(parts[:-1])

            if issue_key not in backups_by_issue:
                backups_by_issue[issue_key] = []

            stat = backup_file.stat()
            backups_by_issue[issue_key].append(
                {
                    "path": backup_file,
                    "mtime": datetime.fromtimestamp(stat.st_mtime, tz=UTC),
                    "size": stat.st_size,
                }
            )

        return backups_by_issue

    @staticmethod
    def _should_delete_backup(
        idx: int, backup: BackupInfo, keep: int, cutoff_date: datetime | None
    ) -> bool:
        """Determine if backup should be deleted.

        Args:
            idx: Index in sorted backup list
            backup: Backup info dict
            keep: Keep this many most recent backups
            cutoff_date: Delete backups older than this date

        Returns:
            True if backup should be deleted
        """
        # Delete if beyond keep count
        if idx >= keep:
            return True

        # Delete if older than cutoff
        if cutoff_date and backup["mtime"] < cutoff_date:
            return True

        return False

    @staticmethod
    def _select_backups_for_deletion(
        backups_dir: Path, keep: int, days: int | None
    ) -> list[BackupInfo]:
        """Select backup files to delete based on age and count.

        Args:
            backups_dir: Directory containing backup files
            keep: Keep this many most recent backups per issue
            days: Delete backups older than this many days

        Returns:
            List of BackupInfo dicts for files to delete
        """
        backup_files = list(backups_dir.glob("*.backup.md"))
        if not backup_files:
            return []

        # Group backups by issue ID
        backups_by_issue = BackupCleanupService._group_backups_by_issue(backup_files)

        # Determine files to delete
        files_to_delete: list[BackupInfo] = []
        cutoff_date = datetime.now(UTC) - timedelta(days=days) if days else None

        for _issue_key, backups in backups_by_issue.items():
            backups.sort(key=lambda x: x["mtime"], reverse=True)

            for idx, backup in enumerate(backups):
                if BackupCleanupService._should_delete_backup(
                    idx, backup, keep, cutoff_date
                ):
                    files_to_delete.append(backup)

        return files_to_delete
