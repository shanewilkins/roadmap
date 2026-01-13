"""Comprehensive unit tests for backup cleanup service.

Tests cover backup selection, grouping, deletion, and cleanup operations.
"""

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import Mock, patch

from roadmap.core.services.health.backup_cleanup_service import (
    BackupCleanupService,
)


class TestCleanupBackups:
    """Test cleanup_backups main method."""

    @patch("roadmap.core.services.health.backup_cleanup_service.logger")
    @patch("pathlib.Path.exists")
    def test_cleanup_no_backups_dir(self, mock_exists, mock_logger):
        """Test cleanup when backups directory doesn't exist."""
        mock_exists.return_value = False

        service = BackupCleanupService()
        roadmap_dir = Path("/tmp/roadmap")
        result = service.cleanup_backups(roadmap_dir)

        assert result.deleted_count == 0
        assert result.failed_count == 0
        mock_logger.info.assert_called()

    @patch("roadmap.core.services.health.backup_cleanup_service.logger")
    @patch.object(BackupCleanupService, "_select_backups_for_deletion")
    @patch("pathlib.Path.exists")
    def test_cleanup_no_files_to_delete(self, mock_exists, mock_select, mock_logger):
        """Test cleanup when no files selected for deletion."""
        mock_exists.return_value = True
        mock_select.return_value = []

        service = BackupCleanupService()
        roadmap_dir = Path("/tmp/roadmap")
        result = service.cleanup_backups(roadmap_dir)

        assert result.deleted_count == 0
        mock_logger.info.assert_called()

    @patch("roadmap.core.services.health.backup_cleanup_service.logger")
    @patch.object(BackupCleanupService, "_select_backups_for_deletion")
    @patch("pathlib.Path.exists")
    def test_cleanup_dry_run(self, mock_exists, mock_select, mock_logger):
        """Test cleanup in dry run mode."""
        mock_exists.return_value = True
        backups = [
            {
                "path": Path("/tmp/test1.backup.md"),
                "mtime": datetime.now(UTC),
                "size": 1024,
            },
            {
                "path": Path("/tmp/test2.backup.md"),
                "mtime": datetime.now(UTC),
                "size": 2048,
            },
        ]
        mock_select.return_value = backups

        service = BackupCleanupService()
        roadmap_dir = Path("/tmp/roadmap")
        result = service.cleanup_backups(roadmap_dir, dry_run=True)

        assert result.deleted_count == 2
        assert result.total_freed_bytes == 3072
        mock_logger.info.assert_called()

    @patch("roadmap.core.services.health.backup_cleanup_service.logger")
    @patch("pathlib.Path.unlink")
    @patch.object(BackupCleanupService, "_select_backups_for_deletion")
    @patch("pathlib.Path.exists")
    def test_cleanup_actual_deletion(
        self, mock_exists, mock_select, mock_unlink, mock_logger
    ):
        """Test actual backup deletion."""
        mock_exists.return_value = True
        backups = [
            {
                "path": Path("/tmp/test1.backup.md"),
                "mtime": datetime.now(UTC),
                "size": 1024,
            },
        ]
        mock_select.return_value = backups

        service = BackupCleanupService()
        roadmap_dir = Path("/tmp/roadmap")
        result = service.cleanup_backups(roadmap_dir, dry_run=False)

        assert result.deleted_count == 1
        mock_unlink.assert_called_once()

    @patch("roadmap.core.services.health.backup_cleanup_service.logger")
    @patch("pathlib.Path.unlink")
    @patch.object(BackupCleanupService, "_select_backups_for_deletion")
    @patch("pathlib.Path.exists")
    def test_cleanup_deletion_failure(
        self, mock_exists, mock_select, mock_unlink, mock_logger
    ):
        """Test handling of deletion failure."""
        mock_exists.return_value = True
        backups = [
            {
                "path": Path("/tmp/test.backup.md"),
                "mtime": datetime.now(UTC),
                "size": 1024,
            },
        ]
        mock_select.return_value = backups
        mock_unlink.side_effect = PermissionError("Permission denied")

        service = BackupCleanupService()
        roadmap_dir = Path("/tmp/roadmap")
        result = service.cleanup_backups(roadmap_dir, dry_run=False)

        assert result.deleted_count == 0
        assert result.failed_count == 1
        mock_logger.warning.assert_called()

    @patch("roadmap.core.services.health.backup_cleanup_service.logger")
    @patch("pathlib.Path.unlink")
    @patch.object(BackupCleanupService, "_select_backups_for_deletion")
    @patch("pathlib.Path.exists")
    def test_cleanup_keep_parameter(
        self, mock_exists, mock_select, mock_unlink, mock_logger
    ):
        """Test cleanup with custom keep parameter."""
        mock_exists.return_value = True
        mock_select.return_value = []

        service = BackupCleanupService()
        roadmap_dir = Path("/tmp/roadmap")
        service.cleanup_backups(roadmap_dir, keep=20)

        mock_select.assert_called_once_with(roadmap_dir / "backups", 20, None)

    @patch("roadmap.core.services.health.backup_cleanup_service.logger")
    @patch("pathlib.Path.unlink")
    @patch.object(BackupCleanupService, "_select_backups_for_deletion")
    @patch("pathlib.Path.exists")
    def test_cleanup_days_parameter(
        self, mock_exists, mock_select, mock_unlink, mock_logger
    ):
        """Test cleanup with custom days parameter."""
        mock_exists.return_value = True
        mock_select.return_value = []

        service = BackupCleanupService()
        roadmap_dir = Path("/tmp/roadmap")
        service.cleanup_backups(roadmap_dir, days=14)

        mock_select.assert_called_once_with(roadmap_dir / "backups", 10, 14)


