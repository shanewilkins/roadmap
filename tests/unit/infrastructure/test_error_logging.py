"""Comprehensive unit tests for error logging module.

Tests cover error classification, recovery suggestion, and all error logging functions.
"""

from unittest.mock import patch

from roadmap.infrastructure.logging.error_logging import (
    ErrorClassification,
    classify_error,
    is_error_recoverable,
    log_database_error,
    log_error_with_context,
    log_external_service_error,
    log_validation_error,
    suggest_recovery,
)


class TestErrorClassification:
    """Test ErrorClassification constants."""

    def test_error_classification_constants(self):
        """Test that classification constants are defined."""
        assert ErrorClassification.USER_ERROR == "user_error"
        assert ErrorClassification.SYSTEM_ERROR == "system_error"
        assert ErrorClassification.EXTERNAL_ERROR == "external_error"
        assert ErrorClassification.UNKNOWN_ERROR == "unknown_error"


class TestClassifyError:
    """Test classify_error function."""

    def test_classify_validation_error(self):
        """Test classification of ValidationError."""
        from roadmap.common.errors import ValidationError

        error = ValidationError("Invalid value")
        result = classify_error(error)
        assert result == ErrorClassification.USER_ERROR

    def test_classify_value_error(self):
        """Test classification of ValueError."""
        error = ValueError("Bad value")
        result = classify_error(error)
        assert result == ErrorClassification.USER_ERROR

    def test_classify_type_error(self):
        """Test classification of TypeError."""
        error = TypeError("Type mismatch")
        result = classify_error(error)
        assert result == ErrorClassification.USER_ERROR

    def test_classify_key_error(self):
        """Test classification of KeyError."""
        error = KeyError("Missing key")
        result = classify_error(error)
        assert result == ErrorClassification.USER_ERROR

    def test_classify_os_error(self):
        """Test classification of OSError."""
        error = OSError("File not found")
        result = classify_error(error)
        assert result == ErrorClassification.SYSTEM_ERROR

    def test_classify_file_not_found_error(self):
        """Test classification of FileNotFoundError."""
        error = FileNotFoundError("Missing file")
        result = classify_error(error)
        assert result == ErrorClassification.SYSTEM_ERROR

    def test_classify_permission_error(self):
        """Test classification of PermissionError."""
        error = PermissionError("Access denied")
        result = classify_error(error)
        assert result == ErrorClassification.SYSTEM_ERROR

    def test_classify_connection_error(self):
        """Test classification of ConnectionError."""
        error = ConnectionError("Connection failed")
        result = classify_error(error)
        # ConnectionError is a subclass of OSError, so it's classified as SYSTEM_ERROR
        assert result == ErrorClassification.SYSTEM_ERROR

    def test_classify_timeout_error(self):
        """Test classification of TimeoutError."""
        error = TimeoutError("Request timeout")
        result = classify_error(error)
        # TimeoutError is a subclass of OSError, so it's classified as SYSTEM_ERROR
        assert result == ErrorClassification.SYSTEM_ERROR

    def test_classify_runtime_error(self):
        """Test classification of RuntimeError."""
        error = RuntimeError("Runtime problem")
        result = classify_error(error)
        assert result == ErrorClassification.UNKNOWN_ERROR

    def test_classify_generic_exception(self):
        """Test classification of generic Exception."""
        error = Exception("Unknown error")
        result = classify_error(error)
        assert result == ErrorClassification.UNKNOWN_ERROR


