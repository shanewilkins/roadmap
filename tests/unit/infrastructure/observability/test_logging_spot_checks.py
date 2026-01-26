"""Logging Spot-Check Tests.

Verify that critical error paths are properly logging with context.
Focuses on verifying logging in archive, CLI commands, and GitHub handlers.
"""

from unittest.mock import patch

from roadmap.common.errors import (
    GitError,
    GitHubAPIError,
    NetworkError,
    ValidationError,
)
from roadmap.common.logging.error_logging import (
    ErrorClassification,
    classify_error,
    is_error_recoverable,
    log_error_with_context,
    suggest_recovery,
)


class TestErrorClassification:
    """Test error classification system."""

    def test_classify_validation_error(self):
        """Test classifying validation errors as user errors."""
        error = ValidationError("Invalid input")
        classification = classify_error(error)
        assert classification == ErrorClassification.USER_ERROR

    def test_classify_os_error(self):
        """Test classifying file operation errors as system errors."""
        error = FileNotFoundError("File not found")
        classification = classify_error(error)
        assert classification == ErrorClassification.SYSTEM_ERROR

    def test_classify_permission_error(self):
        """Test classifying permission errors as system errors."""
        error = PermissionError("Access denied")
        classification = classify_error(error)
        assert classification == ErrorClassification.SYSTEM_ERROR

    def test_classify_git_error(self):
        """Test classifying git errors."""
        error = GitError("clone", "Repository corrupted")
        classification = classify_error(error)
        # GitError is a RoadmapException (not RoadmapError), so returns UNKNOWN_ERROR
        assert classification == ErrorClassification.UNKNOWN_ERROR

    def test_classify_github_api_error(self):
        """Test classifying GitHub API errors."""
        error = GitHubAPIError("fetch_issues", "API error")
        classification = classify_error(error)
        # GitHubAPIError is a RoadmapError, so returns SYSTEM_ERROR
        assert classification == ErrorClassification.SYSTEM_ERROR

    def test_classify_timeout_error(self):
        """Test classifying timeout errors as system errors."""
        error = TimeoutError("Request timed out")
        classification = classify_error(error)
        # TimeoutError is not in the checked types, so returns SYSTEM_ERROR
        assert classification == ErrorClassification.SYSTEM_ERROR

    def test_classify_connection_error(self):
        """Test classifying connection errors as system errors."""
        error = ConnectionError("Connection refused")
        classification = classify_error(error)
        # ConnectionError is not in the OSError | RoadmapError check, returns SYSTEM_ERROR
        assert classification == ErrorClassification.SYSTEM_ERROR

    def test_classify_type_error(self):
        """Test classifying type errors as user errors."""
        error = TypeError("Invalid type")
        classification = classify_error(error)
        assert classification == ErrorClassification.USER_ERROR

    def test_classify_key_error(self):
        """Test classifying key errors as user errors."""
        error = KeyError("Missing key")
        classification = classify_error(error)
        assert classification == ErrorClassification.USER_ERROR

    def test_classify_unknown_error(self):
        """Test classifying unknown errors."""
        error = RuntimeError("Something unexpected happened")
        classification = classify_error(error)
        assert classification == ErrorClassification.UNKNOWN_ERROR


class TestErrorRecoverability:
    """Test error recoverability assessment."""

    def test_network_error_recoverable(self):
        """Test that connection errors are considered recoverable."""
        error = ConnectionError("Connection refused")
        is_recoverable = is_error_recoverable(error)
        assert is_recoverable

    def test_validation_error_not_recoverable(self):
        """Test that validation errors are not recoverable."""
        error = ValidationError("Invalid input")
        is_recoverable = is_error_recoverable(error)
        assert not is_recoverable

    def test_permission_error_not_recoverable(self):
        """Test that permission errors are not recoverable."""
        error = PermissionError("Access denied")
        is_recoverable = is_error_recoverable(error)
        assert not is_recoverable

    def test_timeout_error_recoverable(self):
        """Test that timeout errors are recoverable."""
        error = TimeoutError("Request timed out")
        is_recoverable = is_error_recoverable(error)
        assert is_recoverable

    def test_broken_pipe_recoverable(self):
        """Test that broken pipe errors are recoverable."""
        error = BrokenPipeError("Broken pipe")
        is_recoverable = is_error_recoverable(error)
        assert is_recoverable


