"""Tests for metrics collection and reporting."""

from datetime import datetime

from roadmap.shared.metrics import (
    MetricsCollector,
    OperationMetric,
    get_metrics_collector,
)


class TestOperationMetric:
    """Tests for OperationMetric dataclass."""

    def test_metric_creation(self):
        """Test creating a basic operation metric."""
        metric = OperationMetric(operation="test_op", duration_ms=150.5, success=True)

        assert metric.operation == "test_op"
        assert metric.duration_ms == 150.5
        assert metric.success is True
        assert metric.error is None
        assert isinstance(metric.timestamp, datetime)
        assert isinstance(metric.metadata, dict)
        assert len(metric.metadata) == 0

    def test_metric_with_error(self):
        """Test creating a metric for a failed operation."""
        metric = OperationMetric(
            operation="failed_op",
            duration_ms=50.0,
            success=False,
            error="Connection timeout",
        )

        assert metric.success is False
        assert metric.error == "Connection timeout"

    def test_metric_with_metadata(self):
        """Test creating a metric with additional metadata."""
        metadata = {"user_id": "123", "issue_count": 5}
        metric = OperationMetric(
            operation="list_issues", duration_ms=200.0, success=True, metadata=metadata
        )

        assert metric.metadata == metadata
        assert metric.metadata["user_id"] == "123"
        assert metric.metadata["issue_count"] == 5