class TestIsErrorRecoverable:
    """Test is_error_recoverable function."""

    def test_recoverable_connection_error(self):
        """Test that ConnectionError is recoverable."""
        error = ConnectionError("Network issue")
        assert is_error_recoverable(error) is True

    def test_recoverable_timeout_error(self):
        """Test that TimeoutError is recoverable."""
        error = TimeoutError("Request timeout")
        assert is_error_recoverable(error) is True

    def test_recoverable_blocking_io_error(self):
        """Test that BlockingIOError is recoverable."""
        error = BlockingIOError("Blocking I/O")
        assert is_error_recoverable(error) is True

    def test_recoverable_broken_pipe_error(self):
        """Test that BrokenPipeError is recoverable."""
        error = BrokenPipeError("Pipe broken")
        assert is_error_recoverable(error) is True

    def test_not_recoverable_value_error(self):
        """Test that ValueError is not recoverable."""
        error = ValueError("Bad value")
        assert is_error_recoverable(error) is False

    def test_not_recoverable_os_error(self):
        """Test that OSError is not recoverable."""
        error = OSError("File issue")
        assert is_error_recoverable(error) is False

    def test_not_recoverable_runtime_error(self):
        """Test that RuntimeError is not recoverable."""
        error = RuntimeError("Runtime problem")
        assert is_error_recoverable(error) is False


class TestSuggestRecovery:
    """Test suggest_recovery function."""

    def test_suggest_recovery_for_connection_error(self):
        """Test recovery suggestion for recoverable errors."""
        error = ConnectionError("Connection failed")
        result = suggest_recovery(error)
        assert result == "retry"

    def test_suggest_recovery_for_timeout_error(self):
        """Test recovery suggestion for timeout errors."""
        error = TimeoutError("Timeout")
        result = suggest_recovery(error)
        assert result == "retry"

    def test_suggest_recovery_for_blocking_io_error(self):
        """Test recovery suggestion for BlockingIOError."""
        error = BlockingIOError("Blocking I/O")
        result = suggest_recovery(error)
        assert result == "retry"

    def test_suggest_recovery_for_validation_error(self):
        """Test recovery suggestion for validation errors."""
        from roadmap.common.errors import ValidationError

        error = ValidationError("Invalid")
        result = suggest_recovery(error)
        assert result == "validate_input"

    def test_suggest_recovery_for_value_error(self):
        """Test recovery suggestion for value errors."""
        error = ValueError("Bad value")
        result = suggest_recovery(error)
        assert result == "validate_input"

    def test_suggest_recovery_for_os_error(self):
        """Test recovery suggestion for OS errors."""
        error = OSError("Permission denied")
        result = suggest_recovery(error)
        assert result == "manual_intervention"

    def test_suggest_recovery_for_runtime_error(self):
        """Test recovery suggestion for unknown errors."""
        error = RuntimeError("Unknown problem")
        result = suggest_recovery(error)
        assert result == "contact_support"

    def test_suggest_recovery_with_context(self):
        """Test recovery suggestion with context."""
        error = ValueError("Bad input")
        context = {"operation": "parsing", "field": "name"}
        result = suggest_recovery(error, context)
        assert result == "validate_input"


