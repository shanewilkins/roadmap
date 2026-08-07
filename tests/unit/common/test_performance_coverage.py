"""Test coverage for performance module."""

import asyncio
import time
from unittest.mock import MagicMock, patch

import pytest

from roadmap.common.services import (
    OperationTimer,
    async_timed_operation,
    timed_operation,
)


class TestTimedOperationDecorator:
    """Test the timed_operation decorator."""

    def test_timed_operation_completes_successfully(self):
        """Test timed operation completes and returns result."""

        @timed_operation("test_op")
        def func():
            return "success"

        result = func()
        assert result == "success"

    def test_timed_operation_measures_duration(self):
        """Test timed operation measures execution time."""

        @timed_operation("test_op", record_metric=False)
        def func():
            time.sleep(0.05)
            return "done"

        result = func()
        assert result == "done"

    def test_timed_operation_with_custom_name(self):
        """Test timed operation with custom operation name."""
        with patch("roadmap.common.services.performance.logger"):

            @timed_operation("custom_operation", record_metric=False)
            def func():
                return "result"

            result = func()
            assert result == "result"

    def test_timed_operation_logs_execution(self):
        """Test timed operation logs execution."""
        with patch("roadmap.common.services.performance.logger") as mock_logger:

            @timed_operation("test_op", record_metric=False)
            def func():
                return "success"

            result = func()
            assert result == "success"
            mock_logger.info.assert_called()

    def test_timed_operation_logs_error(self):
        """Test timed operation logs errors."""
        with patch("roadmap.common.services.performance.logger") as mock_logger:

            @timed_operation("test_op", record_metric=False)
            def func():
                raise ValueError("test error")

            with pytest.raises(ValueError):
                func()

            mock_logger.error.assert_called()

    def test_timed_operation_reraises_exception(self):
        """Test timed operation re-raises exceptions."""

        @timed_operation("test_op", record_metric=False)
        def func():
            raise ValueError("error")

        with pytest.raises(ValueError):
            func()

    def test_timed_operation_with_args_and_kwargs(self):
        """Test timed operation with function arguments."""

        @timed_operation("test_op", record_metric=False)
        def func(a, b, c=None):
            return f"{a}-{b}-{c}"

        result = func(1, 2, c=3)
        assert result == "1-2-3"

    def test_timed_operation_preserves_function_metadata(self):
        """Test timed operation preserves function metadata."""

        @timed_operation("test_op")
        def my_function():
            """My docstring."""
            return "result"

        assert my_function.__name__ == "my_function"
        assert my_function.__doc__ is not None and "My docstring" in my_function.__doc__

    def test_timed_operation_uses_default_name(self):
        """Test timed operation uses function name when not provided."""
        with patch("roadmap.common.services.performance.logger") as mock_logger:

            @timed_operation(record_metric=False)
            def my_function():
                return "result"

            my_function()
            # Should log with function name
            mock_logger.info.assert_called()
            call_args = mock_logger.info.call_args
            assert "my_function" in str(call_args)

    def test_timed_operation_returns_none(self):
        """Test timed operation with function returning None."""

        @timed_operation("test_op", record_metric=False)
        def func():
            return None

        result = func()
        assert result is None

    def test_timed_operation_with_record_metric_true(self):
        """Test timed operation records metric when enabled."""
        with patch(
            "roadmap.common.services.performance.get_metrics_collector"
        ) as mock_collector:
            mock_instance = MagicMock()
            mock_collector.return_value = mock_instance

            @timed_operation("test_op", record_metric=True)
            def func():
                return "result"

            result = func()
            assert result == "result"
            mock_instance.record.assert_called()

    def test_timed_operation_records_success_metric(self):
        """Test timed operation records successful execution metric."""
        with patch(
            "roadmap.common.services.performance.get_metrics_collector"
        ) as mock_collector:
            mock_instance = MagicMock()
            mock_collector.return_value = mock_instance

            @timed_operation("test_op", record_metric=True)
            def func():
                return "success"

            func()

            # Verify metric was recorded with success=True
            call_args = mock_instance.record.call_args
            metric = call_args[0][0]
            assert metric.success

    def test_timed_operation_records_failure_metric(self):
        """Test timed operation records failure metric."""
        with patch(
            "roadmap.common.services.performance.get_metrics_collector"
        ) as mock_collector:
            mock_instance = MagicMock()
            mock_collector.return_value = mock_instance

            @timed_operation("test_op", record_metric=True)
            def func():
                raise ValueError("error")

            with pytest.raises(ValueError):
                func()

            # Verify metric was recorded with success=False
            call_args = mock_instance.record.call_args
            metric = call_args[0][0]
            assert not metric.success


