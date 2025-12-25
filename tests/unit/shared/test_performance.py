"""Unit tests for performance monitoring module."""

import time
from unittest.mock import MagicMock, patch

import pytest

from roadmap.common.performance import timed_operation


class TestTimedOperation:
    """Test timed_operation decorator."""

    def test_successful_operation_timing(self):
        """Test timing a successful operation."""

        @timed_operation("test_op")
        def sample_func():
            time.sleep(0.01)
            return "result"

        result = sample_func()
        assert result == "result"

    def test_operation_with_arguments(self):
        """Test timed operation with function arguments."""

        @timed_operation("add_numbers")
        def add_numbers(a, b):
            return a + b

        result = add_numbers(2, 3)
        assert result == 5

    def test_operation_with_kwargs(self):
        """Test timed operation with keyword arguments."""

        @timed_operation("greeting")
        def greet(name, greeting="Hello"):
            return f"{greeting}, {name}!"

        result = greet("Alice", greeting="Hi")
        assert result == "Hi, Alice!"

    def test_operation_default_name(self):
        """Test that operation name defaults to function name."""

        @timed_operation()
        def my_function():
            return "result"

        with patch("roadmap.common.performance.logger") as mock_logger:
            result = my_function()
            assert result == "result"
            # Check that logger was called with function name
            assert any(
                call[1].get("operation") == "my_function"
                for call in mock_logger.info.call_args_list
            )

    def test_operation_with_exception(self):
        """Test timed operation when exception is raised."""

        @timed_operation("failing_op")
        def failing_func():
            raise ValueError("Test error")

        with pytest.raises(ValueError, match="Test error"):
            failing_func()

    def test_operation_exception_still_logs(self):
        """Test that timing is logged even when exception occurs."""

        @timed_operation("error_op")
        def error_func():
            raise RuntimeError("Error")

        with patch("roadmap.common.performance.logger") as mock_logger:
            with pytest.raises(RuntimeError):
                error_func()
            # Check that error was logged
            mock_logger.error.assert_called_once()

    def test_operation_disables_metric_recording(self):
        """Test disabling metric recording."""

        @timed_operation("no_metric_op", record_metric=False)
        def no_metric_func():
            return "result"

        with patch(
            "roadmap.common.performance.get_metrics_collector"
        ) as mock_collector:
            result = no_metric_func()
            assert result == "result"
            # Collector should not be called
            mock_collector.assert_not_called()

    def test_operation_records_metric(self):
        """Test that metrics are recorded."""
        with patch(
            "roadmap.common.performance.get_metrics_collector"
        ) as mock_collector:
            mock_instance = MagicMock()
            mock_collector.return_value = mock_instance

            @timed_operation("metric_op", record_metric=True)
            def metric_func():
                return "result"

            result = metric_func()
            assert result == "result"
            # Verify collector was called
            mock_instance.record.assert_called_once()

    def test_operation_preserves_function_metadata(self):
        """Test that decorator preserves function metadata."""

        @timed_operation("test")
        def documented_func():
            """Original docstring."""
            return "result"

        assert documented_func.__name__ == "documented_func"
        assert documented_func.__doc__ is not None
        assert "Original docstring" in documented_func.__doc__

    def test_operation_with_complex_return_value(self):
        """Test timed operation with complex return value."""

        @timed_operation("complex_op")
        def complex_func():
            return {"key": "value", "list": [1, 2, 3]}

        result = complex_func()
        assert result == {"key": "value", "list": [1, 2, 3]}

    def test_operation_timing_accuracy(self):
        """Test that operation timing is reasonably accurate."""

        @timed_operation("timing_op")
        def timed_func():
            time.sleep(0.01)
            return "result"

        with patch("roadmap.common.performance.logger") as mock_logger:
            result = timed_func()
            assert result == "result"
            # Check that timing was logged
            call_args = mock_logger.info.call_args_list[0]
            duration_ms = call_args[1].get("duration_ms", 0)
            # Should be roughly 10ms (allow for some variance)
            assert 5 < duration_ms < 50


class TestMetricsCollection:
    """Test metrics collection integration."""

    def test_operation_metric_recording(self):
        """Test that operation metrics are properly formatted."""
        from roadmap.common.metrics import OperationMetric

        metric = OperationMetric(
            operation="test_op",
            duration_ms=123.45,
            success=True,
            error=None,
        )
        assert metric.operation == "test_op"
        assert metric.duration_ms == 123.45
        assert metric.success
        assert metric.error is None

    def test_operation_metric_with_error(self):
        """Test that operation metrics capture errors."""
        from roadmap.common.metrics import OperationMetric

        metric = OperationMetric(
            operation="failed_op",
            duration_ms=50.0,
            success=False,
            error="Connection timeout",
        )
        assert metric.operation == "failed_op"
        assert not metric.success
        assert metric.error == "Connection timeout"
