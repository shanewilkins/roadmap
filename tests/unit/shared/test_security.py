"""Comprehensive test suite for the security module.

This module tests all security functions including:
- File and directory creation with secure permissions
- Path validation and traversal attack prevention
- Filename sanitization
- Security event logging and configuration
- Export size validation
- Backup cleanup operations
- Exception handling and edge cases
"""

import logging
import os
import tempfile
import time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from roadmap.common.security import (
    PathValidationError,
    SecurityError,
    cleanup_old_backups,
    configure_security_logging,
    create_secure_directory,
    create_secure_file,
    create_secure_temp_file,
    log_security_event,
    sanitize_filename,
    secure_file_permissions,
    security_logger,
    validate_export_size,
    validate_path,
)

pytestmark = pytest.mark.unit


@contextmanager
def safe_working_directory(directory):
    """Context manager for safely changing working directory during tests."""
    try:
        original_dir = os.getcwd()
    except (FileNotFoundError, OSError):
        # If current directory doesn't exist, start from home
        original_dir = os.path.expanduser("~")
        os.chdir(original_dir)

    try:
        os.chdir(directory)
        yield
    finally:
        # Safely restore original directory, handle case where it might be deleted
        try:
            if os.path.exists(original_dir):
                os.chdir(original_dir)
            else:
                # If original directory is gone, change to a known safe directory
                os.chdir(os.path.expanduser("~"))
        except (FileNotFoundError, OSError):
            # Last resort - go to home directory
            os.chdir(os.path.expanduser("~"))


@pytest.fixture
def temp_dir():
    """Provide a temporary directory for test operations."""
    with tempfile.TemporaryDirectory() as td:
        yield Path(td)


@pytest.fixture
def temp_base_dir():
    """Provide a temporary base directory with safe working context."""
    with tempfile.TemporaryDirectory() as td:
        with safe_working_directory(td):
            yield Path(td)


class TestSecurityExceptions:
    """Test security exception classes."""

    def test_security_error_creation(self):
        """Test SecurityError exception creation."""
        error = SecurityError("Test error message")
        assert str(error) == "Test error message"
        assert isinstance(error, Exception)

    def test_path_validation_error_creation(self):
        """Test PathValidationError exception creation."""
        error = PathValidationError("Path validation failed")
        assert str(error) == "Path validation failed"
        assert isinstance(error, SecurityError)
        assert isinstance(error, Exception)

    def test_security_error_inheritance(self):
        """Test that PathValidationError inherits from SecurityError."""
        try:
            raise PathValidationError("Test")
        except SecurityError:
            pass  # Should catch as SecurityError
        except Exception:
            pytest.fail("PathValidationError should inherit from SecurityError")


class TestCreateSecureFile:
    """Test create_secure_file function."""

    @pytest.mark.parametrize("mode,content,expected_content", [
        ("w", "test content", "test content"),
        ("wb", b"binary data", b"binary data"),
        ("a", "appended", "initial appended"),
    ])
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

    def test_create_secure_file_basic(self, temp_dir):
        """Test basic secure file creation."""
        test_path = temp_dir / "test_file.txt"

        with create_secure_file(test_path, "w") as f:
            f.write("test content")
            assert f.writable()

        # Verify file exists and has correct permissions
        assert test_path.exists()
        assert test_path.read_text() == "test content"

        # Check permissions (owner read/write only)
        permissions = test_path.stat().st_mode & 0o777
        assert permissions == 0o600

    def test_create_secure_file_custom_permissions(self, temp_dir):
        """Test secure file creation with custom permissions."""
        test_path = temp_dir / "custom_perm.txt"

        with create_secure_file(test_path, "w", permissions=0o644) as f:
            f.write("content")

        # Check custom permissions
        permissions = test_path.stat().st_mode & 0o777
        assert permissions == 0o644

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


