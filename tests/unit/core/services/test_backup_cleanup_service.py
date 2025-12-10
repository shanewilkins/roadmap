"""Comprehensive unit tests for backup cleanup service.

Tests cover backup selection, grouping, deletion, and cleanup operations.
"""

from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch

from roadmap.core.services.backup_cleanup_service import (
    BackupCleanupResult,
    BackupCleanupService,
    BackupInfo,
)


class TestBackupInfo:
    """Test BackupInfo TypedDict."""

    def test_backup_info_creation(self):
        """Test creating BackupInfo."""
        now = datetime.now()
        backup: BackupInfo = {
            "path": Path("/tmp/test.backup.md"),
            "mtime": now,
            "size": 1024,
        }
        assert backup["path"] == Path("/tmp/test.backup.md")
        assert backup["mtime"] == now
        assert backup["size"] == 1024


class TestBackupCleanupResult:
    """Test BackupCleanupResult class."""

    def test_initialization(self):
        """Test result initialization."""
        result = BackupCleanupResult()
        assert result.deleted_count == 0
        assert result.failed_count == 0
        assert result.total_freed_bytes == 0
        assert result.files_deleted == []
        assert result.files_failed == []

    def test_add_deleted(self):
        """Test recording deleted file."""
        result = BackupCleanupResult()
        path = Path("/tmp/test1.backup.md")

        result.add_deleted(path, 1024)

        assert result.deleted_count == 1
        assert result.total_freed_bytes == 1024
        assert result.files_deleted == [path]

    def test_add_deleted_multiple(self):
        """Test recording multiple deleted files."""
        result = BackupCleanupResult()
        path1 = Path("/tmp/test1.backup.md")
        path2 = Path("/tmp/test2.backup.md")

        result.add_deleted(path1, 1024)
        result.add_deleted(path2, 2048)

        assert result.deleted_count == 2
        assert result.total_freed_bytes == 3072
        assert result.files_deleted == [path1, path2]

    def test_add_failed(self):
        """Test recording failed file."""
        result = BackupCleanupResult()
        path = Path("/tmp/test.backup.md")
        error = "Permission denied"

        result.add_failed(path, error)

        assert result.failed_count == 1
        assert result.files_failed == [(path, error)]

    def test_add_failed_multiple(self):
        """Test recording multiple failed files."""
        result = BackupCleanupResult()
        path1 = Path("/tmp/test1.backup.md")
        path2 = Path("/tmp/test2.backup.md")

        result.add_failed(path1, "Permission denied")
        result.add_failed(path2, "File not found")

        assert result.failed_count == 2
        assert len(result.files_failed) == 2

    def test_freed_mb_zero(self):
        """Test freed_mb calculation with zero bytes."""
        result = BackupCleanupResult()
        assert result.freed_mb == 0.0

    def test_freed_mb_calculation(self):
        """Test freed_mb calculation."""
        result = BackupCleanupResult()
        result.add_deleted(Path("/tmp/test1.backup.md"), 1024 * 1024)  # 1 MB
        result.add_deleted(Path("/tmp/test2.backup.md"), 2 * 1024 * 1024)  # 2 MB

        assert result.freed_mb == 3.0

    def test_freed_mb_partial(self):
        """Test freed_mb calculation with fractional MB."""
        result = BackupCleanupResult()
        result.add_deleted(Path("/tmp/test.backup.md"), 512 * 1024)  # 0.5 MB

        assert abs(result.freed_mb - 0.5) < 0.001


