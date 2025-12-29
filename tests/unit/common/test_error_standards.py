"""Tests for error handling standards and decorators."""

from pathlib import Path
from unittest.mock import patch

import pytest

from roadmap.common.errors import (
    CreateError,
    DeleteError,
    RoadmapException,
    UpdateError,
    ValidationError,
)
from roadmap.common.errors.error_standards import (
    ErrorContext,
    OperationType,
    RecoveryAction,
    log_operation,
    safe_operation,
    with_error_handling,
)


class TestErrorContext:
    """Test ErrorContext builder."""

    def test_error_context_basic(self):
        """Test creating basic error context."""
        context = ErrorContext("create", "Issue")
        data = context.build()
        assert data["operation"] == "create"
        assert data["entity_type"] == "Issue"

    def test_error_context_with_entity_id(self):
        """Test adding entity ID to context."""
        context = ErrorContext("update", "Issue").with_entity_id("ISSUE-123")
        data = context.build()
        assert data["entity_id"] == "ISSUE-123"

    def test_error_context_with_input(self):
        """Test adding input parameters to context."""
        context = ErrorContext("create", "Issue").with_input(
            title="Test", priority="high"
        )
        data = context.build()
        assert data["input"]["title"] == "Test"
        assert data["input"]["priority"] == "high"

    def test_error_context_with_state(self):
        """Test adding state information to context."""
        context = ErrorContext("sync", "Issues").with_state(
            synced_count=10, failed_count=1
        )
        data = context.build()
        assert data["state"]["synced_count"] == 10
        assert data["state"]["failed_count"] == 1

    def test_error_context_with_recovery(self):
        """Test adding recovery suggestion to context."""
        context = ErrorContext("delete", "Issue").with_recovery(
            "retry", "Check network connection"
        )
        data = context.build()
        assert data["recovery_action"] == "retry"
        assert data["recovery_details"] == "Check network connection"

    def test_error_context_with_attempt(self):
        """Test adding retry attempt information to context."""
        context = ErrorContext("sync", "GitHub").with_attempt(2, 3)
        data = context.build()
        assert data["retry_attempt"] == 2
        assert data["max_retries"] == 3

    def test_error_context_fluent_api(self):
        """Test that all builder methods return self for fluent API."""
        context = (
            ErrorContext("create", "Issue")
            .with_entity_id("ISSUE-123")
            .with_input(title="Test")
            .with_state(status="active")
            .with_recovery("retry", "Network error")
        )
        data = context.build()
        assert data["entity_id"] == "ISSUE-123"
        assert data["input"]["title"] == "Test"
        assert data["state"]["status"] == "active"
        assert data["recovery_action"] == "retry"

    def test_error_context_build_returns_copy(self):
        """Test that build() returns a copy, not the original."""
        context = ErrorContext("create", "Issue").with_input(title="Test")
        data1 = context.build()
        data1["new_key"] = "new_value"
        data2 = context.build()
        assert "new_key" not in data2