class TestLogErrorWithContext:
    """Test log_error_with_context function."""

    @patch("roadmap.infrastructure.logging.error_logging.logger")
    def test_log_error_basic(self, mock_logger):
        """Test basic error logging."""
        error = ValueError("Bad value")
        log_error_with_context(error, "parse_config")

        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args
        assert call_args[0][0] == "parse_config_failed"
        assert call_args[1]["operation"] == "parse_config"
        assert call_args[1]["error_type"] == "ValueError"

    @patch("roadmap.infrastructure.logging.error_logging.logger")
    def test_log_error_with_entity_context(self, mock_logger):
        """Test error logging with entity context."""
        error = ConnectionError("API unavailable")
        log_error_with_context(
            error,
            "sync_issue",
            entity_type="issue",
            entity_id="issue-123",
        )

        call_args = mock_logger.error.call_args
        assert call_args[1]["entity_type"] == "issue"
        assert call_args[1]["entity_id"] == "issue-123"

    @patch("roadmap.infrastructure.logging.error_logging.logger")
    def test_log_error_with_additional_context(self, mock_logger):
        """Test error logging with additional context."""
        error = FileNotFoundError("Config not found")
        additional = {"config_path": "/etc/roadmap.yml", "retry_count": 2}

        log_error_with_context(
            error,
            "load_config",
            additional_context=additional,
        )

        call_args = mock_logger.error.call_args
        assert call_args[1]["config_path"] == "/etc/roadmap.yml"
        assert call_args[1]["retry_count"] == 2

    @patch("roadmap.infrastructure.logging.error_logging.logger")
    def test_log_error_with_traceback(self, mock_logger):
        """Test error logging with traceback."""
        error = ValueError("Bad value")
        log_error_with_context(
            error,
            "validate_data",
            include_traceback=True,
        )

        call_args = mock_logger.error.call_args
        assert "traceback" in call_args[1]

    @patch("roadmap.infrastructure.logging.error_logging.logger")
    def test_log_error_classification(self, mock_logger):
        """Test that error classification is logged."""
        error = ConnectionError("Network failed")
        log_error_with_context(error, "network_operation")

        call_args = mock_logger.error.call_args
        # ConnectionError is subclass of OSError, so classified as SYSTEM_ERROR
        assert call_args[1]["error_classification"] == ErrorClassification.SYSTEM_ERROR
        assert call_args[1]["is_recoverable"] is True

    @patch("roadmap.infrastructure.logging.error_logging.logger")
    def test_log_error_recovery_suggestion(self, mock_logger):
        """Test that recovery suggestion is logged."""
        error = ValueError("Invalid")
        log_error_with_context(error, "parse_input")

        call_args = mock_logger.error.call_args
        assert call_args[1]["suggested_action"] == "validate_input"

    @patch("roadmap.infrastructure.logging.error_logging.logger")
    def test_log_error_all_parameters(self, mock_logger):
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

        call_args = mock_logger.error.call_args
        assert call_args[1]["operation"] == "write_file"
        assert call_args[1]["entity_type"] == "file"
        assert call_args[1]["entity_id"] == "/path/to/file.txt"
        assert call_args[1]["mode"] == "w"
        assert "traceback" in call_args[1]


class TestLogValidationError:
    """Test log_validation_error function."""

    @patch("roadmap.infrastructure.logging.error_logging.logger")
    def test_log_validation_error_basic(self, mock_logger):
        """Test basic validation error logging."""
        from roadmap.common.errors import ValidationError

        error = ValidationError("Invalid priority")
        log_validation_error(error, "issue")

        mock_logger.warning.assert_called_once()
        call_args = mock_logger.warning.call_args
        assert call_args[0][0] == "validation_error"
        assert call_args[1]["entity_type"] == "issue"
        assert call_args[1]["error_type"] == "ValidationError"

    @patch("roadmap.infrastructure.logging.error_logging.logger")
    def test_log_validation_error_with_field(self, mock_logger):
        """Test validation error logging with field name."""
        error = ValueError("Invalid value")
        log_validation_error(error, "issue", field_name="priority")

        call_args = mock_logger.warning.call_args
        assert call_args[1]["field_name"] == "priority"

    @patch("roadmap.infrastructure.logging.error_logging.logger")
    def test_log_validation_error_with_value(self, mock_logger):
        """Test validation error logging with proposed value."""
        error = ValueError("Out of range")
        log_validation_error(
            error,
            "issue",
            field_name="estimated_hours",
            proposed_value=-5,
        )

        call_args = mock_logger.warning.call_args
        assert call_args[1]["proposed_value"] == -5

    @patch("roadmap.infrastructure.logging.error_logging.logger")
    def test_log_validation_error_suggests_validation(self, mock_logger):
        """Test that validation error suggests validation action."""
        error = ValueError("Bad data")
        log_validation_error(error, "milestone")

        call_args = mock_logger.warning.call_args
        assert call_args[1]["suggested_action"] == "validate_input"

    @patch("roadmap.infrastructure.logging.error_logging.logger")
    def test_log_validation_error_with_none_values(self, mock_logger):
        """Test validation error with None field and value."""
        error = ValueError("Invalid")
        log_validation_error(error, "project", field_name=None, proposed_value=None)

        call_args = mock_logger.warning.call_args
        assert call_args[1]["field_name"] is None
        assert call_args[1]["proposed_value"] is None