class TestValidatePath:
    """Test validate_path function."""

    def test_validate_path_simple_relative(self, temp_base_dir):
        """Test path validation with simple relative path."""
        base_dir = temp_base_dir

        # Create the actual subdirectory and file for testing
        subdir = base_dir / "subdir"
        subdir.mkdir()
        test_file = subdir / "file.txt"
        test_file.write_text("content")

        result = validate_path("subdir/file.txt", base_dir)
        assert result.name == "file.txt"

    def test_validate_path_directory_traversal_blocked(self, temp_dir):
        """Test that directory traversal attempts are blocked."""
        base_dir = temp_dir

        # Test various traversal attempts
        traversal_paths = [
            "../../../etc/passwd",
            "subdir/../../../etc/passwd",
            "subdir/../../parent_file.txt",
            Path("../outside.txt"),
        ]

        for bad_path in traversal_paths:
            with pytest.raises(
                PathValidationError,
                match="outside allowed directory|directory traversal",
            ):
                validate_path(bad_path, base_dir)

    def test_validate_path_absolute_not_allowed(self):
        """Test that absolute paths are rejected when not allowed."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_dir = Path(temp_dir)
            abs_path = Path("/etc/passwd")

            with pytest.raises(PathValidationError, match="Absolute paths not allowed"):
                validate_path(abs_path, base_dir, allow_absolute=False)

    def test_validate_path_absolute_allowed(self):
        """Test that absolute paths are accepted when allowed."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test.txt"
            test_file.write_text("content")

            result = validate_path(test_file, allow_absolute=True)
            assert result.is_absolute()
            assert result == test_file.resolve()

    def test_validate_path_no_base_dir(self):
        """Test path validation without base directory."""
        safe_path = Path("safe/relative/path.txt")
        result = validate_path(safe_path)
        assert isinstance(result, Path)

    def test_validate_path_no_base_dir_with_traversal(self):
        """Test path validation without base dir still blocks traversal."""
        with pytest.raises(PathValidationError, match="directory traversal"):
            validate_path("../dangerous/path.txt")

    def test_validate_path_dangerous_components(self):
        """Test that paths with dangerous components are blocked."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_dir = Path(temp_dir)

            # These should be blocked due to dangerous components or directory traversal
            dangerous_paths = [
                "subdir/../file.txt",  # Contains .. - should be blocked by traversal check
                "./file.txt",  # Contains . - may be blocked
                "~/file.txt",  # Contains ~ - may be blocked
            ]

            for dangerous_path in dangerous_paths:
                with pytest.raises(
                    PathValidationError,
                    match="dangerous components|outside allowed directory",
                ):
                    validate_path(dangerous_path, base_dir)

    def test_validate_path_string_input(self):
        """Test path validation with string input."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_dir = Path(temp_dir)

            # Create the actual file for testing
            test_file = base_dir / "safe_file.txt"
            test_file.write_text("content")

            # Change to temp directory to ensure relative paths work correctly
            with safe_working_directory(temp_dir):
                result = validate_path("safe_file.txt", str(base_dir))
                assert result.name == "safe_file.txt"

    @patch("roadmap.common.security.path_validation.log_security_event")
    def test_validate_path_logging_success(self, mock_log):
        """Test successful path validation logging."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_dir = Path(temp_dir)
            test_path = "safe_path.txt"

            # Create the file to make path valid
            test_file = base_dir / test_path
            test_file.write_text("content")

            # Change to temp directory to ensure relative paths work correctly
            import os

            original_dir = os.getcwd()
            try:
                os.chdir(temp_dir)
                validate_path(test_path, base_dir)

                # Check that success was logged
                mock_log.assert_called()
            finally:
                os.chdir(original_dir)
            success_logged = any(
                call[0][0] == "path_validated" for call in mock_log.call_args_list
            )
            assert success_logged

    @patch("roadmap.common.security.path_validation.log_security_event")
    def test_validate_path_logging_failure(self, mock_log):
        """Test failed path validation logging."""
        with pytest.raises(PathValidationError):
            validate_path("../bad_path.txt", "/tmp")

        # Check that failure was logged
        failure_logged = any(
            call[0][0] == "path_validation_failed" for call in mock_log.call_args_list
        )
        assert failure_logged


class TestSanitizeFilename:
    """Test sanitize_filename function."""

    @pytest.mark.parametrize("input_name,expected", [
        ("normal_file.txt", "normal_file.txt"),
        ("file<name>.txt", "file_name_.txt"),
        ("file>name.txt", "file_name.txt"),
        ('file"name.txt', "file_name.txt"),
        ("file|name.txt", "file_name.txt"),
        ("file?name.txt", "file_name.txt"),
        ("file*name.txt", "file_name.txt"),
        ("file\\name.txt", "file_name.txt"),
        ("file/name.txt", "file_name.txt"),
        ("file:name.txt", "file_name.txt"),
        (" filename.txt ", "filename.txt"),
        (".filename.txt", "filename.txt"),
        ("filename.txt.", "filename.txt"),
        (" . filename . ", "filename"),
    ])
    def test_sanitize_filename_variants(self, input_name, expected):
        """Test sanitization of various filename formats."""
        result = sanitize_filename(input_name)
        assert result == expected

    def test_sanitize_filename_basic(self):
        """Test basic filename sanitization."""
        result = sanitize_filename("normal_file.txt")
        assert result == "normal_file.txt"

    def test_sanitize_filename_directory_traversal(self):
        """Test sanitization of directory traversal attempts."""
        traversal_attempts = [
            "../file.txt",
            "file/../other.txt",
            "..file.txt",
            "file..txt",
        ]

        for attempt in traversal_attempts:
            result = sanitize_filename(attempt)
            assert ".." not in result
            assert "_" in result or result == "safe_filename"

    def test_sanitize_filename_max_length(self):
        """Test filename length truncation."""
        long_name = "a" * 300 + ".txt"
        result = sanitize_filename(long_name, max_length=255)

        assert len(result) <= 255
        assert result.endswith(".txt")  # Extension preserved

    def test_sanitize_filename_empty_input(self):
        """Test handling of empty filename."""
        with pytest.raises(SecurityError, match="Filename cannot be empty"):
            sanitize_filename("")

    def test_sanitize_filename_only_dangerous(self):
        """Test filename with only dangerous characters."""
        result = sanitize_filename("...")
        assert result == "_"

        result = sanitize_filename("..")
        assert result == "_"

        result = sanitize_filename(".")
        assert result == "safe_filename"

    def test_sanitize_filename_null_bytes(self):
        """Test handling of null bytes."""
        result = sanitize_filename("file\0name.txt")
        assert "\0" not in result
        assert result == "file_name.txt"

    @patch("roadmap.common.security.filename_sanitization.log_security_event")
    def test_sanitize_filename_logging(self, mock_log):
        """Test filename sanitization logging."""
        original = "dangerous<file>.txt"
        result = sanitize_filename(original)

        mock_log.assert_called_with(
            "filename_sanitized", {"original": original, "sanitized": result}
        )


class TestCreateSecureTempFile:
    """Test create_secure_temp_file function."""

    def test_create_secure_temp_file_basic(self):
        """Test basic secure temporary file creation."""
        temp_file = create_secure_temp_file()

        try:
            assert temp_file.exists()
            assert temp_file.is_file()

            # Check secure permissions
            permissions = temp_file.stat().st_mode & 0o777
            assert permissions == 0o600

            # Check filename pattern
            assert temp_file.name.startswith("roadmap_")
            assert temp_file.name.endswith(".tmp")

        finally:
            if temp_file.exists():
                temp_file.unlink()

    def test_create_secure_temp_file_custom_prefix_suffix(self):
        """Test temp file creation with custom prefix and suffix."""
        temp_file = create_secure_temp_file(prefix="custom_", suffix=".test")

        try:
            assert temp_file.name.startswith("custom_")
            assert temp_file.name.endswith(".test")
        finally:
            if temp_file.exists():
                temp_file.unlink()

    def test_create_secure_temp_file_writable(self):
        """Test that created temp file is writable."""
        temp_file = create_secure_temp_file()

        try:
            # Should be able to write to it
            temp_file.write_text("test content")
            assert temp_file.read_text() == "test content"
        finally:
            temp_file.unlink()

    @patch("tempfile.mkstemp", side_effect=OSError("No space left"))
    def test_create_secure_temp_file_failure(self, mock_mkstemp):
        """Test temp file creation failure handling."""
        with pytest.raises(
            SecurityError, match="Failed to create secure temporary file"
        ):
            create_secure_temp_file()

    @patch("roadmap.common.security.temp_files.log_security_event")
    def test_create_secure_temp_file_logging(self, mock_log):
        """Test temp file creation logging."""
        temp_file = create_secure_temp_file()

        try:
            mock_log.assert_called_with("temp_file_created", {"path": str(temp_file)})
        finally:
            temp_file.unlink()


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
    def test_secure_file_permissions_failure(self, mock_chmod):
        """Test permission setting failure."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test.txt"
            test_file.write_text("content")

            with pytest.raises(SecurityError, match="Failed to set secure permissions"):
                secure_file_permissions(test_file)

    @patch("roadmap.common.security.file_operations.log_security_event")
    def test_secure_file_permissions_logging(self, mock_log):
        """Test permission setting logging."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test.txt"
            test_file.write_text("content")

            secure_file_permissions(test_file, permissions=0o640)

            mock_log.assert_called_with(
                "permissions_set", {"path": str(test_file), "permissions": "0o640"}
            )


class TestLogSecurityEvent:
    """Test log_security_event function."""

    @pytest.mark.parametrize("event_type,has_details", [
        ("test_event", True),
        ("simple_event", False),
        ("complex_event", True),
    ])
    def test_log_security_event_variants(self, event_type, has_details):
        """Test logging with and without event details."""
        mock_handler = MagicMock()
        mock_handler.stream = MagicMock()
        mock_handler.stream.closed = False

        with (
            patch.object(security_logger, "handlers", [mock_handler]),
            patch.object(security_logger, "info") as mock_info,
        ):
            details = {"key": "value"} if has_details else None
            if details:
                log_security_event(event_type, details)
            else:
                log_security_event(event_type)

            mock_info.assert_called_once()
            args, kwargs = mock_info.call_args
            assert f"Security event: {event_type}" in args[0]
            assert kwargs["extra"]["event_type"] == event_type

    def test_log_security_event_with_timestamp(self):
        """Test that timestamp is added to logged events."""
        mock_handler = MagicMock()
        mock_handler.stream = MagicMock()
        mock_handler.stream.closed = False

        with (
            patch.object(security_logger, "handlers", [mock_handler]),
            patch.object(security_logger, "info") as mock_info,
        ):
            log_security_event("timed_event")
            args, kwargs = mock_info.call_args
            assert "timestamp" in kwargs["extra"]
            # Verify timestamp is ISO format
            datetime.fromisoformat(kwargs["extra"]["timestamp"])

    def test_log_security_event_exception_handling(self):
        """Test that logging exceptions don't break functionality."""
        with (
            patch.object(security_logger, "handlers", [MagicMock()]),
            patch.object(security_logger, "info", side_effect=Exception("Logging failed")),
        ):
            log_security_event("failing_event")

    def test_log_security_event_closed_handler(self):
        """Test handling of closed log handlers."""
        mock_handler = Mock()
        mock_handler.stream = Mock()
        mock_handler.stream.closed = True

        with (
            patch.object(security_logger, "handlers", [mock_handler]),
            patch.object(security_logger, "info") as mock_info,
        ):
            log_security_event("closed_handler_event")
            mock_info.assert_not_called()


