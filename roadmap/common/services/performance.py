"""Performance monitoring decorators and utilities."""

import functools
import time
from collections.abc import Callable
from typing import Any, TypeVar

from ..logging import get_logger
from .metrics import OperationMetric, get_metrics_collector
from .profiling import get_profiler

logger = get_logger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


def timed_operation(operation_name: str | None = None, record_metric: bool = True):
    """Time operations and optionally record metrics.

    This decorator measures the execution time of a function and logs it.
    It can also record the timing as a metric in the global MetricsCollector
    and performance profiler.

    Args:
        operation_name: Name for the operation (defaults to function name)
        record_metric: Whether to record the timing as a metric

    Example:
        @timed_operation("create_issue")
        def create_issue(title: str) -> Issue:
            # ... implementation
            pass
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            op_name = operation_name or func.__name__
            start_time = time.perf_counter()
            error: Exception | None = None
            result: Any = None

            # Record in profiler
            profiler = get_profiler()
            profiler.start_operation(op_name)

            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                error = e
                raise
            finally:
                # Calculate duration
                duration_ms = (time.perf_counter() - start_time) * 1000

                # Record in profiler
                profiler.end_operation(op_name, error=error is not None)

                # Log the timing
                if error:
                    logger.error(
                        "operation_failed",
                        operation=op_name,
                        duration_ms=round(duration_ms, 2),
                        error=str(error),
                        error_type=type(error).__name__,
                    )
                else:
                    logger.info(
                        "operation_completed",
                        operation=op_name,
                        duration_ms=round(duration_ms, 2),
                    )

                # Record metric if requested
                if record_metric:
                    collector = get_metrics_collector()
                    metric = OperationMetric(
                        operation=op_name,
                        duration_ms=duration_ms,
                        success=error is None,
                        error=str(error) if error else None,
                    )
                    collector.record(metric)

        return wrapper  # type: ignore

    return decorator


def async_timed_operation(
    operation_name: str | None = None, record_metric: bool = True
):
    """Async version of timed_operation decorator.

    Args:
        operation_name: Name for the operation (defaults to function name)
        record_metric: Whether to record the timing as a metric

    Example:
        @async_timed_operation("fetch_issues")
        async def fetch_issues() -> list[Issue]:
            # ... async implementation
            pass
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            op_name = operation_name or func.__name__
            start_time = time.perf_counter()
            error: Exception | None = None
            result: Any = None

            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                error = e
                raise
            finally:
                # Calculate duration
                duration_ms = (time.perf_counter() - start_time) * 1000

                # Log the timing
                if error:
                    logger.error(
                        "async_operation_failed",
                        operation=op_name,
                        duration_ms=round(duration_ms, 2),
                        error=str(error),
                        error_type=type(error).__name__,
                    )
                else:
                    logger.info(
                        "async_operation_completed",
                        operation=op_name,
                        duration_ms=round(duration_ms, 2),
                    )

                # Record metric if requested
                if record_metric:
                    collector = get_metrics_collector()
                    metric = OperationMetric(
                        operation=op_name,
                        duration_ms=duration_ms,
                        success=error is None,
                        error=str(error) if error else None,
                    )
                    collector.record(metric)

        return wrapper  # type: ignore

    return decorator


class OperationTimer:
    """Context manager for timing code blocks.

    Example:
        with OperationTimer("database_query") as timer:
            # ... perform operation
            pass
        print(f"Operation took {timer.duration_ms}ms")
    """

    def __init__(self, operation_name: str, record_metric: bool = True):
        """Initialize the timer.

        Args:
            operation_name: Name of the operation being timed
            record_metric: Whether to record the timing as a metric
        """
        self.operation_name = operation_name
        self.record_metric = record_metric
        self.start_time: float | None = None
        self.end_time: float | None = None
        self.duration_ms: float | None = None
        self.error: Exception | None = None

    def __enter__(self) -> "OperationTimer":
        """Start the timer."""
        self.start_time = time.perf_counter()
        logger.debug("operation_started", operation=self.operation_name)
        return self

    def __exit__(self, _exc_type, exc_val, _exc_tb) -> None:
        """Stop the timer and record metrics."""
        self.end_time = time.perf_counter()
        assert self.start_time is not None
        self.duration_ms = (self.end_time - self.start_time) * 1000

        if exc_val:
            self.error = exc_val
            logger.error(
                "operation_failed",
                operation=self.operation_name,
                duration_ms=round(self.duration_ms, 2),
                error=str(exc_val),
                error_type=type(exc_val).__name__,
            )
        else:
            logger.info(
                "operation_completed",
                operation=self.operation_name,
                duration_ms=round(self.duration_ms, 2),
            )

        # Record metric if requested
        if self.record_metric:
            collector = get_metrics_collector()
            metric = OperationMetric(
                operation=self.operation_name,
                duration_ms=self.duration_ms,
                success=exc_val is None,
                error=str(exc_val) if exc_val else None,
            )
            collector.record(metric)
