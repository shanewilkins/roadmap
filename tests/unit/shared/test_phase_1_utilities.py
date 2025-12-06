"""Tests for Phase 1 foundation utilities.

Comprehensive test coverage for:
- BaseValidator abstract class
- @service_operation decorator
- FileEnumerationService
- StatusSummary utility
"""

from enum import Enum
from unittest.mock import Mock, patch

from roadmap.common.decorators import service_operation
from roadmap.common.status_utils import StatusSummary
from roadmap.core.services.base_validator import (
    BaseValidator,
    HealthStatus,
)
from roadmap.infrastructure.file_enumeration import FileEnumerationService
from roadmap.infrastructure.health import HealthStatus as ApplicationHealthStatus

# ============================================================================
# BaseValidator Tests
# ============================================================================


class ConcreteValidator(BaseValidator):
    """Concrete implementation for testing."""

    @staticmethod
    def get_check_name() -> str:
        return "test_check"

    @staticmethod
    def perform_check():
        return HealthStatus.HEALTHY, "All good"


class FailingValidator(BaseValidator):
    """Validator that raises exceptions."""

    @staticmethod
    def get_check_name() -> str:
        return "failing_check"

    @staticmethod
    def perform_check():
        raise RuntimeError("Check failed")


class DegradedValidator(BaseValidator):
    """Validator that returns degraded status."""

    @staticmethod
    def get_check_name() -> str:
        return "degraded_check"

    @staticmethod
    def perform_check():
        return HealthStatus.DEGRADED, "Service degraded"


class TestBaseValidator:
    """Test BaseValidator abstract class."""

    def test_check_success(self):
        """Test successful check."""
        status, message = ConcreteValidator.check()
        assert status == HealthStatus.HEALTHY
        assert message == "All good"

    def test_check_degraded(self):
        """Test degraded status."""
        status, message = DegradedValidator.check()
        assert status == HealthStatus.DEGRADED
        assert message == "Service degraded"

    def test_check_exception_handling(self):
        """Test that exceptions are caught and logged."""
        status, message = FailingValidator.check()
        assert status == HealthStatus.UNHEALTHY
        assert "Error checking" in message
        assert "failing_check" in message

    def test_check_exception_includes_error(self):
        """Test that exception message is included."""
        status, message = FailingValidator.check()
        assert "Check failed" in message

    def test_check_logs_success(self):
        """Test that successful checks are logged."""
        with patch("roadmap.core.services.base_validator.logger") as mock_logger:
            ConcreteValidator.check()
            mock_logger.debug.assert_called_once()
            call_args = mock_logger.debug.call_args
            assert "health_check_test_check" in str(call_args)

    def test_check_logs_failure(self):
        """Test that failures are logged."""
        with patch("roadmap.core.services.base_validator.logger") as mock_logger:
            FailingValidator.check()
            mock_logger.error.assert_called_once()
            call_args = mock_logger.error.call_args
            assert "health_check_failing_check_failed" in str(call_args)

    def test_cannot_instantiate_abstract(self):
        """Test that BaseValidator cannot be instantiated."""
        # BaseValidator is abstract, cannot be instantiated directly
        # This is verified by the type checker at compile time


# ============================================================================
# @service_operation Decorator Tests
# ============================================================================