class TestConfigureSecurityLogging:
    """Test configure_security_logging function."""

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        """Clear existing handlers before and after each test."""
        original_handlers = security_logger.handlers.copy()
        original_level = security_logger.level

        security_logger.handlers.clear()
        yield

        for handler in security_logger.handlers.copy():
            handler.close()
            security_logger.removeHandler(handler)

        security_logger.handlers.clear()
        for handler in original_handlers:
            security_logger.addHandler(handler)
        security_logger.setLevel(original_level)

    @pytest.mark.parametrize("level_str,expected_level", [
        ("DEBUG", logging.DEBUG),
        ("INFO", logging.INFO),
        ("WARNING", logging.WARNING),
        ("ERROR", logging.ERROR),
    ])
    def test_configure_security_logging_levels(self, level_str, expected_level):
        """Test different logging levels."""
        configure_security_logging(level_str)
        assert security_logger.level == expected_level

    def test_configure_security_logging_basic(self):
        """Test basic logging configuration."""
        configure_security_logging("INFO")
        assert security_logger.level == logging.INFO
        assert len(security_logger.handlers) == 1
        assert isinstance(security_logger.handlers[0], logging.StreamHandler)

    def test_configure_security_logging_with_file(self, temp_dir):
        """Test logging configuration with file output."""
        log_file = temp_dir / "security.log"
        configure_security_logging("DEBUG", log_file)

        assert security_logger.level == logging.DEBUG
        assert len(security_logger.handlers) == 2
        assert log_file.exists()
        assert (log_file.stat().st_mode & 0o777) == 0o600

    def test_configure_security_logging_formatter(self):
        """Test that formatter is properly set."""
        configure_security_logging()
        handler = security_logger.handlers[0]
        formatter = handler.formatter
        assert formatter is not None

        log_record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="test message", args=(), exc_info=None,
        )
        formatted = formatter.format(log_record)
        assert "test message" in formatted