class TestErrorContextLogging:
    """Test error logging with context."""

    def test_log_error_with_operation_context(self):
        """Test logging error with operation context."""
        error = ValidationError("Invalid input")

        with patch("roadmap.common.logging.error_logging.logger") as mock_logger:
            log_error_with_context(
                error=error,
                operation="create_issue",
                entity_type="issue",
                entity_id="123",
            )

            mock_logger.error.assert_called_once()
            call_args = mock_logger.error.call_args
            assert call_args[0][0] == "operation_failed"
            assert "operation" in call_args[1]
            assert call_args[1]["operation"] == "create_issue"

    def test_log_error_with_additional_context(self):
        """Test logging error with additional context."""
        error = GitHubAPIError("API error")
        additional = {"retry_count": 3, "endpoint": "/issues"}

        with patch("roadmap.common.logging.error_logging.logger") as mock_logger:
            log_error_with_context(
                error=error,
                operation="sync_issues",
                additional_context=additional,
            )

            mock_logger.error.assert_called_once()
            call_args = mock_logger.error.call_args
            assert call_args[1]["retry_count"] == 3
            assert call_args[1]["endpoint"] == "/issues"

    def test_log_error_with_traceback(self):
        """Test logging error with traceback included."""
        error = GitError("clone", "Repository corrupted")

        with patch("roadmap.common.logging.error_logging.logger") as mock_logger:
            log_error_with_context(
                error=error,
                operation="clone_repo",
                include_traceback=True,
            )

            mock_logger.error.assert_called_once()
            call_args = mock_logger.error.call_args
            assert "traceback" in call_args[1]

    def test_log_error_classification_in_context(self):
        """Test that error classification is included in logged context."""
        error = TimeoutError("Request timed out")

        with patch("roadmap.common.logging.error_logging.logger") as mock_logger:
            log_error_with_context(
                error=error,
                operation="fetch_data",
            )

            mock_logger.error.assert_called_once()
            call_args = mock_logger.error.call_args
            assert "error_classification" in call_args[1]
            # TimeoutError returns SYSTEM_ERROR based on the classify_error logic
            assert (
                call_args[1]["error_classification"] == ErrorClassification.SYSTEM_ERROR
            )

    def test_log_error_includes_recovery_suggestion(self):
        """Test that error includes recovery suggestion."""
        error = ConnectionError("Connection refused")

        with patch("roadmap.common.logging.error_logging.logger") as mock_logger:
            log_error_with_context(
                error=error,
                operation="connect_to_server",
            )

            mock_logger.error.assert_called_once()
            call_args = mock_logger.error.call_args
            assert "suggested_action" in call_args[1]


class TestSuggestRecovery:
    """Test recovery suggestion logic."""

    def test_suggest_retry_for_network_error(self):
        """Test suggesting retry for network errors."""
        error = ConnectionError("Connection refused")
        recovery = suggest_recovery(error)
        assert isinstance(recovery, str)

    def test_suggest_recovery_for_validation_error(self):
        """Test suggesting recovery for validation errors."""
        error = ValidationError("Invalid input")
        recovery = suggest_recovery(error)
        assert isinstance(recovery, str)

    def test_suggest_recovery_for_timeout(self):
        """Test suggesting recovery for timeout errors."""
        error = TimeoutError("Request timed out")
        recovery = suggest_recovery(error)
        assert isinstance(recovery, str)

    def test_suggest_recovery_for_git_error(self):
        """Test suggesting recovery for git errors."""
        error = GitError("clone", "Repository not found")
        recovery = suggest_recovery(error)
        assert isinstance(recovery, str)