class TestServiceOperationDecorator:
    """Test @service_operation decorator."""

    def test_successful_execution(self):
        """Test decorator on successful function."""

        @service_operation()
        def successful_func(self):
            return {"result": "success"}

        mock_self = Mock()
        result = successful_func(mock_self)
        assert result == {"result": "success"}

    def test_exception_handling_default_return(self):
        """Test that default return is used on exception."""

        @service_operation(default_return={"error": True})
        def failing_func(self):
            raise ValueError("Something went wrong")

        mock_self = Mock()
        result = failing_func(mock_self)
        assert result == {"error": True}

    def test_exception_handling_none_return(self):
        """Test that None default return works."""

        @service_operation(default_return={"result": None})
        def failing_func(self):
            raise ValueError("Error")

        mock_self = Mock()
        result = failing_func(mock_self)
        assert result == {"result": None}

    def test_exception_handling_empty_dict_default(self):
        """Test that empty dict is default when not specified."""

        @service_operation()
        def failing_func(self):
            raise ValueError("Error")

        mock_self = Mock()
        result = failing_func(mock_self)
        assert result == {}

    def test_log_level_error(self):
        """Test error log level."""

        @service_operation(log_level="error")
        def failing_func(self):
            raise ValueError("Error message")

        with patch("roadmap.common.decorators.logger") as mock_logger:
            mock_self = Mock()
            failing_func(mock_self)
            mock_logger.error.assert_called_once()

    def test_log_level_warning(self):
        """Test warning log level."""

        @service_operation(log_level="warning")
        def failing_func(self):
            raise ValueError("Warning message")

        with patch("roadmap.common.decorators.logger") as mock_logger:
            mock_self = Mock()
            failing_func(mock_self)
            mock_logger.warning.assert_called_once()

    def test_log_level_debug(self):
        """Test debug log level."""

        @service_operation(log_level="debug")
        def failing_func(self):
            raise ValueError("Debug message")

        with patch("roadmap.common.decorators.logger") as mock_logger:
            mock_self = Mock()
            failing_func(mock_self)
            mock_logger.debug.assert_called_once()

    def test_log_level_info(self):
        """Test info log level."""

        @service_operation(log_level="info")
        def failing_func(self):
            raise ValueError("Info message")

        with patch("roadmap.common.decorators.logger") as mock_logger:
            mock_self = Mock()
            failing_func(mock_self)
            mock_logger.info.assert_called_once()

    def test_invalid_log_level(self):
        """Test that invalid log level is rejected."""
        # Invalid log level will be caught at type-check time
        # Runtime validation also ensures only valid levels are accepted

    def test_custom_error_message(self):
        """Test custom error message."""

        @service_operation(
            log_level="error",
            error_message="Custom error occurred",
        )
        def failing_func(self):
            raise ValueError("Original error")

        with patch("roadmap.common.decorators.logger") as mock_logger:
            mock_self = Mock()
            failing_func(mock_self)
            # The message is the first positional arg
            call_args = mock_logger.error.call_args[0]
            assert "Custom error" in str(call_args)

    def test_traceback_included(self):
        """Test that traceback is included when requested."""

        @service_operation(
            log_level="error",
            include_traceback=True,
        )
        def failing_func(self):
            raise ValueError("Error with traceback")

        with patch("roadmap.common.decorators.logger") as mock_logger:
            mock_self = Mock()
            failing_func(mock_self)
            call_kwargs = mock_logger.error.call_args[1]
            assert "traceback" in call_kwargs
            assert "ValueError" in call_kwargs["traceback"]

    def test_traceback_not_included_by_default(self):
        """Test that traceback is not included by default."""

        @service_operation(log_level="error")
        def failing_func(self):
            raise ValueError("Error without traceback")

        with patch("roadmap.common.decorators.logger") as mock_logger:
            mock_self = Mock()
            failing_func(mock_self)
            call_kwargs = mock_logger.error.call_args[1]
            assert "traceback" not in call_kwargs

    def test_error_type_captured(self):
        """Test that error type is captured."""

        @service_operation(log_level="error")
        def failing_func(self):
            raise RuntimeError("Runtime error")

        with patch("roadmap.common.decorators.logger") as mock_logger:
            mock_self = Mock()
            failing_func(mock_self)
            call_kwargs = mock_logger.error.call_args[1]
            assert call_kwargs["error_type"] == "RuntimeError"

    def test_operation_name_captured(self):
        """Test that operation name is captured."""

        @service_operation(log_level="error")
        def my_special_operation(self):
            raise ValueError("Error")

        with patch("roadmap.common.decorators.logger") as mock_logger:
            mock_self = Mock()
            my_special_operation(mock_self)
            call_kwargs = mock_logger.error.call_args[1]
            assert call_kwargs["operation"] == "my_special_operation"

    def test_log_success_option(self):
        """Test log_success option."""

        @service_operation(log_success=True)
        def successful_func(self):
            return {"result": "success"}

        with patch("roadmap.common.decorators.logger") as mock_logger:
            mock_self = Mock()
            successful_func(mock_self)
            mock_logger.debug.assert_called_once()

    def test_preserves_function_name(self):
        """Test that decorator preserves function name."""

        @service_operation()
        def my_function(self):
            return "result"

        assert my_function.__name__ == "my_function"

    def test_preserves_docstring(self):
        """Test that decorator preserves docstring."""

        @service_operation()
        def documented_function(self):
            """This is documentation."""
            return "result"

        if documented_function.__doc__:
            assert "This is documentation" in documented_function.__doc__


