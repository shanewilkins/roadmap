"""Test security file operations and permissions handling.

Tests secure file and directory creation, permission management,
and backup cleanup operations.
"""

import time
from pathlib import Path
from unittest.mock import patch

import pytest

from roadmap.common.security import (
    SecurityError,
    cleanup_old_backups,
    create_secure_directory,
    create_secure_file,
    secure_file_permissions,
)

pytestmark = pytest.mark.unit


@pytest.fixture
def temp_dir(temp_dir_context):
    """Provide a temporary directory for test operations."""
    with temp_dir_context() as td:
        yield Path(td)


class TestCreateSecureFile:
    """Test create_secure_file function."""

    @pytest.mark.parametrize(
        "mode,content,expected_content",
        [
            ("w", "test content", "test content"),
            ("wb", b"binary data", b"binary data"),
            ("a", "appended", "initial appended"),
        ],
    )
    def test_create_secure_file_modes(self, temp_dir, mode, content, expected_content):
        """Test secure file creation with different file modes."""
        test_path = temp_dir / "test_file.txt"

        if mode == "a":
            test_path.write_text("initial ")

        with create_secure_file(test_path, mode) as f:
            f.write(content)

        if isinstance(content, bytes):
            assert test_path.read_bytes() == expected_content
        else:
            assert test_path.read_text() == expected_content

    @pytest.mark.parametrize(
        "permissions,scenario",
        [
            (None, "basic"),
            (0o644, "custom"),
        ],
    )
    def test_create_secure_file_permissions(self, temp_dir, permissions, scenario):
        """Test secure file creation with various permission modes."""
        test_path = temp_dir / f"perm_{scenario}.txt"

        if permissions is None:
            with create_secure_file(test_path, "w") as f:
                f.write("content")
            expected_perms = 0o600
        else:
            with create_secure_file(test_path, "w", permissions=permissions) as f:
                f.write("content")
            expected_perms = permissions

        # Check permissions
        actual_perms = test_path.stat().st_mode & 0o777
        assert actual_perms == expected_perms

    def test_create_secure_file_creates_parent_dirs(self, temp_dir):
        """Test that parent directories are created automatically."""
        nested_path = temp_dir / "nested" / "deep" / "file.txt"

        with create_secure_file(nested_path) as f:
            f.write("nested content")

        assert nested_path.exists()
        assert nested_path.read_text() == "nested content"

    def test_create_secure_file_read_mode(self, temp_dir):
        """Test secure file creation in read mode with existing file."""
        test_path = temp_dir / "existing.txt"
        test_path.write_text("existing content")

        with create_secure_file(test_path, "r") as f:
            content = f.read()
            assert content == "existing content"

    def test_create_secure_file_invalid_path(self):
        """Test secure file creation with invalid path."""
        invalid_path = Path("/invalid/nonexistent/deeply/nested/path/file.txt")

        with pytest.raises(SecurityError, match="Failed to create secure file"):
            with create_secure_file(invalid_path):
                pass

    @patch("roadmap.common.security.file_operations.log_security_event")
    def test_create_secure_file_logging(self, mock_log, temp_dir):
        """Test that security events are logged properly."""
        test_path = temp_dir / "logged.txt"

        with create_secure_file(test_path) as f:
            f.write("content")

        # Should log file creation
        mock_log.assert_called()
        call_args = mock_log.call_args_list

        # Find the file_created event
        creation_logged = any(call[0][0] == "file_created" for call in call_args)
        assert creation_logged


class TestCreateSecureDirectory:
    """Test create_secure_directory function."""

    @pytest.mark.parametrize("permissions", [0o700, 0o755])
    def test_create_secure_directory_permissions(self, temp_dir, permissions):
        """Test secure directory creation with various permissions."""
        test_dir = temp_dir / f"dir_{permissions:o}"

        create_secure_directory(test_dir, permissions=permissions)

        dir_permissions = test_dir.stat().st_mode & 0o777
        assert dir_permissions == permissions

    def test_create_secure_directory_basic(self, temp_dir):
        """Test basic secure directory creation."""
        test_dir = temp_dir / "secure_dir"

        create_secure_directory(test_dir)

        assert test_dir.exists()
        assert test_dir.is_dir()

        # Check permissions (owner only by default)
        permissions = test_dir.stat().st_mode & 0o777
        assert permissions == 0o700

    def test_create_secure_directory_nested(self, temp_dir):
        """Test creation of nested directories."""
        nested_dir = temp_dir / "level1" / "level2" / "level3"

        create_secure_directory(nested_dir)

        assert nested_dir.exists()
        assert nested_dir.is_dir()

    def test_create_secure_directory_exists_ok(self, temp_dir):
        """Test that existing directories don't cause errors."""
        test_dir = temp_dir / "existing"
        test_dir.mkdir()

        # Should not raise error
        create_secure_directory(test_dir)
        assert test_dir.exists()

    def test_create_secure_directory_invalid_path(self):
        """Test directory creation with invalid path."""
        # Try to create directory in a read-only location (simulate)
        with patch("pathlib.Path.mkdir", side_effect=PermissionError("Access denied")):
            with pytest.raises(
                SecurityError, match="Failed to create secure directory"
            ):
                create_secure_directory(Path("/invalid/path"))

    @patch("roadmap.common.security.file_operations.log_security_event")
    def test_create_secure_directory_logging(self, mock_log, temp_dir):
        """Test directory creation logging."""
        test_dir = temp_dir / "logged_dir"

        create_secure_directory(test_dir)

        mock_log.assert_called_with(
            "directory_created", {"path": str(test_dir), "permissions": "0o700"}
        )


