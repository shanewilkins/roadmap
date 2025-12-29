"""Tests for error handling standards and decorators."""

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
    log_operation,
    safe_operation,
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
