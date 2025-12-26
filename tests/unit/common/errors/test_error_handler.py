"""Tests for error handling utilities."""

import logging

import pytest

from roadmap.common.errors.error_base import (
    ErrorCategory,
    ErrorSeverity,
    RoadmapError,
)
from roadmap.common.errors.error_handler import ErrorHandler, handle_errors


class TestErrorHandler:
    """Tests for ErrorHandler class."""

    @pytest.fixture
    def handler(self):
        """Create error handler with mock logger and console."""
        logger = logging.getLogger("test")
        return ErrorHandler(logger=logger)

    @pytest.fixture
    def roadmap_error(self):
        """Create a test RoadmapError."""
        return RoadmapError(
            "Test error",
            severity=ErrorSeverity.MEDIUM,
            category=ErrorCategory.VALIDATION,
        )

    def test_handler_initialization(self):
        """Test ErrorHandler initialization."""
        handler = ErrorHandler()
        assert handler.logger is not None
        assert handler.console is not None
        assert handler.error_counts == {}

    def test_handle_regular_exception(self, handler):
        """Test handling of regular Python exceptions."""
        error = ValueError("Something went wrong")
        result = handler.handle_error(error, exit_on_critical=False)

        assert result is True
        assert ErrorCategory.VALIDATION in handler.error_counts

    def test_handle_roadmap_error(self, handler, roadmap_error):
        """Test handling of RoadmapError."""
        result = handler.handle_error(roadmap_error, exit_on_critical=False)

        assert result is True
        assert handler.error_counts[ErrorCategory.VALIDATION] == 1

    def test_error_counts_accumulate(self, handler, roadmap_error):
        """Test that error counts accumulate."""
        handler.handle_error(roadmap_error, exit_on_critical=False)
        handler.handle_error(roadmap_error, exit_on_critical=False)

        assert handler.error_counts[ErrorCategory.VALIDATION] == 2

    def test_handle_error_with_context(self, handler, roadmap_error):
        """Test error handling with context information."""
        context = {"file": "test.md", "line": 10}
        result = handler.handle_error(
            roadmap_error, context=context, exit_on_critical=False
        )

        assert result is True

    def test_critical_error_exits(self, handler):
        """Test that critical errors cause exit."""
        critical_error = RoadmapError(
            "Critical error",
            severity=ErrorSeverity.CRITICAL,
            category=ErrorCategory.FILE_OPERATION,
        )

        with pytest.raises(SystemExit):
            handler.handle_error(critical_error, exit_on_critical=True)

    def test_critical_error_no_exit_when_disabled(self, handler):
        """Test that critical errors don't exit when exit_on_critical=False."""
        critical_error = RoadmapError(
            "Critical error",
            severity=ErrorSeverity.CRITICAL,
            category=ErrorCategory.FILE_OPERATION,
        )

        result = handler.handle_error(critical_error, exit_on_critical=False)
        assert result is True

    @pytest.mark.parametrize(
        "severity",
        [
            ErrorSeverity.CRITICAL,
            ErrorSeverity.HIGH,
            ErrorSeverity.MEDIUM,
            ErrorSeverity.LOW,
            ErrorSeverity.WARNING,
            ErrorSeverity.INFO,
        ],
    )
    def test_handle_various_severity_levels(self, handler, severity):
        """Test handling errors of different severity levels."""
        error = RoadmapError(
            f"Test {severity.value} error",
            severity=severity,
            category=ErrorCategory.VALIDATION,
        )

        result = handler.handle_error(error, exit_on_critical=False)
        assert result is True

    def test_get_error_summary(self, handler, roadmap_error):
        """Test error summary generation."""
        handler.handle_error(roadmap_error, exit_on_critical=False)
        handler.handle_error(roadmap_error, exit_on_critical=False)

        summary = handler.get_error_summary()
        assert summary[ErrorCategory.VALIDATION.value] == 2

    def test_error_with_cause(self, handler):
        """Test error handling with cause chain."""
        cause = ValueError("Original error")
        error = RoadmapError(
            "Wrapped error",
            severity=ErrorSeverity.HIGH,
            category=ErrorCategory.FILE_OPERATION,
            cause=cause,
        )

        result = handler.handle_error(error, exit_on_critical=False)
        assert result is True

    def test_handle_error_with_traceback(self, handler, roadmap_error):
        """Test error handling with traceback display."""
        result = handler.handle_error(
            roadmap_error, show_traceback=True, exit_on_critical=False
        )
        assert result is True


class TestHandleErrorsContextManager:
    """Tests for handle_errors context manager."""

    def test_successful_block_execution(self):
        """Test context manager with successful execution."""
        with handle_errors() as handler:
            # Should execute without error
            pass

        # Handler should exist and have no errors
        assert isinstance(handler, ErrorHandler)

    def test_context_manager_catches_roadmap_error(self):
        """Test context manager catching RoadmapError."""
        error = RoadmapError(
            "Test error",
            severity=ErrorSeverity.MEDIUM,
            category=ErrorCategory.VALIDATION,
        )

        with handle_errors(ignore_errors=False, exit_on_critical=False):
            raise error

    def test_context_manager_catches_regular_exception(self):
        """Test context manager catching regular exceptions."""
        with handle_errors(ignore_errors=True, exit_on_critical=False):
            raise ValueError("Test error")

    def test_context_manager_ignores_errors(self):
        """Test context manager ignoring errors."""
        error = RoadmapError(
            "Test error",
            severity=ErrorSeverity.LOW,
            category=ErrorCategory.VALIDATION,
        )

        # Should not raise when ignore_errors=True
        with handle_errors(ignore_errors=True):
            raise error

    def test_context_manager_critical_error_raises(self):
        """Test context manager re-raising critical errors."""
        critical_error = RoadmapError(
            "Critical error",
            severity=ErrorSeverity.CRITICAL,
            category=ErrorCategory.FILE_OPERATION,
        )

        with pytest.raises(RoadmapError):
            with handle_errors(ignore_errors=False, exit_on_critical=False):
                raise critical_error

    def test_context_manager_with_custom_handler(self):
        """Test context manager with custom error handler."""
        custom_handler = ErrorHandler()

        with handle_errors(error_handler=custom_handler, exit_on_critical=False) as h:
            assert h is custom_handler

    def test_context_manager_with_context_info(self):
        """Test context manager passing context information."""
        context = {"operation": "test"}

        with handle_errors(context=context, exit_on_critical=False):
            pass

    def test_context_manager_non_roadmap_error(self):
        """Test context manager wrapping non-RoadmapError exceptions."""
        with handle_errors(ignore_errors=True, exit_on_critical=False):
            raise RuntimeError("Generic error")
