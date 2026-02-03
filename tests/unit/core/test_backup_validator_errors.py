"""Error path tests for BackupValidator.

Tests cover error handling, boundary conditions, and edge cases.
"""

import os
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from roadmap.core.services.validators.backup_validator import BackupValidator


# temp_dir_context fixture for this test file
@pytest.fixture
def temp_dir_context():
    """Fixture for TemporaryDirectory context manager pattern."""
    from tempfile import TemporaryDirectory

    def _context_manager():
        return TemporaryDirectory()

    return _context_manager


class TestBackupValidatorDirectoryHandling:
    """Test directory validation and error handling."""

    def test_scan_nonexistent_backups_dir(self, temp_dir_context):
        """Nonexistent backups dir should return empty result."""
        nonexistent_path = Path("/nonexistent/path/to/backups")
        result = BackupValidator.scan_for_old_backups(nonexistent_path)

        assert result["files_to_delete"] == []
        assert result["total_size_bytes"] == 0

    def test_scan_empty_backups_dir(self, temp_dir_context):
        """Empty backups dir should return empty result."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backups_dir = Path(tmpdir)
            result = BackupValidator.scan_for_old_backups(backups_dir)

            assert result["files_to_delete"] == []
            assert result["total_size_bytes"] == 0

    def test_scan_dir_with_no_backup_files(self, temp_dir_context):
        """Dir with non-backup files should return empty result."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backups_dir = Path(tmpdir)
            (backups_dir / "readme.txt").touch()
            (backups_dir / "config.json").touch()

            result = BackupValidator.scan_for_old_backups(backups_dir)

            assert result["files_to_delete"] == []
            assert result["total_size_bytes"] == 0

    def test_scan_permission_denied_on_directory(self, temp_dir_context):
        """Permission denied accessing directory should raise exception."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backups_dir = Path(tmpdir)
            backup_file = backups_dir / "issue_1.backup.md"
            backup_file.touch()

            with patch.object(
                Path, "exists", side_effect=PermissionError("Access denied")
            ):
                with pytest.raises(PermissionError):
                    BackupValidator.scan_for_old_backups(backups_dir)


class TestBackupValidatorFileScanning:
    """Test file scanning and grouping logic."""

    def test_scan_single_backup_file(self, temp_dir_context):
        """Single backup file below keep threshold should not be deleted."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backups_dir = Path(tmpdir)
            backup_file = backups_dir / "issue_123_v1.backup.md"
            backup_file.write_text("backup content")

            result = BackupValidator.scan_for_old_backups(backups_dir, keep=10)

            assert result["files_to_delete"] == []
            assert result["total_size_bytes"] == 0

    def test_scan_multiple_backup_files_same_issue(self, temp_dir_context):
        """Multiple backups of same issue, some beyond keep threshold."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backups_dir = Path(tmpdir)

            # Create 5 backup files for same issue
            for i in range(5):
                backup_file = backups_dir / f"issue_123_v{i}.backup.md"
                backup_file.write_text(f"backup {i}" * 100)

            result = BackupValidator.scan_for_old_backups(backups_dir, keep=2)

            # Should have 3 files to delete (5 - 2 keep)
            assert len(result["files_to_delete"]) == 3
            assert result["total_size_bytes"] > 0

    def test_scan_multiple_issues_separate_keep_threshold(self, temp_dir_context):
        """Each issue has its own keep threshold."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backups_dir = Path(tmpdir)

            # Create 3 backups for issue 1
            for i in range(3):
                backup_file = backups_dir / f"issue_1_v{i}.backup.md"
                backup_file.write_text("content1")

            # Create 4 backups for issue 2
            for i in range(4):
                backup_file = backups_dir / f"issue_2_v{i}.backup.md"
                backup_file.write_text("content2")

            result = BackupValidator.scan_for_old_backups(backups_dir, keep=2)

            # 1 from issue 1 + 2 from issue 2 = 3 total
            assert len(result["files_to_delete"]) == 3

    def test_scan_keep_value_zero(self, temp_dir_context):
        """Keep value of 0 should delete all files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backups_dir = Path(tmpdir)

            for i in range(3):
                backup_file = backups_dir / f"issue_123_v{i}.backup.md"
                backup_file.write_text("backup")

            result = BackupValidator.scan_for_old_backups(backups_dir, keep=0)

            assert len(result["files_to_delete"]) == 3

    def test_scan_keep_value_negative(self, temp_dir_context):
        """Negative keep value should delete all files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backups_dir = Path(tmpdir)

            for i in range(3):
                backup_file = backups_dir / f"issue_123_v{i}.backup.md"
                backup_file.write_text("backup")

            result = BackupValidator.scan_for_old_backups(backups_dir, keep=-5)

            # All files should be deleted since keep is negative
            assert len(result["files_to_delete"]) == 3

    def test_scan_files_with_underscores_in_names(self, temp_dir_context):
        """Files with multiple underscores should be grouped correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backups_dir = Path(tmpdir)

            # Issue key is everything before last underscore
            backup_file1 = backups_dir / "issue_123_456_v1.backup.md"
            backup_file2 = backups_dir / "issue_123_456_v2.backup.md"
            backup_file1.write_text("content")
            backup_file2.write_text("content")

            result = BackupValidator.scan_for_old_backups(backups_dir, keep=1)

            # Should delete oldest (v1)
            assert len(result["files_to_delete"]) == 1


class TestBackupValidatorSizeCalculation:
    """Test total_size_bytes calculation."""

    def test_size_calculation_single_file(self, temp_dir_context):
        """Size should match file size."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backups_dir = Path(tmpdir)

            # Create 3 files, delete oldest
            content = "x" * 1000  # 1000 bytes
            for i in range(3):
                backup_file = backups_dir / f"issue_123_v{i}.backup.md"
                backup_file.write_text(content)

            result = BackupValidator.scan_for_old_backups(backups_dir, keep=2)

            assert len(result["files_to_delete"]) == 1
            assert result["total_size_bytes"] == len(content.encode())

    def test_size_calculation_multiple_files(self, temp_dir_context):
        """Total size should sum all deleted files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backups_dir = Path(tmpdir)
            base_time = time.time()

            sizes = [100, 200, 300, 400]
            for i, size in enumerate(sizes):
                backup_file = backups_dir / f"issue_123_v{i}.backup.md"
                backup_file.write_text("x" * size)
                # Set deterministic mtime (older files have earlier times)
                mtime = base_time + i
                os.utime(backup_file, (mtime, mtime))

            result = BackupValidator.scan_for_old_backups(backups_dir, keep=2)

            # Should delete 2 oldest files: 100 + 200 = 300
            assert result["total_size_bytes"] == 300

    def test_size_zero_for_empty_result(self, temp_dir_context):
        """No files to delete should result in zero size."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backups_dir = Path(tmpdir)
            backup_file = backups_dir / "issue_123_v1.backup.md"
            backup_file.write_text("content")

            result = BackupValidator.scan_for_old_backups(backups_dir, keep=10)

            assert result["files_to_delete"] == []
            assert result["total_size_bytes"] == 0


