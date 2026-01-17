"""Comprehensive unit tests for error logging module.

Tests cover error classification, recovery suggestion, and all error logging functions.
"""


import pytest

from roadmap.common.logging.error_logging import (
    ErrorClassification,
    classify_error,
    is_error_recoverable,
    log_database_error,
    log_error_with_context,
    log_external_service_error,
    log_validation_error,
    suggest_recovery,
)


class TestLogErrorWithContext:
    """Test log_error_with_context function."""

    def test_log_error_basic(self, error_logging_logger_mocked):
        """Test basic error logging."""
        error = ValueError("Bad value")
        log_error_with_context(error, "parse_config")

        error_logging_logger_mocked.error.assert_called_once()
        call_args = error_logging_logger_mocked.error.call_args
        assert call_args[0][0] == "parse_config_failed"
        assert call_args[1]["operation"] == "parse_config"
        assert call_args[1]["error_type"] == "ValueError"

    def test_log_error_with_entity_context(self, error_logging_logger_mocked):
        """Test error logging with entity context."""
        error = ConnectionError("API unavailable")
        log_error_with_context(
            error,
            "sync_issue",
            entity_type="issue",
            entity_id="issue-123",
        )

        call_args = error_logging_logger_mocked.error.call_args
        assert call_args[1]["entity_type"] == "issue"
        assert call_args[1]["entity_id"] == "issue-123"

    def test_log_error_with_additional_context(self, error_logging_logger_mocked):
        """Test error logging with additional context."""
        error = FileNotFoundError("Config not found")
        additional = {"config_path": "/etc/roadmap.yml", "retry_count": 2}

        log_error_with_context(
            error,
            "load_config",
            additional_context=additional,
        )

        call_args = error_logging_logger_mocked.error.call_args
        assert call_args[1]["config_path"] == "/etc/roadmap.yml"
        assert call_args[1]["retry_count"] == 2

    def test_log_error_with_traceback(self, error_logging_logger_mocked):
        """Test error logging with traceback."""
        error = ValueError("Bad value")
        log_error_with_context(
            error,
            "validate_data",
            include_traceback=True,
        )

        call_args = error_logging_logger_mocked.error.call_args
        assert "traceback" in call_args[1]

    def test_log_error_classification(self, error_logging_logger_mocked):
        """Test that error classification is logged."""
        error = ConnectionError("Network failed")
        log_error_with_context(error, "network_operation")

        call_args = error_logging_logger_mocked.error.call_args
        # ConnectionError is subclass of OSError, so classified as SYSTEM_ERROR
        assert call_args[1]["error_classification"] == ErrorClassification.SYSTEM_ERROR
        assert call_args[1]["is_recoverable"]

    def test_log_error_recovery_suggestion(self, error_logging_logger_mocked):
        """Test that recovery suggestion is logged."""
        error = ValueError("Invalid")
        log_error_with_context(error, "parse_input")

        call_args = error_logging_logger_mocked.error.call_args
        assert call_args[1]["suggested_action"] == "validate_input"

    def test_log_error_all_parameters(self, error_logging_logger_mocked):
        """Test error logging with all parameters."""
        error = OSError("Permission denied")
        log_error_with_context(
            error,
            "write_file",
            entity_type="file",
            entity_id="/path/to/file.txt",
            additional_context={"mode": "w", "encoding": "utf-8"},
            include_traceback=True,
        )

        call_args = error_logging_logger_mocked.error.call_args
        assert call_args[1]["operation"] == "write_file"
        assert call_args[1]["entity_type"] == "file"
        assert call_args[1]["entity_id"] == "/path/to/file.txt"
        assert call_args[1]["mode"] == "w"
        assert "traceback" in call_args[1]


class TestLogValidationError:
    """Test log_validation_error function."""

    def test_log_validation_error_basic(self, error_logging_logger_mocked):
        """Test basic validation error logging."""
        from roadmap.common.errors import ValidationError

        error = ValidationError("Invalid priority")
        log_validation_error(error, "issue")

        error_logging_logger_mocked.warning.assert_called_once()
        call_args = error_logging_logger_mocked.warning.call_args
        assert call_args[0][0] == "validation_error"
        assert call_args[1]["entity_type"] == "issue"
        assert call_args[1]["error_type"] == "ValidationError"

    def test_log_validation_error_with_field(self, error_logging_logger_mocked):
        """Test validation error logging with field name."""
        error = ValueError("Invalid value")
        log_validation_error(error, "issue", field_name="priority")

        call_args = error_logging_logger_mocked.warning.call_args
        assert call_args[1]["field_name"] == "priority"

    def test_log_validation_error_with_value(self, error_logging_logger_mocked):
        """Test validation error logging with proposed value."""
        error = ValueError("Out of range")
        log_validation_error(
            error,
            "issue",
            field_name="estimated_hours",
            proposed_value=-5,
        )

        call_args = error_logging_logger_mocked.warning.call_args
        assert call_args[1]["proposed_value"] == -5

    def test_log_validation_error_suggests_validation(
        self, error_logging_logger_mocked
    ):
        """Test that validation error suggests validation action."""
        error = ValueError("Bad data")
        log_validation_error(error, "milestone")

        call_args = error_logging_logger_mocked.warning.call_args
        assert call_args[1]["suggested_action"] == "validate_input"

    def test_log_validation_error_with_none_values(self, error_logging_logger_mocked):
        """Test validation error with None field and value."""
        error = ValueError("Invalid")
        log_validation_error(error, "project", field_name=None, proposed_value=None)

        call_args = error_logging_logger_mocked.warning.call_args
        assert call_args[1]["field_name"] is None
        assert call_args[1]["proposed_value"] is None


