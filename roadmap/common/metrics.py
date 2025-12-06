"""Metrics collection and reporting for monitoring operation performance."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .logging import get_logger

logger = get_logger(__name__)


@dataclass
class OperationMetric:
    """Track operation performance and success.

    Attributes:
        operation: Name of the operation being tracked
        duration_ms: Duration of the operation in milliseconds
        success: Whether the operation succeeded
        error: Error message if operation failed, None otherwise
        timestamp: When the operation completed (UTC)
        metadata: Additional context about the operation
    """

    operation: str
    duration_ms: float
    success: bool
    error: str | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)


class MetricsCollector:
    """Collect and report application metrics.

    This class maintains a collection of operation metrics and provides
    aggregated statistics for monitoring and observability.
    """

    def __init__(self):
        """Initialize an empty metrics collector."""
        self.metrics: list[OperationMetric] = []
        logger.debug("metrics_collector_initialized")

    def record(self, metric: OperationMetric) -> None:
        """Record a metric.

        Args:
            metric: The operation metric to record
        """
        self.metrics.append(metric)
        logger.debug(
            "metric_recorded",
            operation=metric.operation,
            duration_ms=metric.duration_ms,
            success=metric.success,
            error=metric.error,
        )

    def get_stats(self) -> dict[str, Any]:
        """Get aggregated statistics from recorded metrics.

        Returns:
            Dictionary containing:
                - total_operations: Total number of operations recorded
                - success_rate: Percentage of successful operations (0.0-1.0)
                - avg_duration_ms: Average operation duration in milliseconds
                - errors: List of failed operation metrics
                - operations_by_type: Count of operations grouped by type
        """
        if not self.metrics:
            return {
                "total_operations": 0,
                "success_rate": 0.0,
                "avg_duration_ms": 0.0,
                "errors": [],
                "operations_by_type": {},
            }

        total = len(self.metrics)
        successful = sum(1 for m in self.metrics if m.success)
        success_rate = successful / total if total > 0 else 0.0
        avg_duration = sum(m.duration_ms for m in self.metrics) / total
        errors = [m for m in self.metrics if not m.success]

        # Count operations by type
        operations_by_type: dict[str, int] = {}
        for metric in self.metrics:
            operations_by_type[metric.operation] = (
                operations_by_type.get(metric.operation, 0) + 1
            )

        return {
            "total_operations": total,
            "success_rate": success_rate,
            "avg_duration_ms": avg_duration,
            "errors": errors,
            "operations_by_type": operations_by_type,
        }

    def clear(self) -> None:
        """Clear all recorded metrics."""
        count = len(self.metrics)
        self.metrics.clear()
        logger.debug("metrics_cleared", count=count)

    def get_error_rate(self) -> float:
        """Get the error rate (1 - success_rate).

        Returns:
            Error rate as a float between 0.0 and 1.0
        """
        if not self.metrics:
            return 0.0
        return 1.0 - self.get_stats()["success_rate"]

    def get_operation_stats(self, operation: str) -> dict[str, Any]:
        """Get statistics for a specific operation type.

        Args:
            operation: Name of the operation to get stats for

        Returns:
            Dictionary with stats specific to this operation type
        """
        op_metrics = [m for m in self.metrics if m.operation == operation]

        if not op_metrics:
            return {
                "count": 0,
                "success_rate": 0.0,
                "avg_duration_ms": 0.0,
                "errors": [],
            }

        total = len(op_metrics)
        successful = sum(1 for m in op_metrics if m.success)

        return {
            "count": total,
            "success_rate": successful / total,
            "avg_duration_ms": sum(m.duration_ms for m in op_metrics) / total,
            "errors": [m for m in op_metrics if not m.success],
        }


# Global metrics collector instance
_global_collector: MetricsCollector | None = None


def get_metrics_collector() -> MetricsCollector:
    """Get or create the global metrics collector instance.

    Returns:
        The global MetricsCollector instance
    """
    global _global_collector
    if _global_collector is None:
        _global_collector = MetricsCollector()
        logger.debug("global_metrics_collector_created")
    return _global_collector