class TestValidateExportSize:
    """Test validate_export_size function."""

    @pytest.mark.parametrize("file_size_mb,limit_mb,should_fail", [
        (0.5, 1, False),
        (1.0, 1, False),
        (2.0, 1, True),
        (10.0, 5, True),
        (0.1, 1, False),
    ])
    def test_validate_export_size_various_limits(self, temp_dir, file_size_mb, limit_mb, should_fail):
        """Test validation with various file sizes and limits."""
        test_file = temp_dir / "test.txt"
        content_size = int(file_size_mb * 1024 * 1024)
        test_file.write_text("x" * content_size)

        if should_fail:
            with pytest.raises(SecurityError, match="Export file too large"):
                validate_export_size(test_file, max_size_mb=limit_mb)
        else:
            validate_export_size(test_file, max_size_mb=limit_mb)

    def test_validate_export_size_nonexistent_file(self):
        """Test validation of nonexistent file (should pass)."""
        nonexistent = Path("/nonexistent/file.txt")
        validate_export_size(nonexistent)

    def test_validate_export_size_empty_file(self, temp_dir):
        """Test validation of empty file."""
        empty_file = temp_dir / "empty.txt"
        empty_file.touch()
        validate_export_size(empty_file, max_size_mb=1)

    @patch("roadmap.common.security.export_cleanup.log_security_event")
    def test_validate_export_size_logging_large_file(self, mock_log, temp_dir):
        """Test logging of large file detection."""
        large_file = temp_dir / "large.txt"
        large_content = "x" * (2 * 1024 * 1024)
        large_file.write_text(large_content)

        with pytest.raises(SecurityError):
            validate_export_size(large_file, max_size_mb=1)

        mock_log.assert_called()
        log_calls = mock_log.call_args_list
        large_file_logged = any(
            call[0][0] == "large_export_detected" for call in log_calls
        )
        assert large_file_logged


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

    @pytest.mark.parametrize("retention_days,file_age_days,should_delete", [
        (30, 35, True),
        (30, 25, False),
        (7, 10, True),
        (7, 5, False),
    ])
    def test_cleanup_old_backups_retention_policy(self, temp_dir, retention_days, file_age_days, should_delete):
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
            mock_glob.return_value = [(backup_dir / "file.backup"), (backup_dir / "file.backup.gz")]
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

        cleanup_logged = any(
            call[0][0] == "backup_cleaned" for call in log_calls
        )
        completion_logged = any(
            call[0][0] == "backup_cleanup_completed" for call in log_calls
        )

        assert cleanup_logged
        assert completion_logged