class TestAsyncTimedOperationDecorator:
    """Test the async_timed_operation decorator."""

    @pytest.mark.asyncio
    async def test_async_timed_operation_completes_successfully(self):
        """Test async timed operation completes."""

        @async_timed_operation("async_op", record_metric=False)
        async def func():
            return "success"

        result = await func()
        assert result == "success"

    @pytest.mark.asyncio
    async def test_async_timed_operation_with_delay(self):
        """Test async timed operation with delay."""

        @async_timed_operation("async_op", record_metric=False)
        async def func():
            await asyncio.sleep(0.01)
            return "done"

        result = await func()
        assert result == "done"

    @pytest.mark.asyncio
    async def test_async_timed_operation_logs_execution(self):
        """Test async timed operation logs."""
        with patch("roadmap.common.services.performance.logger") as mock_logger:

            @async_timed_operation("async_op", record_metric=False)
            async def func():
                return "success"

            result = await func()
            assert result == "success"
            mock_logger.info.assert_called()

    @pytest.mark.asyncio
    async def test_async_timed_operation_logs_error(self):
        """Test async timed operation logs errors."""
        with patch("roadmap.common.services.performance.logger") as mock_logger:

            @async_timed_operation("async_op", record_metric=False)
            async def func():
                raise ValueError("async error")

            with pytest.raises(ValueError):
                await func()

            mock_logger.error.assert_called()

    @pytest.mark.asyncio
    async def test_async_timed_operation_reraises_exception(self):
        """Test async timed operation re-raises exceptions."""

        @async_timed_operation("async_op", record_metric=False)
        async def func():
            raise RuntimeError("error")

        with pytest.raises(RuntimeError):
            await func()

    @pytest.mark.asyncio
    async def test_async_timed_operation_with_args(self):
        """Test async timed operation with arguments."""

        @async_timed_operation("async_op", record_metric=False)
        async def func(a, b):
            return f"{a}-{b}"

        result = await func(1, 2)
        assert result == "1-2"

    @pytest.mark.asyncio
    async def test_async_timed_operation_records_metric(self):
        """Test async timed operation records metric."""
        with patch(
            "roadmap.common.services.performance.get_metrics_collector"
        ) as mock_collector:
            mock_instance = MagicMock()
            mock_collector.return_value = mock_instance

            @async_timed_operation("async_op", record_metric=True)
            async def func():
                return "success"

            await func()
            mock_instance.record.assert_called()