class TestGroupBackupsByIssue:
    """Test _group_backups_by_issue static method."""

    @patch("pathlib.Path.stat")
    def test_group_single_issue(self, mock_stat):
        """Test grouping backups for single issue."""
        mock_stat.return_value = Mock(st_mtime=datetime.now().timestamp(), st_size=1024)

        backup_files = [
            Path("backups/issue-123_v1.backup.md"),
            Path("backups/issue-123_v2.backup.md"),
            Path("backups/issue-123_v3.backup.md"),
        ]

        result = BackupCleanupService._group_backups_by_issue(backup_files)

        assert len(result) == 1
        assert "issue-123" in result
        assert len(result["issue-123"]) == 3

    @patch("pathlib.Path.stat")
    def test_group_multiple_issues(self, mock_stat):
        """Test grouping backups for multiple issues."""
        mock_stat.return_value = Mock(st_mtime=datetime.now().timestamp(), st_size=1024)

        backup_files = [
            Path("backups/issue-123_v1.backup.md"),
            Path("backups/issue-456_v1.backup.md"),
            Path("backups/issue-123_v2.backup.md"),
            Path("backups/issue-789_v1.backup.md"),
        ]

        result = BackupCleanupService._group_backups_by_issue(backup_files)

        assert len(result) == 3
        assert len(result["issue-123"]) == 2
        assert len(result["issue-456"]) == 1
        assert len(result["issue-789"]) == 1

    @patch("pathlib.Path.stat")
    def test_group_empty_list(self, mock_stat):
        """Test grouping empty backup list."""
        result = BackupCleanupService._group_backups_by_issue([])
        assert result == {}

    @patch("pathlib.Path.stat")
    def test_group_preserves_metadata(self, mock_stat):
        """Test that grouping preserves file metadata."""
        mtime = datetime.now().timestamp()
        size = 2048
        mock_stat.return_value = Mock(st_mtime=mtime, st_size=size)

        backup_files = [Path("backups/issue-123_v1.backup.md")]

        result = BackupCleanupService._group_backups_by_issue(backup_files)
        backup_info = result["issue-123"][0]

        assert backup_info["size"] == size
        assert backup_info["path"] == Path("backups/issue-123_v1.backup.md")


class TestShouldDeleteBackup:
    """Test _should_delete_backup static method."""

    def test_delete_beyond_keep_count(self):
        """Test deletion when beyond keep count."""
        now = datetime.now()
        backup: BackupInfo = {
            "path": Path("test.backup.md"),
            "mtime": now,
            "size": 1024,
        }

        # Index 10 with keep=5 should be deleted
        assert BackupCleanupService._should_delete_backup(10, backup, 5, None) is True

    def test_keep_within_count(self):
        """Test preservation when within keep count."""
        now = datetime.now()
        backup: BackupInfo = {
            "path": Path("test.backup.md"),
            "mtime": now,
            "size": 1024,
        }

        # Index 3 with keep=5 should be kept
        assert BackupCleanupService._should_delete_backup(3, backup, 5, None) is False

    def test_delete_older_than_cutoff(self):
        """Test deletion when older than cutoff date."""
        old_date = datetime.now() - timedelta(days=30)
        backup: BackupInfo = {
            "path": Path("test.backup.md"),
            "mtime": old_date,
            "size": 1024,
        }
        cutoff = datetime.now() - timedelta(days=7)

        # Backup older than cutoff should be deleted
        assert (
            BackupCleanupService._should_delete_backup(0, backup, 100, cutoff) is True
        )

    def test_keep_newer_than_cutoff(self):
        """Test preservation when newer than cutoff date."""
        new_date = datetime.now() - timedelta(days=2)
        backup: BackupInfo = {
            "path": Path("test.backup.md"),
            "mtime": new_date,
            "size": 1024,
        }
        cutoff = datetime.now() - timedelta(days=7)

        # Backup newer than cutoff should be kept
        assert (
            BackupCleanupService._should_delete_backup(0, backup, 100, cutoff) is False
        )

    def test_both_conditions_met(self):
        """Test deletion when both conditions are met."""
        old_date = datetime.now() - timedelta(days=30)
        backup: BackupInfo = {
            "path": Path("test.backup.md"),
            "mtime": old_date,
            "size": 1024,
        }
        cutoff = datetime.now() - timedelta(days=7)

        # Beyond keep count AND older than cutoff
        assert BackupCleanupService._should_delete_backup(10, backup, 5, cutoff) is True