class TestLogDatabaseError:
    """Test log_database_error function."""

    @patch("roadmap.infrastructure.logging.error_logging.logger")
    def test_log_database_error_basic(self, mock_logger):
        """Test basic database error logging."""
        error = OSError("Database locked")
        log_database_error(error, "create", entity_type="issue")

        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args
        assert call_args[0][0] == "database_operation_failed"
        assert call_args[1]["operation"] == "create"
        assert call_args[1]["entity_type"] == "issue"

    @patch("roadmap.infrastructure.logging.error_logging.logger")
    def test_log_database_error_with_entity_id(self, mock_logger):
        """Test database error logging with entity ID."""
        error = ConnectionError("Connection lost")
        log_database_error(
            error,
            "update",
            entity_type="issue",
            entity_id="issue-456",
        )

        call_args = mock_logger.error.call_args
        assert call_args[1]["entity_id"] == "issue-456"

    @patch("roadmap.infrastructure.logging.error_logging.logger")
    def test_log_database_error_with_retry_count(self, mock_logger):
        """Test database error logging with retry count."""
        error = TimeoutError("Query timeout")
        log_database_error(
            error,
            "read",
            entity_type="milestone",
            retry_count=3,
        )

        call_args = mock_logger.error.call_args
        assert call_args[1]["retry_count"] == 3

    @patch("roadmap.infrastructure.logging.error_logging.logger")
    def test_log_database_error_recoverable(self, mock_logger):
        """Test that recoverable database errors are marked."""
        error = TimeoutError("Timeout")
        log_database_error(error, "delete", entity_type="project")

        call_args = mock_logger.error.call_args
        assert call_args[1]["is_recoverable"] is True
        assert call_args[1]["suggested_action"] == "retry"

    @patch("roadmap.infrastructure.logging.error_logging.logger")
    def test_log_database_error_not_recoverable(self, mock_logger):
        """Test that non-recoverable database errors are marked."""
        error = OSError("Permission denied")
        log_database_error(error, "create", entity_type="issue")

        call_args = mock_logger.error.call_args
        assert call_args[1]["is_recoverable"] is False
        assert call_args[1]["suggested_action"] == "manual_intervention"

    @patch("roadmap.infrastructure.logging.error_logging.logger")
    def test_log_database_error_various_operations(self, mock_logger):
        """Test database error logging for different operations."""
        operations = ["create", "read", "update", "delete"]
        error = ValueError("Bad value")

        for op in operations:
            mock_logger.reset_mock()
            log_database_error(error, op, entity_type="issue")

            call_args = mock_logger.error.call_args
            assert call_args[1]["operation"] == op


class TestLogExternalServiceError:
    """Test log_external_service_error function."""

    @patch("roadmap.infrastructure.logging.error_logging.logger")
    def test_log_external_service_error_basic(self, mock_logger):
        """Test basic external service error logging."""
        error = ConnectionError("API unreachable")
        log_external_service_error(error, "github_api", "sync_issues")

        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args
        assert call_args[0][0] == "external_service_error"
        assert call_args[1]["service_name"] == "github_api"
        assert call_args[1]["operation"] == "sync_issues"

    @patch("roadmap.infrastructure.logging.error_logging.logger")
    def test_log_external_service_error_with_retry_count(self, mock_logger):
        """Test external service error logging with retry count."""
        error = TimeoutError("Request timeout")
        log_external_service_error(
            error,
            "github_api",
            "fetch_issues",
            retry_count=2,
        )

        call_args = mock_logger.error.call_args
        assert call_args[1]["retry_count"] == 2

    @patch("roadmap.infrastructure.logging.error_logging.logger")
    def test_log_external_service_error_recoverable(self, mock_logger):
        """Test that recoverable external errors suggest retry."""
        error = ConnectionError("Service temporarily unavailable")
        log_external_service_error(error, "slack_api", "post_message")

        call_args = mock_logger.error.call_args
        assert call_args[1]["is_recoverable"] is True
        assert call_args[1]["suggested_action"] == "check_connectivity"

    @patch("roadmap.infrastructure.logging.error_logging.logger")
    def test_log_external_service_error_not_recoverable(self, mock_logger):
        """Test that non-recoverable external errors suggest contact support."""
        error = RuntimeError("Invalid API response")
        log_external_service_error(error, "github_api", "get_user")

        call_args = mock_logger.error.call_args
        assert call_args[1]["is_recoverable"] is False
        assert call_args[1]["suggested_action"] == "contact_support"

    @patch("roadmap.infrastructure.logging.error_logging.logger")
    def test_log_external_service_error_different_services(self, mock_logger):
        """Test external service error logging for different services."""
        services = ["github_api", "slack_api", "github_graphql", "custom_service"]
        error = ConnectionError("Connection failed")

        for service in services:
            mock_logger.reset_mock()
            log_external_service_error(error, service, "test_operation")

            call_args = mock_logger.error.call_args
            assert call_args[1]["service_name"] == service

    @patch("roadmap.infrastructure.logging.error_logging.logger")
    def test_log_external_service_error_error_type(self, mock_logger):
        """Test that error type is logged correctly."""
        errors = [
            (ConnectionError("Network"), "ConnectionError"),
            (TimeoutError("Timeout"), "TimeoutError"),
            (ValueError("Bad value"), "ValueError"),
        ]

        for error, error_name in errors:
            mock_logger.reset_mock()
            log_external_service_error(error, "test_api", "test_op")

            call_args = mock_logger.error.call_args
            assert call_args[1]["error_type"] == error_name


