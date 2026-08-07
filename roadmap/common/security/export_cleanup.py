"""Export validation and backup cleanup utilities."""

import time
from pathlib import Path

from .exceptions import SecurityError
from .logging import log_security_event


def validate_export_size(file_path: Path, max_size_mb: int = 100) -> None:
    """Validate that an export file isn't too large.

    Args:
        file_path: Path to the export file
        max_size_mb: Maximum allowed size in MB

    Raises:
        SecurityError: If file is too large
    """
    if not file_path.exists():
        return

    file_size_mb = file_path.stat().st_size / (1024 * 1024)

    if file_size_mb > max_size_mb:
        log_security_event(
            "large_export_detected",
            {
                "path": str(file_path),
                "size_mb": file_size_mb,
                "max_size_mb": max_size_mb,
            },
        )
        raise SecurityError(
            f"Export file too large: {file_size_mb:.1f}MB > {max_size_mb}MB"
        )


def cleanup_old_backups(backup_dir: Path, retention_days: int = 30) -> int:
    """Clean up old backup files for security.

    Args:
        backup_dir: Directory containing backup files
        retention_days: Number of days to retain backups

    Returns:
        Number of files cleaned up
    """
    if not backup_dir.exists():
        return 0

    cutoff_time = time.time() - (retention_days * 24 * 60 * 60)
    cleaned_count = 0

    try:
        for backup_file in backup_dir.glob("*.backup*"):
            if backup_file.stat().st_mtime < cutoff_time:
                backup_file.unlink()
                cleaned_count += 1

                log_security_event(
                    "backup_cleaned",
                    {
                        "path": str(backup_file),
                        "age_days": (time.time() - backup_file.stat().st_mtime)
                        / (24 * 60 * 60),
                    },
                )

        if cleaned_count > 0:
            log_security_event(
                "backup_cleanup_completed",
                {"files_cleaned": cleaned_count, "retention_days": retention_days},
            )

    except Exception as e:
        log_security_event("backup_cleanup_failed", {"error": str(e)})

    return cleaned_count