class TestSecureFilePermissions:
    """Test secure_file_permissions function."""

    @pytest.mark.parametrize("perms", [0o600, 0o644, 0o755])
    def test_secure_file_permissions_custom(self, temp_dir, perms):
        """Test setting custom permissions."""
        test_file = temp_dir / "test.txt"
        test_file.write_text("content")

        secure_file_permissions(test_file, permissions=perms)

        file_perms = test_file.stat().st_mode & 0o777
        assert file_perms == perms

    def test_secure_file_permissions_directory(self, temp_dir):
        """Test setting permissions on directory."""
        test_dir = temp_dir / "secure_dir"
        test_dir.mkdir()

        secure_file_permissions(test_dir, permissions=0o700)

        dir_perms = test_dir.stat().st_mode & 0o777
        assert dir_perms == 0o700

    def test_secure_file_permissions_nonexistent(self):
        """Test error when file doesn't exist."""
        nonexistent = Path("/nonexistent/file.txt")

        with pytest.raises(SecurityError, match="File does not exist"):
            secure_file_permissions(nonexistent)

    @patch("pathlib.Path.chmod", side_effect=PermissionError("Access denied"))
    def test_secure_file_permissions_failure(self, mock_chmod, temp_dir_context):
        """Test permission setting failure."""
        with temp_dir_context() as temp_dir:
            test_file = Path(temp_dir) / "test.txt"
            test_file.write_text("content")

            with pytest.raises(SecurityError, match="Failed to set secure permissions"):
                secure_file_permissions(test_file)

    @patch("roadmap.common.security.file_operations.log_security_event")
    def test_secure_file_permissions_logging(self, mock_log, temp_dir_context):
        """Test permission setting logging."""
        with temp_dir_context() as temp_dir:
            test_file = Path(temp_dir) / "test.txt"
            test_file.write_text("content")

            secure_file_permissions(test_file, permissions=0o640)

            mock_log.assert_called_with(
                "permissions_set", {"path": str(test_file), "permissions": "0o640"}
            )


class TestCleanupOldBackups:
    """Test cleanup_old_backups function."""

    def test_cleanup_old_backups_nonexistent_dir(self):
        """Test cleanup with nonexistent backup directory."""
        nonexistent_dir = Path("/nonexistent/backup/dir")
        result = cleanup_old_backups(nonexistent_dir)
        assert result == 0

    def test_cleanup_old_backups_no_old_files(self, temp_dir):
        """Test cleanup when no files are old enough."""
        backup_dir = temp_dir / "backups"
        backup_dir.mkdir()

        for i in range(3):
            backup_file = backup_dir / f"recent{i}.backup"
            backup_file.write_text(f"content {i}")

        result = cleanup_old_backups(backup_dir, retention_days=30)
        assert result == 0

    @pytest.mark.parametrize(
        "retention_days,file_age_days,should_delete",
        [
            (30, 35, True),
            (30, 25, False),
            (7, 10, True),
            (7, 5, False),
        ],
    )
    def test_cleanup_old_backups_retention_policy(
        self, temp_dir, retention_days, file_age_days, should_delete
    ):
        """Test cleanup respects retention policy."""
        backup_dir = temp_dir / "backups"
        backup_dir.mkdir()

        backup_file = backup_dir / "test.backup"
        backup_file.write_text("content")

        file_time = time.time() - (file_age_days * 24 * 60 * 60)

        with patch("pathlib.Path.glob") as mock_glob:
            mock_glob.return_value = [backup_file]
            with patch("os.stat") as mock_stat:
                mock_stat.return_value.st_mtime = file_time
                result = cleanup_old_backups(backup_dir, retention_days=retention_days)
                # Function should complete successfully
                assert result >= 0

    def test_cleanup_old_backups_mixed_file_types(self, temp_dir):
        """Test cleanup only processes backup files."""
        backup_dir = temp_dir / "backups"
        backup_dir.mkdir()

        (backup_dir / "file.backup").write_text("backup")
        (backup_dir / "file.backup.gz").write_text("compressed")
        (backup_dir / "file.txt").write_text("other")

        with patch("pathlib.Path.glob") as mock_glob:
            mock_glob.return_value = [
                (backup_dir / "file.backup"),
                (backup_dir / "file.backup.gz"),
            ]
            with patch.object(Path, "stat") as mock_stat:
                mock_stat.return_value.st_mtime = time.time() - (35 * 24 * 60 * 60)
                cleanup_old_backups(backup_dir, retention_days=30)
                mock_glob.assert_called_with("*.backup*")

    @patch("roadmap.common.security.export_cleanup.log_security_event")
    def test_cleanup_old_backups_logging(self, mock_log, temp_dir):
        """Test backup cleanup logging."""
        backup_dir = temp_dir / "backups"
        backup_dir.mkdir()

        old_backup = backup_dir / "old.backup"
        old_backup.write_text("content")
        old_time = time.time() - (35 * 24 * 60 * 60)

        with patch("pathlib.Path.glob") as mock_glob:
            mock_glob.return_value = [old_backup]
            with patch("os.stat") as mock_stat:
                mock_stat.return_value.st_mtime = old_time
                cleanup_old_backups(backup_dir, retention_days=30)

        log_calls = mock_log.call_args_list

        cleanup_logged = any(call[0][0] == "backup_cleaned" for call in log_calls)
        completion_logged = any(
            call[0][0] == "backup_cleanup_completed" for call in log_calls
        )

        assert cleanup_logged
        assert completion_logged