class TestLogDatabaseError:
    """Test log_database_error function."""

    def test_log_database_error_basic(self, error_logging_logger_mocked):
        """Test basic database error logging."""
        error = OSError("Database locked")
        log_database_error(error, "create", entity_type="issue")

        error_logging_logger_mocked.error.assert_called_once()
        call_args = error_logging_logger_mocked.error.call_args
        assert call_args[0][0] == "database_operation_failed"
        assert call_args[1]["operation"] == "create"
        assert call_args[1]["entity_type"] == "issue"

    def test_log_database_error_with_entity_id(self, error_logging_logger_mocked):
        """Test database error logging with entity ID."""
        error = ConnectionError("Connection lost")
        log_database_error(
            error,
            "update",
            entity_type="issue",
            entity_id="issue-456",
        )

        call_args = error_logging_logger_mocked.error.call_args
        assert call_args[1]["entity_id"] == "issue-456"

    def test_log_database_error_with_retry_count(self, error_logging_logger_mocked):
        """Test database error logging with retry count."""
        error = TimeoutError("Query timeout")
        log_database_error(
            error,
            "read",
            entity_type="milestone",
            retry_count=3,
        )

        call_args = error_logging_logger_mocked.error.call_args
        assert call_args[1]["retry_count"] == 3

    def test_log_database_error_recoverable(self, error_logging_logger_mocked):
        """Test that recoverable database errors are marked."""
        error = TimeoutError("Timeout")
        log_database_error(error, "delete", entity_type="project")

        call_args = error_logging_logger_mocked.error.call_args
        assert call_args[1]["is_recoverable"]
        assert call_args[1]["suggested_action"] == "retry"

    def test_log_database_error_not_recoverable(self, error_logging_logger_mocked):
        """Test that non-recoverable database errors are marked."""
        error = OSError("Permission denied")
        log_database_error(error, "create", entity_type="issue")

        call_args = error_logging_logger_mocked.error.call_args
        assert not call_args[1]["is_recoverable"]
        assert call_args[1]["suggested_action"] == "manual_intervention"

    @pytest.mark.parametrize(
        "operation,entity_type,expected_operation",
        [
            ("create", "issue", "create"),
            ("read", "milestone", "read"),
            ("update", "issue", "update"),
            ("delete", "project", "delete"),
        ],
    )
    def test_log_database_error_operations(
        self, error_logging_logger_mocked, operation, entity_type, expected_operation
    ):
        """Test database error logging for different operations.

        Covers lines 423-434: Multiple database operations
        """
        error = ValueError("Bad value")
        log_database_error(error, operation, entity_type=entity_type)

        call_args = error_logging_logger_mocked.error.call_args
        assert call_args[1]["operation"] == expected_operation
        assert call_args[1]["entity_type"] == entity_type

    def test_log_database_error_various_operations(self, error_logging_logger_mocked):
        """Test database error logging for different operations."""
        operations = ["create", "read", "update", "delete"]
        error = ValueError("Bad value")

        for op in operations:
            error_logging_logger_mocked.reset_mock()
            log_database_error(error, op, entity_type="issue")

            call_args = error_logging_logger_mocked.error.call_args
            assert call_args[1]["operation"] == op