class TestMetricsCollector:
    """Tests for MetricsCollector class."""

    def test_collector_initialization(self):
        """Test creating a new metrics collector."""
        collector = MetricsCollector()

        assert isinstance(collector.metrics, list)
        assert len(collector.metrics) == 0

    def test_record_metric(self):
        """Test recording a single metric."""
        collector = MetricsCollector()
        metric = OperationMetric(operation="test", duration_ms=100.0, success=True)

        collector.record(metric)

        assert len(collector.metrics) == 1
        assert collector.metrics[0] == metric

    def test_record_multiple_metrics(self):
        """Test recording multiple metrics."""
        collector = MetricsCollector()

        for i in range(5):
            metric = OperationMetric(
                operation=f"test_{i}", duration_ms=100.0 * i, success=True
            )
            collector.record(metric)

        assert len(collector.metrics) == 5

    def test_get_stats_empty(self):
        """Test getting stats from empty collector."""
        collector = MetricsCollector()
        stats = collector.get_stats()

        assert stats["total_operations"] == 0
        assert stats["success_rate"] == 0.0
        assert stats["avg_duration_ms"] == 0.0
        assert stats["errors"] == []
        assert stats["operations_by_type"] == {}

    def test_get_stats_all_successful(self):
        """Test stats calculation with all successful operations."""
        collector = MetricsCollector()

        for _i in range(10):
            metric = OperationMetric(operation="test", duration_ms=100.0, success=True)
            collector.record(metric)

        stats = collector.get_stats()

        assert stats["total_operations"] == 10
        assert stats["success_rate"] == 1.0
        assert stats["avg_duration_ms"] == 100.0
        assert len(stats["errors"]) == 0

    def test_get_stats_with_failures(self):
        """Test stats calculation with some failures."""
        collector = MetricsCollector()

        # 7 successful, 3 failed
        for _i in range(7):
            collector.record(
                OperationMetric(operation="success", duration_ms=100.0, success=True)
            )

        for _i in range(3):
            collector.record(
                OperationMetric(
                    operation="failure",
                    duration_ms=50.0,
                    success=False,
                    error="Test error",
                )
            )

        stats = collector.get_stats()

        assert stats["total_operations"] == 10
        assert stats["success_rate"] == 0.7
        assert len(stats["errors"]) == 3

    def test_get_stats_avg_duration(self):
        """Test average duration calculation."""
        collector = MetricsCollector()

        durations = [100.0, 200.0, 300.0, 400.0]
        for duration in durations:
            collector.record(
                OperationMetric(operation="test", duration_ms=duration, success=True)
            )

        stats = collector.get_stats()
        expected_avg = sum(durations) / len(durations)

        assert stats["avg_duration_ms"] == expected_avg

    def test_get_stats_operations_by_type(self):
        """Test grouping operations by type."""
        collector = MetricsCollector()

        # 3 create, 2 update, 5 list operations
        for _ in range(3):
            collector.record(
                OperationMetric(
                    operation="create_issue", duration_ms=100.0, success=True
                )
            )

        for _ in range(2):
            collector.record(
                OperationMetric(
                    operation="update_issue", duration_ms=150.0, success=True
                )
            )

        for _ in range(5):
            collector.record(
                OperationMetric(
                    operation="list_issues", duration_ms=200.0, success=True
                )
            )

        stats = collector.get_stats()

        assert stats["operations_by_type"]["create_issue"] == 3
        assert stats["operations_by_type"]["update_issue"] == 2
        assert stats["operations_by_type"]["list_issues"] == 5

    def test_clear_metrics(self):
        """Test clearing all metrics."""
        collector = MetricsCollector()

        # Add some metrics
        for _i in range(5):
            collector.record(
                OperationMetric(operation="test", duration_ms=100.0, success=True)
            )

        assert len(collector.metrics) == 5

        # Clear
        collector.clear()

        assert len(collector.metrics) == 0

    def test_get_error_rate(self):
        """Test error rate calculation."""
        collector = MetricsCollector()

        # 6 successful, 4 failed = 40% error rate
        for _ in range(6):
            collector.record(
                OperationMetric(operation="success", duration_ms=100.0, success=True)
            )

        for _ in range(4):
            collector.record(
                OperationMetric(
                    operation="failure", duration_ms=50.0, success=False, error="Error"
                )
            )

        error_rate = collector.get_error_rate()

        assert error_rate == 0.4

    def test_get_error_rate_empty(self):
        """Test error rate for empty collector."""
        collector = MetricsCollector()

        assert collector.get_error_rate() == 0.0

    def test_get_operation_stats(self):
        """Test getting stats for a specific operation type."""
        collector = MetricsCollector()

        # Add metrics for different operations
        for _ in range(3):
            collector.record(
                OperationMetric(
                    operation="create_issue", duration_ms=100.0, success=True
                )
            )

        collector.record(
            OperationMetric(
                operation="create_issue",
                duration_ms=200.0,
                success=False,
                error="Error",
            )
        )

        for _ in range(2):
            collector.record(
                OperationMetric(
                    operation="update_issue", duration_ms=150.0, success=True
                )
            )

        # Get stats for create_issue only
        create_stats = collector.get_operation_stats("create_issue")

        assert create_stats["count"] == 4
        assert create_stats["success_rate"] == 0.75
        assert create_stats["avg_duration_ms"] == 125.0  # (100+100+100+200)/4
        assert len(create_stats["errors"]) == 1

    def test_get_operation_stats_nonexistent(self):
        """Test getting stats for operation that doesn't exist."""
        collector = MetricsCollector()

        collector.record(
            OperationMetric(operation="test", duration_ms=100.0, success=True)
        )

        stats = collector.get_operation_stats("nonexistent")

        assert stats["count"] == 0
        assert stats["success_rate"] == 0.0
        assert stats["avg_duration_ms"] == 0.0
        assert stats["errors"] == []


class TestGlobalMetricsCollector:
    """Tests for global metrics collector instance."""

    def test_get_global_collector(self):
        """Test getting the global metrics collector."""
        collector1 = get_metrics_collector()
        collector2 = get_metrics_collector()

        # Should return the same instance
        assert collector1 is collector2

    def test_global_collector_persistence(self):
        """Test that global collector persists data."""
        collector = get_metrics_collector()

        # Clear any existing data
        collector.clear()

        # Add a metric
        collector.record(
            OperationMetric(operation="test", duration_ms=100.0, success=True)
        )

        # Get collector again
        collector2 = get_metrics_collector()

        # Should have the metric we added
        assert len(collector2.metrics) == 1
        assert collector2.metrics[0].operation == "test"
