"""Test security path validation and filename sanitization.

Tests path traversal attack prevention, filename sanitization,
and secure temporary file creation.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from roadmap.common.security import (
    PathValidationError,
    SecurityError,
    create_secure_temp_file,
    sanitize_filename,
    validate_path,
)

pytestmark = pytest.mark.unit


@pytest.fixture
def temp_dir(temp_dir_context):
    """Provide a temporary directory for test operations."""
    with tempfile.TemporaryDirectory() as td:
        yield Path(td)


@pytest.fixture
def temp_base_dir(temp_dir_context):
    """Provide a temporary base directory with safe working context."""
    with tempfile.TemporaryDirectory() as td:
        original_dir = os.getcwd()
        try:
            os.chdir(td)
            yield Path(td)
        finally:
            os.chdir(original_dir)


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
        caught = False
        try:
            raise PathValidationError("Test")
        except SecurityError:
            caught = True  # Should catch as SecurityError
        except Exception:
            pytest.fail("PathValidationError should inherit from SecurityError")
        assert caught, "PathValidationError should have been caught as SecurityError"


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

    @pytest.mark.parametrize(
        "bad_path",
        [
            "../../../etc/passwd",
            "subdir/../../../etc/passwd",
            "subdir/../../parent_file.txt",
            Path("../outside.txt"),
        ],
    )
    def test_validate_path_directory_traversal_blocked(self, temp_dir, bad_path):
        """Test that directory traversal attempts are blocked."""
        base_dir = temp_dir

        with pytest.raises(
            PathValidationError,
            match="outside allowed directory|directory traversal",
        ):
            validate_path(bad_path, base_dir)

    def test_validate_path_absolute_not_allowed(self, temp_dir_context):
        """Test that absolute paths are rejected when not allowed."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_dir = Path(temp_dir)
            abs_path = Path("/etc/passwd")

            with pytest.raises(PathValidationError, match="Absolute paths not allowed"):
                validate_path(abs_path, base_dir, allow_absolute=False)

    def test_validate_path_absolute_allowed(self, temp_dir_context):
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

    @pytest.mark.parametrize(
        "dangerous_path",
        [
            "subdir/../file.txt",  # Contains .. - should be blocked by traversal check
            "./file.txt",  # Contains . - may be blocked
            "~/file.txt",  # Contains ~ - may be blocked
        ],
    )
    def test_validate_path_dangerous_components(self, temp_dir, dangerous_path):
        """Test that paths with dangerous components are blocked."""
        base_dir = temp_dir

        with pytest.raises(
            PathValidationError,
            match="dangerous components|outside allowed directory",
        ):
            validate_path(dangerous_path, base_dir)

    def test_validate_path_string_input(self, temp_dir_context):
        """Test path validation with string input."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_dir = Path(temp_dir)

            # Create the actual file for testing
            test_file = base_dir / "safe_file.txt"
            test_file.write_text("content")

            # Change to temp directory to ensure relative paths work correctly
            original_dir = os.getcwd()
            try:
                os.chdir(temp_dir)
                result = validate_path("safe_file.txt", str(base_dir))
                assert result.name == "safe_file.txt"
            finally:
                os.chdir(original_dir)

    @patch("roadmap.common.security.path_validation.log_security_event")
    def test_validate_path_logging_scenarios(self, mock_log, temp_dir_context):
        """Test path validation logging for success and failure scenarios."""
        # Test failure logging
        with pytest.raises(PathValidationError):
            validate_path("../bad_path.txt", "/tmp")

        # Check that failure was logged
        failure_logged = any(
            call[0][0] == "path_validation_failed" for call in mock_log.call_args_list
        )
        assert failure_logged

        # Test success logging
        with tempfile.TemporaryDirectory() as temp_dir:
            base_dir = Path(temp_dir)
            test_path = "safe_path.txt"

            # Create the file to make path valid
            test_file = base_dir / test_path
            test_file.write_text("content")

            # Change to temp directory to ensure relative paths work correctly
            original_dir = os.getcwd()
            try:
                os.chdir(temp_dir)
                mock_log.reset_mock()
                validate_path(test_path, base_dir)

                # Check that success was logged
                mock_log.assert_called()
                success_logged = any(
                    call[0][0] == "path_validated" for call in mock_log.call_args_list
                )
                assert success_logged
            finally:
                os.chdir(original_dir)


class TestSanitizeFilename:
    """Test sanitize_filename function."""

    @pytest.mark.parametrize(
        "input_name,expected",
        [
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
        ],
    )
    def test_sanitize_filename_variants(self, input_name, expected):
        """Test sanitization of various filename formats."""
        result = sanitize_filename(input_name)
        assert result == expected

    @pytest.mark.parametrize(
        "dangerous_input",
        [
            "../file.txt",
            "file/../other.txt",
            "..file.txt",
            "file..txt",
        ],
    )
    def test_sanitize_filename_directory_traversal(self, dangerous_input):
        """Test sanitization of directory traversal attempts."""
        result = sanitize_filename(dangerous_input)
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

    @pytest.mark.parametrize(
        "dangerous_chars_input,expected",
        [
            (".", "safe_filename"),
            ("..", "_"),
            ("...", "_"),
        ],
    )
    def test_sanitize_filename_only_dangerous(self, dangerous_chars_input, expected):
        """Test filename with only dangerous characters."""
        result = sanitize_filename(dangerous_chars_input)
        assert result == expected

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
