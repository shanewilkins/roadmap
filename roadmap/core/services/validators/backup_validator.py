"""Validator for old backup files."""

from pathlib import Path

from roadmap.common.logging import get_logger

from . import BackupScanResult

logger = get_logger(__name__)


class BackupValidator:
    """Validator for old backup files."""

    @staticmethod
    def scan_for_old_backups(backups_dir: Path, keep: int = 10) -> BackupScanResult:
        """Scan for old backup files that could be deleted.

        Returns a dict with:
        - 'files_to_delete': List of backup files that exceed the keep threshold
        - 'total_size_bytes': Total size of files that could be deleted (int)
        """
        result: BackupScanResult = {"files_to_delete": [], "total_size_bytes": 0}

        if not backups_dir.exists():
            return result

        backup_files = list(backups_dir.glob("*.backup.md"))
        if not backup_files:
            return result

        # Group backups by issue ID
        backups_by_issue = {}
        for backup_file in backup_files:
            parts = backup_file.stem.split("_")
            issue_key = "_".join(parts[:-1])

            if issue_key not in backups_by_issue:
                backups_by_issue[issue_key] = []

            stat = backup_file.stat()
            backups_by_issue[issue_key].append(
                {
                    "path": backup_file,
                    "mtime": stat.st_mtime,
                    "size": stat.st_size,
                }
            )

        # Find files that exceed keep threshold
        for _issue_key, backups in backups_by_issue.items():
            backups.sort(key=lambda x: x["mtime"], reverse=True)

            for idx, backup in enumerate(backups):
                if idx >= keep:
                    result["files_to_delete"].append(backup)
                    result["total_size_bytes"] += backup["size"]

        return result

    @staticmethod
    def check_old_backups() -> tuple[str, str]:
        """Check for old backup files.

        Returns:
            Tuple of (status, message) describing the health check result
        """
        try:
            from roadmap.core.services.base_validator import HealthStatus

            backups_dir = Path(".roadmap/backups")
            old_backups = BackupValidator.scan_for_old_backups(backups_dir)

            if not old_backups["files_to_delete"]:
                logger.debug("health_check_old_backups", status="none")
                return HealthStatus.HEALTHY, "No old backups to clean up"

            count = len(old_backups["files_to_delete"])
            size_mb = old_backups["total_size_bytes"] / (1024 * 1024)
            message = (
                f"ℹ️ {count} old backup file(s) could be deleted "
                f"(~{size_mb:.1f} MB saved): Run 'roadmap cleanup' to remove"
            )
            logger.info("health_check_old_backups", count=count, size_mb=size_mb)
            return HealthStatus.HEALTHY, message

        except Exception as e:
            logger.debug("health_check_old_backups_failed", error=str(e))
            return HealthStatus.HEALTHY, "Could not check for old backups"