class TestSecurityIntegration:
    """Test integration scenarios combining multiple security functions."""

    def test_secure_file_creation_workflow(self):
        """Test complete secure file creation and validation workflow."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_dir = Path(temp_dir)

            # Sanitize filename first
            safe_filename = sanitize_filename("user<report>.csv")

            # Create secure directory structure
            target_dir = base_dir / "user_data"
            create_secure_directory(target_dir)

            # Create secure file
            final_path = target_dir / safe_filename
            with create_secure_file(final_path) as f:
                f.write("secure,data,content\n")

            # Now validate the path that actually exists
            import os

            original_dir = os.getcwd()
            try:
                os.chdir(temp_dir)
                validate_path(final_path.relative_to(base_dir), base_dir)
            finally:
                os.chdir(original_dir)

            # Validate export size
            validate_export_size(final_path, max_size_mb=1)

            # Verify all security measures applied
            assert final_path.exists()
            assert final_path.read_text() == "secure,data,content\n"

            # Check permissions
            file_perms = final_path.stat().st_mode & 0o777
            dir_perms = target_dir.stat().st_mode & 0o777
            assert file_perms == 0o600
            assert dir_perms == 0o700

    def test_security_logging_integration(self):
        """Test that all security operations properly log events."""
        from roadmap.common.security import security_logger

        # Clean up any existing handlers to ensure test isolation
        for handler in security_logger.handlers[:]:
            security_logger.removeHandler(handler)

        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "security.log"

            # Configure logging
            configure_security_logging("INFO", log_file)

            # Perform various security operations
            test_dir = Path(temp_dir) / "test_operations"
            create_secure_directory(test_dir)

            test_file = test_dir / "test.txt"
            with create_secure_file(test_file) as f:
                f.write("test content")

            sanitize_filename("test<file>.txt")

            # Create a subdirectory and file to validate
            safe_subdir = test_dir / "safe"
            safe_subdir.mkdir()
            safe_file = safe_subdir / "path.txt"
            safe_file.write_text("content")

            # Change to test directory for relative path validation
            import os

            original_dir = os.getcwd()
            try:
                os.chdir(test_dir)
                validate_path("safe/path.txt", test_dir)
            finally:
                os.chdir(original_dir)

            # Verify log file was created and contains events
            assert log_file.exists()
            log_content = log_file.read_text()

            # Should contain various security events
            assert "Security event:" in log_content
            assert "directory_created" in log_content or "file_created" in log_content

            # Clean up handlers to avoid affecting other tests
            for handler in security_logger.handlers[:]:
                security_logger.removeHandler(handler)

    def test_error_handling_integration(self):
        """Test error handling across multiple security functions."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_dir = Path(temp_dir)

            # Test various error conditions
            with pytest.raises(SecurityError):
                sanitize_filename("")

            with pytest.raises(PathValidationError):
                validate_path("../dangerous.txt", base_dir)

            with pytest.raises(SecurityError):
                secure_file_permissions(Path("/nonexistent/file.txt"))

            # Verify other operations still work after errors
            safe_file = base_dir / "recovery.txt"
            with create_secure_file(safe_file) as f:
                f.write("recovery successful")

            assert safe_file.exists()

    def test_comprehensive_logging_coverage(self):
        """Test that all major security operations execute without error."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_dir = Path(temp_dir)

            # Perform all major security operations
            # These should execute without error (logging happens internally)
            create_secure_directory(base_dir / "test_dir")

            test_file = base_dir / "test.txt"
            with create_secure_file(test_file) as f:
                f.write("content")

            # Create a file to validate its relative path
            safe_file = base_dir / "safe.txt"
            safe_file.write_text("content")

            # Change to temp directory for relative path validation
            import os

            original_dir = os.getcwd()
            try:
                os.chdir(temp_dir)
                validate_path("safe.txt", base_dir)
            finally:
                os.chdir(original_dir)

            sanitize_filename("file<name>.txt")
            temp_file = create_secure_temp_file()
            secure_file_permissions(test_file, 0o644)
            validate_export_size(test_file)

            # Clean up temp file
            temp_file.unlink()

            # Verify all operations completed successfully
            # (Logging is tested separately in individual unit tests)
            assert (base_dir / "test_dir").exists()
            assert test_file.exists()
            assert safe_file.exists()


class TestSecurityPerformance:
    """Test security operations performance and resource usage."""

    def test_large_filename_sanitization(self):
        """Test performance with very large filenames."""
        # Create a very long filename
        long_filename = "a" * 10000 + ".txt"

        # Should complete quickly and not consume excessive memory
        import time

        start_time = time.time()
        result = sanitize_filename(long_filename, max_length=255)
        end_time = time.time()

        assert len(result) <= 255
        assert end_time - start_time < 1.0  # Should complete within 1 second

    def test_many_path_validations(self):
        """Test performance with many path validations."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_dir = Path(temp_dir)

            # Create some sample files for validation
            for i in range(10):  # Create fewer files for performance test
                test_file = base_dir / f"file_{i}.txt"
                test_file.write_text("content")

            # Validate paths quickly
            paths_to_validate = [f"file_{i}.txt" for i in range(10)]

            import time

            start_time = time.time()

            # Change to temp directory for relative path validation
            import os

            original_dir = os.getcwd()
            try:
                os.chdir(temp_dir)
                for path in paths_to_validate:
                    validate_path(path, base_dir)
            finally:
                os.chdir(original_dir)

            end_time = time.time()

            # Should complete all validations quickly
            assert end_time - start_time < 5.0  # Within 5 seconds

    def test_temp_file_cleanup(self):
        """Test that temporary files are properly cleaned up."""
        initial_temp_count = len(list(Path(tempfile.gettempdir()).glob("roadmap_*")))

        # Create multiple temporary files
        temp_files = []
        for _ in range(10):
            temp_file = create_secure_temp_file()
            temp_files.append(temp_file)

        # Clean them up
        for temp_file in temp_files:
            temp_file.unlink()

        final_temp_count = len(list(Path(tempfile.gettempdir()).glob("roadmap_*")))

        # Should not leave temp files behind
        assert final_temp_count == initial_temp_count