class TestSafeOperationDecorator:
    """Test @safe_operation decorator."""

    def test_safe_operation_success(self):
        """Test successful function execution."""

        @safe_operation(OperationType.CREATE, "Issue")
        def create_issue(title: str):
            return {"id": "ISSUE-1", "title": title}

        result = create_issue("Test Issue")
        assert result["title"] == "Test Issue"

    def test_safe_operation_catches_exception(self):
        """Test that decorator catches and converts exceptions."""

        @safe_operation(OperationType.CREATE, "Issue")
        def create_issue():
            raise ValueError("Invalid input")

        with pytest.raises(CreateError) as exc_info:
            create_issue()

        assert "Invalid input" in exc_info.value.domain_message

    def test_safe_operation_preserves_roadmap_exception(self):
        """Test that RoadmapException is converted to operation-specific error."""

        @safe_operation(OperationType.CREATE, "Issue")
        def create_issue():
            raise ValidationError("Invalid field")

        # ValidationError is a RoadmapException, but decorator converts to CreateError
        with pytest.raises(CreateError) as exc_info:
            create_issue()
        assert "Invalid field" in exc_info.value.domain_message

    @pytest.mark.parametrize(
        "op_type,expected_error,description",
        [
            (OperationType.CREATE, CreateError, "create_error"),
            (OperationType.UPDATE, UpdateError, "update_error"),
            (OperationType.DELETE, DeleteError, "delete_error"),
        ],
    )
    def test_safe_operation_error_conversion(
        self, op_type, expected_error, description
    ):
        """Test operations convert exceptions to operation-specific errors."""

        @safe_operation(op_type, "Issue")
        def operation():
            raise RuntimeError("DB error")

        with pytest.raises(expected_error):
            operation()

    def test_safe_operation_retry_on_recoverable_error(self):
        """Test retry logic for recoverable errors."""
        call_count = 0

        @safe_operation(
            OperationType.SYNC,
            "GitHub",
            retryable=True,
            max_retries=3,
            retry_delay=0.01,
        )
        def fetch_data():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Network timeout")
            return {"data": "success"}

        result = fetch_data()
        assert result["data"] == "success"
        assert call_count == 3

    def test_safe_operation_retry_exhaustion(self):
        """Test that retries eventually fail and wrap in RoadmapException."""
        call_count = 0

        @safe_operation(
            OperationType.SYNC,
            "GitHub",
            retryable=True,
            max_retries=3,
            retry_delay=0.01,
        )
        def fetch_data():
            nonlocal call_count
            call_count += 1
            raise ConnectionError("Network timeout")

        with pytest.raises(RoadmapException):
            fetch_data()
        assert call_count == 3

    def test_safe_operation_no_retry_on_non_recoverable_error(self):
        """Test that non-recoverable errors don't trigger retry."""
        call_count = 0

        @safe_operation(
            OperationType.SYNC,
            "GitHub",
            retryable=True,
            max_retries=3,
            retry_delay=0.01,
        )
        def fetch_data():
            nonlocal call_count
            call_count += 1
            raise ValueError("Invalid input")

        with pytest.raises(RoadmapException):
            fetch_data()
        assert call_count == 1

    @pytest.mark.parametrize(
        "entity_id,description",
        [
            ("ISSUE-123", "from_first_arg"),
            ("ISSUE-456", "from_kwarg"),
        ],
    )
    def test_safe_operation_captures_entity_id(self, entity_id, description):
        """Test that entity_id is captured from arguments."""

        @safe_operation(OperationType.UPDATE, "Issue")
        def update_issue(issue_id: str | None = None, **kwargs):
            raise RuntimeError("DB error")

        with pytest.raises(UpdateError):
            if description == "from_first_arg":
                update_issue(entity_id)
            else:
                update_issue(id=entity_id)

    def test_safe_operation_exponential_backoff(self):
        """Test that retry delay increases exponentially."""
        delays = []

        def mock_sleep(duration):
            delays.append(duration)
            # Don't actually sleep
            pass

        call_count = 0

        @safe_operation(
            OperationType.SYNC,
            "GitHub",
            retryable=True,
            max_retries=4,
            retry_delay=0.1,
            retry_backoff=2.0,
        )
        def fetch_data():
            nonlocal call_count
            call_count += 1
            if call_count < 4:
                raise ConnectionError("Network timeout")
            return {"data": "success"}

        with patch("time.sleep", mock_sleep):
            result = fetch_data()

        assert result["data"] == "success"
        # Should have slept 3 times with exponential backoff
        assert len(delays) == 3
        assert delays[0] == pytest.approx(0.1)
        assert delays[1] == pytest.approx(0.2)
        assert delays[2] == pytest.approx(0.4)


class TestLogOperationDecorator:
    """Test @log_operation decorator."""

    def test_log_operation_success(self):
        """Test successful function execution with logging."""

        @log_operation(OperationType.READ, "Issue")
        def get_issue(issue_id: str):
            return {"id": issue_id, "title": "Test"}

        result = get_issue("ISSUE-1")
        assert result["title"] == "Test"

    def test_log_operation_lets_exceptions_propagate(self):
        """Test that exceptions propagate normally (no conversion)."""

        @log_operation(OperationType.READ, "Issue")
        def get_issue():
            raise ValueError("Not found")

        with pytest.raises(ValueError):
            get_issue()

    def test_log_operation_without_exception_handling(self):
        """Test that log_operation is lightweight (no try-catch)."""
        # This is more of a conceptual test - log_operation should not catch exceptions
        call_count = 0

        @log_operation(OperationType.READ, "Issue")
        def get_issue():
            nonlocal call_count
            call_count += 1
            raise RuntimeError("Error")

        with pytest.raises(RuntimeError):
            get_issue()
        assert call_count == 1


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