class TestLogExternalServiceError:
    """Test log_external_service_error function."""

    def test_log_external_service_error_basic(self, error_logging_logger_mocked):
        """Test basic external service error logging."""
        error = ConnectionError("API unreachable")
        log_external_service_error(error, "github_api", "sync_issues")

        error_logging_logger_mocked.error.assert_called_once()
        call_args = error_logging_logger_mocked.error.call_args
        assert call_args[0][0] == "external_service_error"
        assert call_args[1]["service_name"] == "github_api"
        assert call_args[1]["operation"] == "sync_issues"

    def test_log_external_service_error_with_retry_count(
        self, error_logging_logger_mocked
    ):
        """Test external service error logging with retry count."""
        error = TimeoutError("Request timeout")
        log_external_service_error(
            error,
            "github_api",
            "fetch_issues",
            retry_count=2,
        )

        call_args = error_logging_logger_mocked.error.call_args
        assert call_args[1]["retry_count"] == 2

    @pytest.mark.parametrize(
        "error,is_recoverable,suggested_action",
        [
            (ConnectionError("Service unavailable"), True, "check_connectivity"),
            (RuntimeError("Invalid response"), False, "contact_support"),
        ],
    )
    def test_log_external_service_error_recoverability(
        self, error_logging_logger_mocked, error, is_recoverable, suggested_action
    ):
        """Test external service error logging with recoverability status."""
        log_external_service_error(error, "test_api", "test_op")

        call_args = error_logging_logger_mocked.error.call_args
        assert call_args[1]["is_recoverable"] == is_recoverable
        assert call_args[1]["suggested_action"] == suggested_action

    @pytest.mark.parametrize(
        "service_name",
        [
            "github_api",
            "slack_api",
            "github_graphql",
            "custom_service",
        ],
    )
    def test_log_external_service_error_services(
        self, error_logging_logger_mocked, service_name
    ):
        """Test external service error logging for different services."""
        error = ConnectionError("Connection failed")
        log_external_service_error(error, service_name, "test_operation")

        call_args = error_logging_logger_mocked.error.call_args
        assert call_args[1]["service_name"] == service_name
        assert call_args[1]["operation"] == "test_operation"

    @pytest.mark.parametrize(
        "error,error_type_name",
        [
            (ConnectionError("Network"), "ConnectionError"),
            (TimeoutError("Timeout"), "TimeoutError"),
            (ValueError("Bad value"), "ValueError"),
        ],
    )
    def test_log_external_service_error_types(
        self, error_logging_logger_mocked, error, error_type_name
    ):
        """Test that error type is logged correctly for various errors."""
        log_external_service_error(error, "test_api", "test_op")

        call_args = error_logging_logger_mocked.error.call_args
        assert call_args[1]["error_type"] == error_type_name


class TestErrorLoggingIntegration:
    """Integration tests for error logging."""

    def test_error_workflow_recoverable_error(self, error_logging_logger_mocked):
        """Test complete workflow for recoverable error."""
        error = TimeoutError("Connection timeout")

        # Classify
        classification = classify_error(error)
        # TimeoutError is subclass of OSError, so classified as SYSTEM_ERROR
        assert classification == ErrorClassification.SYSTEM_ERROR

        # Check if recoverable
        recoverable = is_error_recoverable(error)
        assert recoverable

        # Get recovery suggestion
        recovery = suggest_recovery(error)
        assert recovery == "retry"

        # Log with context
        log_error_with_context(
            error,
            "fetch_data",
            entity_type="issue",
            entity_id="issue-789",
        )

        call_args = error_logging_logger_mocked.error.call_args
        assert call_args[1]["is_recoverable"]
        assert call_args[1]["suggested_action"] == "retry"

    def test_error_workflow_user_error(self, error_logging_logger_mocked):
        """Test complete workflow for user error."""
        error = ValueError("Invalid input format")

        # Classify
        classification = classify_error(error)
        assert classification == ErrorClassification.USER_ERROR

        # Check if recoverable
        recoverable = is_error_recoverable(error)
        assert not recoverable

        # Get recovery suggestion
        recovery = suggest_recovery(error)
        assert recovery == "validate_input"

        # Log validation error
        log_validation_error(error, "issue", field_name="priority")

        call_args = error_logging_logger_mocked.warning.call_args
        assert call_args[1]["field_name"] == "priority"
        assert call_args[1]["suggested_action"] == "validate_input"

    def test_error_workflow_system_error(self, error_logging_logger_mocked):
        """Test complete workflow for system error."""
        error = OSError("Disk full")

        # Classify
        classification = classify_error(error)
        assert classification == ErrorClassification.SYSTEM_ERROR

        # Check if recoverable
        recoverable = is_error_recoverable(error)
        assert not recoverable

        # Log database error
        log_database_error(
            error,
            "write",
            entity_type="backup",
            retry_count=1,
        )

        call_args = error_logging_logger_mocked.error.call_args
        assert not call_args[1]["is_recoverable"]
        assert call_args[1]["suggested_action"] == "manual_intervention"

    def test_multiple_error_types(self, error_logging_logger_mocked):
        """Test logging multiple different error types."""
        errors = [
            (ValueError("Bad value"), ErrorClassification.USER_ERROR),
            (OSError("File issue"), ErrorClassification.SYSTEM_ERROR),
            (
                TimeoutError("Timeout"),
                ErrorClassification.SYSTEM_ERROR,
            ),  # Subclass of OSError
            (RuntimeError("Unknown"), ErrorClassification.UNKNOWN_ERROR),
        ]

        for error, expected_class in errors:
            assert classify_error(error) == expected_class

    def test_error_message_preservation(self, error_logging_logger_mocked):
        """Test that error messages are preserved in logs."""
        error_message = "Very specific error message"
        error = ValueError(error_message)

        log_error_with_context(error, "test_operation")

        call_args = error_logging_logger_mocked.error.call_args
        assert call_args[1]["error_message"] == error_message
