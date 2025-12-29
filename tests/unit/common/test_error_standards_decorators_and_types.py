"""Tests for error handling standards and decorators."""

from pathlib import Path

import pytest

from roadmap.common.errors import (
    RoadmapException,
    ValidationError,
)
from roadmap.common.errors.error_standards import (
    OperationType,
    RecoveryAction,
    safe_operation,
    with_error_handling,
)


class TestWithErrorHandlingContextManager:
    """Test with_error_handling context manager."""

    def test_context_manager_success(self):
        """Test successful execution in context manager."""
        with with_error_handling("sync", "Issues"):
            result = 42

        assert result == 42

    def test_context_manager_catches_exception(self):
        """Test that exceptions are caught and wrapped."""
        with pytest.raises(RoadmapException):
            with with_error_handling("sync", "Issues"):
                raise ValueError("Test error")

    def test_context_manager_preserves_roadmap_exception(self):
        """Test that RoadmapException gets wrapped in RoadmapException."""
        # The context manager wraps all exceptions in RoadmapException
        # (unless fail_silently=True)
        with pytest.raises(RoadmapException):
            with with_error_handling("sync", "Issues"):
                raise ValidationError("Invalid data")

    def test_context_manager_fail_silently(self):
        """Test fail_silently option."""
        with with_error_handling("sync", "Issues", fail_silently=True):
            raise ValueError("Test error")

        # Should not raise

    def test_context_manager_with_entity_id(self):
        """Test adding entity ID to context manager."""
        with pytest.raises(RoadmapException):
            with with_error_handling("sync", "Issues", entity_id="PROJECT-1"):
                raise ValueError("Test error")


class TestRecoveryAction:
    """Test RecoveryAction helper class."""

    def test_retry_with_backoff_success(self):
        """Test successful retry."""
        call_count = 0

        def flaky_operation():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError("Network error")
            return "success"

        result = RecoveryAction.retry_with_backoff(
            flaky_operation, max_attempts=3, initial_delay=0.01
        )
        assert result == "success"
        assert call_count == 2

    def test_retry_with_backoff_exhaustion(self):
        """Test that retries eventually fail."""

        def failing_operation():
            raise ConnectionError("Network error")

        with pytest.raises(ConnectionError):
            RecoveryAction.retry_with_backoff(
                failing_operation, max_attempts=3, initial_delay=0.01
            )

    @pytest.mark.parametrize(
        "error_instance,should_retry",
        [
            (ConnectionError("timeout"), True),
            (TimeoutError("timeout"), True),
            (ValueError("invalid"), False),
            (RuntimeError("runtime"), False),
        ],
    )
    def test_is_retryable(self, error_instance, should_retry):
        """Test error classification for retry."""
        assert RecoveryAction.is_retryable(error_instance) == should_retry

    @pytest.mark.parametrize(
        "create_default,content",
        [
            (True, None),
            (True, "test content"),
            (False, None),
        ],
    )
    def test_handle_missing_file_scenarios(self, tmp_path, create_default, content):
        """Test missing file handling with various configuration options."""
        filepath = str(tmp_path / f"test_{create_default}_{id(content)}.txt")

        if content is not None:
            success = RecoveryAction.handle_missing_file(
                filepath, create_default=create_default, content=content
            )
            if create_default:
                assert success
                assert Path(filepath).exists()
                assert Path(filepath).read_text() == content
        else:
            success = RecoveryAction.handle_missing_file(
                filepath, create_default=create_default
            )
            if create_default:
                assert success
                assert Path(filepath).exists()
            else:
                assert not success

    @pytest.mark.parametrize(
        "error_type,context,expected_content",
        [
            ("permission", "/path/to/file", "chmod"),
            ("permission", "/path/to/file", "/path/to/file"),
            ("connection", "GitHub API", "GitHub API"),
            ("connection", "GitHub API", "network"),
        ],
    )
    def test_error_recovery_messages(self, error_type, context, expected_content):
        """Test error recovery suggestion messages."""
        if error_type == "permission":
            message = RecoveryAction.handle_permission_error(context)
        else:
            message = RecoveryAction.handle_connection_error(context)

        assert expected_content.lower() in message.lower()


class TestOperationType:
    """Test OperationType constants."""

    @pytest.mark.parametrize(
        "operation_type,expected_value",
        [
            (OperationType.CREATE, "create"),
            (OperationType.READ, "read"),
            (OperationType.UPDATE, "update"),
            (OperationType.DELETE, "delete"),
            (OperationType.SYNC, "sync"),
            (OperationType.IMPORT, "import"),
            (OperationType.EXPORT, "export"),
            (OperationType.VALIDATE, "validate"),
            (OperationType.AUTHENTICATE, "authenticate"),
            (OperationType.FETCH, "fetch"),
            (OperationType.SAVE, "save"),
        ],
    )
    def test_operation_type_constants(self, operation_type, expected_value):
        """Test that operation type constants have correct values."""
        assert operation_type == expected_value


# Integration tests
class TestErrorHandlingIntegration:
    """Integration tests for error handling patterns."""

    def test_complete_create_flow_with_retry(self):
        """Test complete create flow with retry on transient failure."""
        call_count = 0

        @safe_operation(
            OperationType.CREATE,
            "Issue",
            retryable=True,
            max_retries=3,
            retry_delay=0.01,
        )
        def create_issue(title: str):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ConnectionError("Network timeout")
            return {"id": "ISSUE-1", "title": title}

        result = create_issue("Test Issue")
        assert result["id"] == "ISSUE-1"
        assert call_count == 2

    def test_nested_error_context(self):
        """Test using nested error contexts."""

        @safe_operation(OperationType.SYNC, "Issues")
        def sync_issues(project_id: str):
            # Simulate work
            raise RuntimeError("Database connection failed")

        with pytest.raises(RoadmapException):
            sync_issues("PROJECT-1")