class TestErrorLoggingIntegration:
    """Integration tests for error logging."""

    @patch("roadmap.infrastructure.logging.error_logging.logger")
    def test_error_workflow_recoverable_error(self, mock_logger):
        """Test complete workflow for recoverable error."""
        error = TimeoutError("Connection timeout")

        # Classify
        classification = classify_error(error)
        # TimeoutError is subclass of OSError, so classified as SYSTEM_ERROR
        assert classification == ErrorClassification.SYSTEM_ERROR

        # Check if recoverable
        recoverable = is_error_recoverable(error)
        assert recoverable is True

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

        call_args = mock_logger.error.call_args
        assert call_args[1]["is_recoverable"] is True
        assert call_args[1]["suggested_action"] == "retry"

    @patch("roadmap.infrastructure.logging.error_logging.logger")
    def test_error_workflow_user_error(self, mock_logger):
        """Test complete workflow for user error."""
        error = ValueError("Invalid input format")

        # Classify
        classification = classify_error(error)
        assert classification == ErrorClassification.USER_ERROR

        # Check if recoverable
        recoverable = is_error_recoverable(error)
        assert recoverable is False

        # Get recovery suggestion
        recovery = suggest_recovery(error)
        assert recovery == "validate_input"

        # Log validation error
        log_validation_error(error, "issue", field_name="priority")

        call_args = mock_logger.warning.call_args
        assert call_args[1]["field_name"] == "priority"
        assert call_args[1]["suggested_action"] == "validate_input"

    @patch("roadmap.infrastructure.logging.error_logging.logger")
    def test_error_workflow_system_error(self, mock_logger):
        """Test complete workflow for system error."""
        error = OSError("Disk full")

        # Classify
        classification = classify_error(error)
        assert classification == ErrorClassification.SYSTEM_ERROR

        # Check if recoverable
        recoverable = is_error_recoverable(error)
        assert recoverable is False

        # Log database error
        log_database_error(
            error,
            "write",
            entity_type="backup",
            retry_count=1,
        )

        call_args = mock_logger.error.call_args
        assert call_args[1]["is_recoverable"] is False
        assert call_args[1]["suggested_action"] == "manual_intervention"

    @patch("roadmap.infrastructure.logging.error_logging.logger")
    def test_multiple_error_types(self, mock_logger):
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

    @patch("roadmap.infrastructure.logging.error_logging.logger")
    def test_error_message_preservation(self, mock_logger):
        """Test that error messages are preserved in logs."""
        error_message = "Very specific error message"
        error = ValueError(error_message)

        log_error_with_context(error, "test_operation")

        call_args = mock_logger.error.call_args
        assert call_args[1]["error_message"] == error_message
