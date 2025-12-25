"""Fixer for old backup files."""

from datetime import datetime, timedelta
from pathlib import Path

from roadmap.adapters.cli.health.fixer import FixResult, FixSafety, HealthFixer


class OldBackupsFixer(HealthFixer):
    """Removes old backup files to free up storage.

    Safety: SAFE (automatically applies)

    Removes backup files older than 90 days.
    """

    BACKUP_THRESHOLD_DAYS = 90

    @property
    def fix_type(self) -> str:
        """Return fixer type identifier."""
        return "old_backups"

    @property
    def safety_level(self) -> FixSafety:
        """Return safety level - SAFE because backups are not primary data."""
        return FixSafety.SAFE

    @property
    def description(self) -> str:
        """Return fixer description."""
        return f"Delete backup files older than {self.BACKUP_THRESHOLD_DAYS} days"

    def scan(self) -> dict:
        """Scan for old backup files.

        Returns:
            Dict with found, count, message, details
        """
        old_backups = self._find_old_backups()

        return {
            "found": len(old_backups) > 0,
            "count": len(old_backups),
            "message": f"Found {len(old_backups)} old backup file(s) to clean up",
            "details": [
                {"path": str(p), "age_days": self._get_age_days(p)} for p in old_backups
            ],
        }

    def dry_run(self) -> FixResult:
        """Preview which backups would be deleted.

        Returns:
            FixResult with dry_run=True
        """
        old_backups = self._find_old_backups()

        return FixResult(
            fix_type=self.fix_type,
            success=True,
            dry_run=True,
            message=f"Would delete {len(old_backups)} old backup file(s)",
            affected_items=[str(p) for p in old_backups],
            items_count=len(old_backups),
            changes_made=0,
        )

    def apply(self, force: bool = False) -> FixResult:
        """Delete old backup files.

        Args:
            force: Ignored (SAFE fixers apply automatically)

        Returns:
            FixResult with results of deletion
        """
        old_backups = self._find_old_backups()
        deleted_count = 0
        failed_items = []

        for backup_path in old_backups:
            try:
                backup_path.unlink()
                deleted_count += 1
            except Exception:
                failed_items.append(str(backup_path))

        success = len(failed_items) == 0

        return FixResult(
            fix_type=self.fix_type,
            success=success,
            dry_run=False,
            message=f"Deleted {deleted_count}/{len(old_backups)} old backup file(s)",
            affected_items=[str(p) for p in old_backups],
            items_count=len(old_backups),
            changes_made=deleted_count,
        )

    def _find_old_backups(self) -> list[Path]:
        """Find backup files older than threshold.

        Returns:
            List of Path objects for old backups
        """
        old_backups = []
        backup_dir = Path(".roadmap/backups")

        if not backup_dir.exists():
            return old_backups

        now = datetime.now()
        threshold = now - timedelta(days=self.BACKUP_THRESHOLD_DAYS)

        for backup_file in backup_dir.glob("*.db"):
            mtime = datetime.fromtimestamp(backup_file.stat().st_mtime)
            if mtime < threshold:
                old_backups.append(backup_file)

        return sorted(old_backups)

    def _get_age_days(self, path: Path) -> int:
        """Get age of file in days.

        Args:
            path: Path to file

        Returns:
            Age in days
        """
        mtime = datetime.fromtimestamp(path.stat().st_mtime)
        age = datetime.now() - mtime
        return age.days