class TestSelectBackupsForDeletion:
    """Test _select_backups_for_deletion static method."""

    @patch("pathlib.Path.glob")
    @patch("pathlib.Path.stat")
    def test_select_by_keep_count(self, mock_stat, mock_glob):
        """Test selection based on keep count."""
        now = datetime.now()
        mock_stat.return_value = Mock(st_mtime=now.timestamp(), st_size=1024)

        backup_files = [
            Path("backups/issue-123_v1.backup.md"),
            Path("backups/issue-123_v2.backup.md"),
            Path("backups/issue-123_v3.backup.md"),
        ]
        mock_glob.return_value = backup_files

        backups_dir = Path("backups")
        result = BackupCleanupService._select_backups_for_deletion(
            backups_dir, keep=2, days=None
        )

        # Should select 1 for deletion (oldest of 3, keeping newest 2)
        assert len(result) == 1

    @patch("pathlib.Path.glob")
    def test_select_no_backups(self, mock_glob):
        """Test when no backup files exist."""
        mock_glob.return_value = []

        backups_dir = Path("backups")
        result = BackupCleanupService._select_backups_for_deletion(
            backups_dir, keep=10, days=None
        )

        assert result == []

    @patch("pathlib.Path.glob")
    @patch("pathlib.Path.stat")
    def test_select_by_age(self, mock_stat, mock_glob):
        """Test selection based on age."""
        now = datetime.now()
        old_date = now - timedelta(days=30)

        backup_files = [
            Path("backups/issue-123_v1.backup.md"),
            Path("backups/issue-123_v2.backup.md"),
        ]

        # Create proper mocks that return different stat values based on path
        old_stat = Mock(st_mtime=old_date.timestamp(), st_size=1024)
        new_stat = Mock(st_mtime=now.timestamp(), st_size=1024)

        # Side effect based on the instance being called on
        def stat_side_effect():
            return old_stat  # Return old date by default

        mock_stat.side_effect = [old_stat, new_stat]
        mock_glob.return_value = backup_files

        backups_dir = Path("backups")
        result = BackupCleanupService._select_backups_for_deletion(
            backups_dir, keep=100, days=7
        )

        # Old backup should be selected for deletion
        assert len(result) >= 1


class TestCleanupBackups:
    """Test cleanup_backups main method."""

    @patch("roadmap.core.services.backup_cleanup_service.logger")
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

    @patch("roadmap.core.services.backup_cleanup_service.logger")
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

    @patch("roadmap.core.services.backup_cleanup_service.logger")
    @patch.object(BackupCleanupService, "_select_backups_for_deletion")
    @patch("pathlib.Path.exists")
    def test_cleanup_dry_run(self, mock_exists, mock_select, mock_logger):
        """Test cleanup in dry run mode."""
        mock_exists.return_value = True
        backups = [
            {
                "path": Path("/tmp/test1.backup.md"),
                "mtime": datetime.now(),
                "size": 1024,
            },
            {
                "path": Path("/tmp/test2.backup.md"),
                "mtime": datetime.now(),
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

    @patch("roadmap.core.services.backup_cleanup_service.logger")
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
                "mtime": datetime.now(),
                "size": 1024,
            },
        ]
        mock_select.return_value = backups

        service = BackupCleanupService()
        roadmap_dir = Path("/tmp/roadmap")
        result = service.cleanup_backups(roadmap_dir, dry_run=False)

        assert result.deleted_count == 1
        mock_unlink.assert_called_once()

    @patch("roadmap.core.services.backup_cleanup_service.logger")
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
                "mtime": datetime.now(),
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

    @patch("roadmap.core.services.backup_cleanup_service.logger")
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

    @patch("roadmap.core.services.backup_cleanup_service.logger")
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

    @patch("roadmap.core.services.backup_cleanup_service.logger")
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

        now = datetime.now()
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

    @patch("roadmap.core.services.backup_cleanup_service.logger")
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

        now = datetime.now()
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