class TestOperationTimer:
    """Test the OperationTimer context manager."""

    def test_operation_timer_measures_duration(self):
        """Test OperationTimer measures execution time."""
        with OperationTimer("test_op", record_metric=False) as timer:
            time.sleep(0.05)

        assert timer.duration_ms is not None
        assert timer.duration_ms >= 50  # At least 50ms

    def test_operation_timer_tracks_success(self):
        """Test OperationTimer tracks successful execution."""
        with OperationTimer("test_op", record_metric=False) as timer:
            pass

        assert timer.error is None
        assert timer.start_time is not None
        assert timer.end_time is not None
        assert timer.duration_ms is not None

    def test_operation_timer_tracks_exception(self):
        """Test OperationTimer tracks exceptions."""
        try:
            with OperationTimer("test_op", record_metric=False) as timer:
                raise ValueError("test error")
        except ValueError:
            pass

        assert timer.error is not None
        assert isinstance(timer.error, ValueError)
        assert timer.duration_ms is not None

    def test_operation_timer_logs_start(self):
        """Test OperationTimer logs operation start."""
        with patch("roadmap.common.services.performance.logger") as mock_logger:
            with OperationTimer("test_op", record_metric=False):
                pass

            mock_logger.debug.assert_called()

    def test_operation_timer_logs_completion(self):
        """Test OperationTimer logs completion."""
        with patch("roadmap.common.services.performance.logger") as mock_logger:
            with OperationTimer("test_op", record_metric=False):
                pass

            # Should have info log for completion
            mock_logger.info.assert_called()

    def test_operation_timer_logs_error(self):
        """Test OperationTimer logs errors."""
        with patch("roadmap.common.services.performance.logger") as mock_logger:
            try:
                with OperationTimer("test_op", record_metric=False):
                    raise ValueError("error")
            except ValueError:
                pass

            mock_logger.error.assert_called()

    def test_operation_timer_records_metric(self):
        """Test OperationTimer records metric."""
        with patch(
            "roadmap.common.services.performance.get_metrics_collector"
        ) as mock_collector:
            mock_instance = MagicMock()
            mock_collector.return_value = mock_instance

            with OperationTimer("test_op", record_metric=True):
                pass

            mock_instance.record.assert_called()

    def test_operation_timer_with_nested_context(self):
        """Test nested OperationTimer contexts."""
        with OperationTimer("outer", record_metric=False) as outer:
            with OperationTimer("inner", record_metric=False) as inner:
                time.sleep(0.01)

            assert inner.duration_ms is not None

        assert outer.duration_ms is not None
        # Outer should be longer than inner
        assert outer.duration_ms >= inner.duration_ms

    def test_operation_timer_name_stored(self):
        """Test OperationTimer stores operation name."""
        timer = OperationTimer("my_operation", record_metric=False)
        assert timer.operation_name == "my_operation"

    def test_operation_timer_context_returns_self(self):
        """Test OperationTimer __enter__ returns self."""
        timer = OperationTimer("test_op", record_metric=False)
        with timer as t:
            assert t is timer

    def test_operation_timer_measures_very_short_duration(self):
        """Test OperationTimer with very short operations."""
        with OperationTimer("fast_op", record_metric=False) as timer:
            # Very fast operation
            _ = 1 + 1

        assert timer.duration_ms is not None
        assert timer.duration_ms >= 0

    def test_operation_timer_re_raises_exception(self):
        """Test OperationTimer context manager re-raises exceptions."""
        with pytest.raises(ValueError):
            with OperationTimer("test_op", record_metric=False):
                raise ValueError("test error")


class TestPerformanceIntegration:
    """Integration tests for performance monitoring."""

    def test_decorator_and_timer_measure_same_operation(self):
        """Test decorator and timer can measure the same operation."""

        @timed_operation("test_op", record_metric=False)
        def decorated_func():
            time.sleep(0.01)
            return "result"

        with OperationTimer("test_op", record_metric=False) as timer:
            time.sleep(0.01)

        result = decorated_func()
        assert result == "result"
        assert timer.duration_ms is not None

    def test_multiple_operations_with_metrics(self):
        """Test recording multiple operations with metrics."""
        with patch(
            "roadmap.common.services.performance.get_metrics_collector"
        ) as mock_collector:
            mock_instance = MagicMock()
            mock_collector.return_value = mock_instance

            @timed_operation("op1", record_metric=True)
            def func1():
                return "r1"

            @timed_operation("op2", record_metric=True)
            def func2():
                return "r2"

            func1()
            func2()

            # Should have recorded two metrics
            assert mock_instance.record.call_count == 2

    @pytest.mark.asyncio
    async def test_async_and_sync_operations_together(self):
        """Test async and sync operations work together."""

        @timed_operation("sync_op", record_metric=False)
        def sync_func():
            return "sync"

        @async_timed_operation("async_op", record_metric=False)
        async def async_func():
            return "async"

        sync_result = sync_func()
        async_result = await async_func()

        assert sync_result == "sync"
        assert async_result == "async"

    def test_performance_with_real_operations(self):
        """Test performance measurement with realistic operations."""

        @timed_operation("data_processing", record_metric=False)
        def process_data(items):
            total = 0
            for item in items:
                total += item
                time.sleep(0.001)
            return total

        result = process_data([1, 2, 3, 4, 5])
        assert result == 15

    def test_operation_timer_with_error_handling(self):
        """Test OperationTimer doesn't suppress exception handling."""
        errors_caught = []

        try:
            with OperationTimer("failing_op", record_metric=False) as timer:
                raise RuntimeError("operation failed")
        except RuntimeError as e:
            errors_caught.append(e)

        assert len(errors_caught) == 1
        assert timer.error is not None