class TestBackupCleanupIntegration:
    """Integration tests for backup cleanup."""

    @patch("roadmap.core.services.health.backup_cleanup_service.logger")
    @patch("pathlib.Path.unlink")
    @patch("pathlib.Path.stat")
    @patch("pathlib.Path.glob")
    @patch("pathlib.Path.exists")
    def test_full_cleanup_workflow(
        self,
        mock_exists,
        mock_glob,
        mock_stat,
        mock_unlink,
        mock_logger,
    ):
        """Test complete cleanup workflow."""
        mock_exists.return_value = True

        now = datetime.now(UTC)
        backup_files = [
            Path("backups/issue-123_v1.backup.md"),
            Path("backups/issue-123_v2.backup.md"),
            Path("backups/issue-123_v3.backup.md"),
        ]
        mock_glob.return_value = backup_files
        mock_stat.return_value = Mock(st_mtime=now.timestamp(), st_size=1024)

        service = BackupCleanupService()
        roadmap_dir = Path("/tmp/roadmap")
        result = service.cleanup_backups(roadmap_dir, keep=1)

        # Should delete 2 backups (keeping only 1)
        assert result.deleted_count == 2

    @patch("roadmap.core.services.health.backup_cleanup_service.logger")
    @patch("pathlib.Path.unlink")
    @patch.object(BackupCleanupService, "_select_backups_for_deletion")
    @patch("pathlib.Path.exists")
    def test_mixed_success_failure(
        self,
        mock_exists,
        mock_select,
        mock_unlink,
        mock_logger,
    ):
        """Test cleanup with mixed success and failure."""
        mock_exists.return_value = True

        now = datetime.now(UTC)
        backups = [
            {
                "path": Path("/tmp/test1.backup.md"),
                "mtime": now,
                "size": 1024,
            },
            {
                "path": Path("/tmp/test2.backup.md"),
                "mtime": now,
                "size": 2048,
            },
        ]
        mock_select.return_value = backups

        # First deletion succeeds, second fails
        mock_unlink.side_effect = [None, PermissionError("Denied")]

        service = BackupCleanupService()
        roadmap_dir = Path("/tmp/roadmap")
        result = service.cleanup_backups(roadmap_dir, keep=1)

        assert result.deleted_count == 1
        assert result.failed_count == 1
        assert result.total_freed_bytes == 1024