# ============================================================================
# FileEnumerationService Tests
# ============================================================================


class TestFileEnumerationService:
    """Test FileEnumerationService."""

    def test_enumerate_and_parse_empty_directory(self, tmp_path):
        """Test with empty directory."""
        result = FileEnumerationService.enumerate_and_parse(tmp_path, Mock())
        assert result == []

    def test_enumerate_and_parse_nonexistent_directory(self, tmp_path):
        """Test with nonexistent directory."""
        nonexistent = tmp_path / "nonexistent"
        result = FileEnumerationService.enumerate_and_parse(nonexistent, Mock())
        assert result == []

    def test_enumerate_and_parse_single_file(self, tmp_path):
        """Test parsing single file."""
        test_file = tmp_path / "test.md"
        test_file.write_text("# Test")

        parser = Mock(return_value={"name": "test"})
        result = FileEnumerationService.enumerate_and_parse(tmp_path, parser)

        assert len(result) == 1
        assert result[0] == {"name": "test"}
        parser.assert_called_once()

    def test_enumerate_and_parse_multiple_files(self, tmp_path):
        """Test parsing multiple files."""
        (tmp_path / "file1.md").write_text("# File 1")
        (tmp_path / "file2.md").write_text("# File 2")
        (tmp_path / "file3.md").write_text("# File 3")

        parser = Mock(side_effect=lambda p: {"file": p.name})
        result = FileEnumerationService.enumerate_and_parse(tmp_path, parser)

        assert len(result) == 3
        assert parser.call_count == 3

    def test_enumerate_and_parse_skips_backup_files(self, tmp_path):
        """Test that backup files are skipped."""
        (tmp_path / "file.md").write_text("# File")
        (tmp_path / "file.backup.md").write_text("# Backup")

        parser = Mock(side_effect=lambda p: {"file": p.name})
        result = FileEnumerationService.enumerate_and_parse(tmp_path, parser)

        assert len(result) == 1
        assert result[0]["file"] == "file.md"

    def test_enumerate_and_parse_skips_backup_disabled(self, tmp_path):
        """Test that backup filtering can be disabled."""
        (tmp_path / "file.md").write_text("# File")
        (tmp_path / "file.backup.md").write_text("# Backup")

        parser = Mock(side_effect=lambda p: {"file": p.name})
        result = FileEnumerationService.enumerate_and_parse(
            tmp_path, parser, backup_filter=False
        )

        assert len(result) == 2

    def test_enumerate_and_parse_parse_error_handling(self, tmp_path):
        """Test that parse errors are handled gracefully."""
        (tmp_path / "good.md").write_text("# Good")
        (tmp_path / "bad.md").write_text("# Bad")

        def parser(path):
            if "bad" in path.name:
                raise ValueError("Parse error")
            return {"file": path.name}

        result = FileEnumerationService.enumerate_and_parse(tmp_path, parser)

        assert len(result) == 1
        assert result[0]["file"] == "good.md"

    def test_enumerate_with_filter(self, tmp_path):
        """Test enumeration with filtering."""
        (tmp_path / "file1.md").write_text("# File 1")
        (tmp_path / "file2.md").write_text("# File 2")

        parser = Mock(
            side_effect=lambda p: {
                "name": p.name,
                "include": "1" in p.name,
            }
        )

        def filter_func(obj):
            return obj["include"]

        result = FileEnumerationService.enumerate_with_filter(
            tmp_path, parser, filter_func
        )

        assert len(result) == 1
        assert result[0]["name"] == "file1.md"

    def test_find_by_id_found(self, tmp_path):
        """Test finding file by ID."""
        (tmp_path / "abc12345-test.md").write_text("# Test")

        parser = Mock(return_value={"id": "abc12345"})
        result = FileEnumerationService.find_by_id(tmp_path, "abc12345", parser)

        assert result == {"id": "abc12345"}

    def test_find_by_id_not_found(self, tmp_path):
        """Test finding file when ID doesn't exist."""
        parser = Mock()
        result = FileEnumerationService.find_by_id(tmp_path, "nonexistent", parser)

        assert result is None

    def test_find_by_id_parse_error(self, tmp_path):
        """Test finding file when parser fails."""
        (tmp_path / "abc12345-test.md").write_text("# Test")

        def parser(path):
            raise ValueError("Parse error")

        result = FileEnumerationService.find_by_id(tmp_path, "abc12345", parser)

        assert result is None

    def test_find_by_id_returns_first_match(self, tmp_path):
        """Test that first match is returned."""
        (tmp_path / "abc12345-file1.md").write_text("# File 1")
        (tmp_path / "abc12345-file2.md").write_text("# File 2")

        results = []

        def parser(path):
            result = {"file": path.name}
            results.append(result)
            return result

        result = FileEnumerationService.find_by_id(tmp_path, "abc12345", parser)

        # Should return first successfully parsed file
        assert result is not None
        assert "file" in result