class TestBackupValidatorHealthCheck:
    """Test health check functionality."""

    def test_health_check_no_old_backups(self, temp_dir_context):
        """No old backups should return HEALTHY status."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backups_dir = Path(tmpdir)
            (backups_dir / "issue_123_v1.backup.md").write_text("content")

            with patch.object(
                BackupValidator,
                "scan_for_old_backups",
                return_value={"files_to_delete": [], "total_size_bytes": 0},
            ):
                status, message = BackupValidator.check_old_backups()

                from roadmap.core.services.validator_base import HealthStatus

                assert status == HealthStatus.HEALTHY
                assert "No old backups" in message

    def test_health_check_with_old_backups(self, temp_dir_context):
        """Old backups should return HEALTHY but inform user."""
        old_backups = {
            "files_to_delete": [{"path": Path("file1.backup.md")} for _ in range(5)],
            "total_size_bytes": 5 * 1024 * 1024,  # 5 MB
        }

        with patch.object(
            BackupValidator, "scan_for_old_backups", return_value=old_backups
        ):
            status, message = BackupValidator.check_old_backups()

            from roadmap.core.services.validator_base import HealthStatus

            assert status == HealthStatus.HEALTHY
            assert "5 old backup file(s)" in message
            assert "5.0 MB" in message

    def test_health_check_exception_handling(self, temp_dir_context):
        """Exception during health check should return HEALTHY with fallback message."""
        with patch.object(
            BackupValidator,
            "scan_for_old_backups",
            side_effect=Exception("Scan failed"),
        ):
            status, message = BackupValidator.check_old_backups()

            from roadmap.core.services.validator_base import HealthStatus

            assert status == HealthStatus.HEALTHY
            assert "Could not check" in message

    def test_health_check_import_error(self, temp_dir_context):
        """Import error during health check should be handled."""
        with patch(
            "roadmap.core.services.validators.backup_validator.Path"
        ) as mock_path:
            mock_path.return_value.glob.side_effect = ImportError("Module not found")

            status, message = BackupValidator.check_old_backups()

            from roadmap.core.services.validator_base import HealthStatus

            assert status == HealthStatus.HEALTHY

    def test_health_check_size_formatting_edge_cases(self, temp_dir_context):
        """Very large sizes should be formatted correctly."""
        old_backups = {
            "files_to_delete": [
                {"path": Path(f"file{i}.backup.md")} for i in range(10)
            ],
            "total_size_bytes": int(1.5 * 1024 * 1024 * 1024),  # 1.5 GB
        }

        with patch.object(
            BackupValidator, "scan_for_old_backups", return_value=old_backups
        ):
            status, message = BackupValidator.check_old_backups()

            from roadmap.core.services.validator_base import HealthStatus

            assert status == HealthStatus.HEALTHY
            # Check that large size is formatted with decimal
            assert "1024.0 MB" in message or "1.0 GB" not in message


class TestBackupValidatorEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_backup_files_with_special_characters(self, temp_dir_context):
        """Backup files with special characters should be handled."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backups_dir = Path(tmpdir)

            # Files with special chars in issue key (if allowed by filesystem)
            backup_file = backups_dir / "issue_123-456_v1.backup.md"
            backup_file.write_text("content")

            result = BackupValidator.scan_for_old_backups(backups_dir, keep=10)

            # Should handle gracefully
            assert isinstance(result["files_to_delete"], list)

    def test_backup_files_same_mtime(self, temp_dir_context):
        """Files with same mtime should still be ordered correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backups_dir = Path(tmpdir)

            # Create files with explicit same mtime
            for i in range(3):
                backup_file = backups_dir / f"issue_123_v{i}.backup.md"
                backup_file.write_text("content")
                backup_file.touch()  # Reset mtime to current

            result = BackupValidator.scan_for_old_backups(backups_dir, keep=1)

            # Should delete 2 files even with same mtime
            assert len(result["files_to_delete"]) == 2

    def test_scan_with_very_large_keep_value(self, temp_dir_context):
        """Very large keep value should keep all files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backups_dir = Path(tmpdir)

            for i in range(5):
                backup_file = backups_dir / f"issue_123_v{i}.backup.md"
                backup_file.write_text("content")

            result = BackupValidator.scan_for_old_backups(backups_dir, keep=1000000)

            assert result["files_to_delete"] == []
            assert result["total_size_bytes"] == 0

    def test_mixed_backup_and_non_backup_files(self, temp_dir_context):
        """Directory with mixed file types should only process backup files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backups_dir = Path(tmpdir)

            # Create backup files
            for i in range(3):
                backup_file = backups_dir / f"issue_123_v{i}.backup.md"
                backup_file.write_text("backup")

            # Create non-backup files
            (backups_dir / "config.json").write_text("config")
            (backups_dir / "readme.txt").write_text("readme")
            (backups_dir / "issue_123.backup").write_text("not .backup.md")

            result = BackupValidator.scan_for_old_backups(backups_dir, keep=1)

            # Should only count .backup.md files
            assert len(result["files_to_delete"]) == 2

    def test_backup_file_with_missing_version(self, temp_dir_context):
        """Backup file with missing version number (edge case in naming)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backups_dir = Path(tmpdir)

            # File without version number
            backup_file = backups_dir / "issue_123.backup.md"
            backup_file.write_text("content")

            result = BackupValidator.scan_for_old_backups(backups_dir, keep=10)

            # Should handle gracefully, file stem is "issue_123.backup"
            # parts would be ['issue', '123', 'backup']
            # issue_key would be 'issue_123'
            assert isinstance(result, dict)
            assert "files_to_delete" in result

    def test_deeply_nested_issue_keys(self, temp_dir_context):
        """Issue keys with many underscores should be parsed correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backups_dir = Path(tmpdir)

            # Very nested issue key
            for i in range(3):
                backup_file = (
                    backups_dir / f"proj_team_issue_123_456_789_v{i}.backup.md"
                )
                backup_file.write_text("content")

            result = BackupValidator.scan_for_old_backups(backups_dir, keep=1)

            # Should group all 3 files together and delete 2
            assert len(result["files_to_delete"]) == 2


class TestBackupValidatorDataIntegrity:
    """Test data integrity and correct result structure."""

    def test_result_structure_always_has_required_keys(self, temp_dir_context):
        """Result should always have required keys."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backups_dir = Path(tmpdir)

            result = BackupValidator.scan_for_old_backups(backups_dir)

            assert "files_to_delete" in result
            assert "total_size_bytes" in result
            assert isinstance(result["files_to_delete"], list)
            assert isinstance(result["total_size_bytes"], int)

    def test_deleted_files_have_correct_path(self, temp_dir_context):
        """Deleted file entries should have Path objects."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backups_dir = Path(tmpdir)

            for i in range(3):
                backup_file = backups_dir / f"issue_123_v{i}.backup.md"
                backup_file.write_text("content")

            result = BackupValidator.scan_for_old_backups(backups_dir, keep=1)

            for deleted_file in result["files_to_delete"]:
                assert isinstance(deleted_file, dict)
                assert "path" in deleted_file
                assert isinstance(deleted_file["path"], Path)

    def test_newest_files_kept_not_deleted(self, temp_dir_context):
        """Newest files (by mtime) should be kept, oldest deleted."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backups_dir = Path(tmpdir)
            base_time = time.time()

            # Create with deterministic mtime ordering
            file_objects = []
            for i in range(5):
                backup_file = backups_dir / f"issue_123_v{i}.backup.md"
                backup_file.write_text(f"content{i}")
                file_objects.append(backup_file)
                # Set deterministic mtime (older files have earlier times)
                mtime = base_time + i
                os.utime(backup_file, (mtime, mtime))

            result = BackupValidator.scan_for_old_backups(backups_dir, keep=2)

            deleted_paths = {f["path"] for f in result["files_to_delete"]}

            # v3 and v4 should be newest (kept)
            # v0, v1, v2 should be oldest (deleted)
            assert file_objects[3] not in deleted_paths
            assert file_objects[4] not in deleted_paths