class TestCriticalPathLogging:
    """Test logging in critical paths."""

    def test_archive_error_logging(self):
        """Test that archive operations log errors properly."""
        error = OSError("Disk full")

        with patch("roadmap.common.logging.error_logging.logger") as mock_logger:
            log_error_with_context(
                error=error,
                operation="archive_issue",
                entity_type="issue",
                entity_id="issue-123",
                additional_context={"archive_path": "/tmp/archive"},
            )

            mock_logger.error.assert_called_once()
            call_args = mock_logger.error.call_args
            assert call_args[0][0] == "operation_failed"
            assert call_args[1]["operation"] == "archive_issue"
            assert call_args[1]["archive_path"] == "/tmp/archive"

    def test_cli_command_error_logging(self):
        """Test that CLI commands log errors with context."""
        error = ValidationError("Missing required argument")

        with patch("roadmap.common.logging.error_logging.logger") as mock_logger:
            log_error_with_context(
                error=error,
                operation="list_issues",
                additional_context={"command": "list", "args": ["--filter", "open"]},
            )

            mock_logger.error.assert_called_once()
            call_args = mock_logger.error.call_args
            assert call_args[1]["command"] == "list"
            assert call_args[1]["args"] == ["--filter", "open"]

    def test_github_handler_error_logging(self):
        """Test that GitHub handlers log errors properly."""
        error = GitHubAPIError("Rate limit exceeded")

        with patch("roadmap.common.logging.error_logging.logger") as mock_logger:
            log_error_with_context(
                error=error,
                operation="get_issues",
                entity_type="repository",
                entity_id="owner/repo",
                additional_context={"api_endpoint": "GET /repos/{owner}/{repo}/issues"},
            )

            mock_logger.error.assert_called_once()
            call_args = mock_logger.error.call_args
            assert call_args[1]["entity_id"] == "owner/repo"
            assert "api_endpoint" in call_args[1]

    def test_database_error_logging(self):
        """Test that database errors are logged with context."""
        error = RuntimeError("Database connection lost")

        with patch("roadmap.common.logging.error_logging.logger") as mock_logger:
            log_error_with_context(
                error=error,
                operation="save_issue",
                entity_type="issue",
                entity_id="issue-456",
                additional_context={"table": "issues", "operation_type": "insert"},
            )

            mock_logger.error.assert_called_once()
            call_args = mock_logger.error.call_args
            assert call_args[1]["table"] == "issues"
            assert call_args[1]["operation_type"] == "insert"


class TestErrorLoggingRecovery:
    """Test error logging in recovery scenarios."""

    def test_log_retry_attempt(self):
        """Test logging retry attempts."""
        error = TimeoutError("Request timed out")

        with patch("roadmap.common.logging.error_logging.logger") as mock_logger:
            log_error_with_context(
                error=error,
                operation="fetch_github_data",
                additional_context={"attempt": 1, "max_attempts": 3},
            )

            mock_logger.error.assert_called_once()
            call_args = mock_logger.error.call_args
            assert call_args[1]["attempt"] == 1
            assert call_args[1]["max_attempts"] == 3

    def test_log_fallback_action(self):
        """Test logging fallback actions."""
        error = NetworkError("Network unreachable")

        with patch("roadmap.common.logging.error_logging.logger") as mock_logger:
            log_error_with_context(
                error=error,
                operation="sync_with_github",
                additional_context={"fallback_action": "use_local_cache"},
            )

            mock_logger.error.assert_called_once()
            call_args = mock_logger.error.call_args
            assert call_args[1]["fallback_action"] == "use_local_cache"

    def test_log_partial_success(self):
        """Test logging partial success with errors."""
        error = ValidationError("Some items failed validation")

        with patch("roadmap.common.logging.error_logging.logger") as mock_logger:
            log_error_with_context(
                error=error,
                operation="bulk_update_issues",
                additional_context={
                    "total": 100,
                    "succeeded": 95,
                    "failed": 5,
                },
            )

            mock_logger.error.assert_called_once()
            call_args = mock_logger.error.call_args
            assert call_args[1]["total"] == 100
            assert call_args[1]["succeeded"] == 95
            assert call_args[1]["failed"] == 5