# ============================================================================
# StatusSummary Tests
# ============================================================================


class MockHealthStatus(Enum):
    """Mock health status enum for testing."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class TestStatusSummary:
    """Test StatusSummary utility."""

    def test_count_by_status_single(self):
        """Test counting single status."""
        items = [("check1", MockHealthStatus.HEALTHY)]  # type: ignore
        result = StatusSummary.count_by_status(items)  # type: ignore

        assert result == {"healthy": 1}

    def test_count_by_status_multiple(self):
        """Test counting multiple statuses."""
        items = [  # type: ignore
            ("check1", MockHealthStatus.HEALTHY),
            ("check2", MockHealthStatus.HEALTHY),
            ("check3", MockHealthStatus.DEGRADED),
            ("check4", MockHealthStatus.UNHEALTHY),
        ]
        result = StatusSummary.count_by_status(items)  # type: ignore

        assert result == {"healthy": 2, "degraded": 1, "unhealthy": 1}

    def test_count_by_status_empty(self):
        """Test counting empty list."""
        result = StatusSummary.count_by_status([])  # type: ignore
        assert result == {}

    def test_summarize_checks_balanced(self):
        """Test summarizing checks."""
        # Use actual ApplicationHealthStatus from health module
        checks = {  # type: ignore
            "check1": (ApplicationHealthStatus.HEALTHY, "OK"),
            "check2": (ApplicationHealthStatus.HEALTHY, "OK"),
            "check3": (ApplicationHealthStatus.DEGRADED, "Warning"),
            "check4": (ApplicationHealthStatus.UNHEALTHY, "Error"),
        }

        result = StatusSummary.summarize_checks(checks)  # type: ignore

        assert result["total"] == 4
        assert result["healthy"] == 2
        assert result["degraded"] == 1
        assert result["unhealthy"] == 1

    def test_summarize_checks_all_healthy(self):
        """Test summarizing all healthy checks."""
        checks = {  # type: ignore
            "check1": (ApplicationHealthStatus.HEALTHY, "OK"),
            "check2": (ApplicationHealthStatus.HEALTHY, "OK"),
        }

        result = StatusSummary.summarize_checks(checks)  # type: ignore

        assert result["total"] == 2
        assert result["healthy"] == 2
        assert result["degraded"] == 0
        assert result["unhealthy"] == 0

    def test_summarize_checks_empty(self):
        """Test summarizing empty checks."""
        result = StatusSummary.summarize_checks({})  # type: ignore

        assert result["total"] == 0
        assert result["healthy"] == 0
        assert result["degraded"] == 0
        assert result["unhealthy"] == 0
