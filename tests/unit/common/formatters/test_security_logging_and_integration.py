"""Test security logging, event handling, and integration scenarios.

Tests security event logging, logging configuration, export size validation,
and comprehensive security workflows.
"""

import logging
import os
import tempfile
import time
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from roadmap.common.security import (
    SecurityError,
    configure_security_logging,
    create_secure_directory,
    create_secure_file,
    create_secure_temp_file,
    log_security_event,
    sanitize_filename,
    security_logger,
    validate_export_size,
    validate_path,
)
from tests.unit.domain.test_data_factory_generation import TestDataFactory

pytestmark = pytest.mark.unit


@pytest.fixture
def temp_dir():
    """Provide a temporary directory for test operations."""
    with tempfile.TemporaryDirectory() as td:
        yield Path(td)


class TestLogSecurityEvent:
    """Test log_security_event function."""

    @pytest.mark.parametrize(
        "event_type,has_details",
        [
            ("test_event", True),
            ("simple_event", False),
            ("complex_event", True),
        ],
    )
    def test_log_security_event_variants(self, event_type, has_details):
        """Test logging with and without event details."""
        mock_handler = TestDataFactory.create_mock_core(is_initialized=True)
        mock_handler.stream = TestDataFactory.create_mock_core(is_initialized=True)
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
        mock_handler = TestDataFactory.create_mock_core(is_initialized=True)
        mock_handler.stream = TestDataFactory.create_mock_core(is_initialized=True)
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
            patch.object(
                security_logger, "info", side_effect=Exception("Logging failed")
            ),
        ):
            log_security_event("failing_event")
        # If we reach here, exception was handled
        assert True

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

    @pytest.mark.parametrize(
        "level_str,expected_level",
        [
            ("DEBUG", logging.DEBUG),
            ("INFO", logging.INFO),
            ("WARNING", logging.WARNING),
            ("ERROR", logging.ERROR),
        ],
    )
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
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="test message",
            args=(),
            exc_info=None,
        )
        formatted = formatter.format(log_record)
        assert "test message" in formatted


class TestValidateExportSize:
    """Test validate_export_size function."""

    @pytest.mark.parametrize(
        "file_size_mb,limit_mb,should_fail",
        [
            (0.5, 1, False),
            (1.0, 1, False),
            (2.0, 1, True),
            (10.0, 5, True),
            (0.1, 1, False),
        ],
    )
    def test_validate_export_size_various_limits(
        self, temp_dir, file_size_mb, limit_mb, should_fail
    ):
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
        # Should not raise, nonexistent files are OK
        assert True

    def test_validate_export_size_empty_file(self, temp_dir):
        """Test validation of empty file."""
        empty_file = temp_dir / "empty.txt"
        empty_file.touch()
        validate_export_size(empty_file, max_size_mb=1)
        # Validation succeeded for empty file
        assert True

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

            with pytest.raises(SecurityError):
                validate_path("../dangerous.txt", base_dir)

            from roadmap.common.security import secure_file_permissions

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
            original_dir = os.getcwd()
            try:
                os.chdir(temp_dir)
                validate_path("safe.txt", base_dir)
            finally:
                os.chdir(original_dir)

            sanitize_filename("file<name>.txt")
            temp_file = create_secure_temp_file()
            from roadmap.common.security import secure_file_permissions

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
