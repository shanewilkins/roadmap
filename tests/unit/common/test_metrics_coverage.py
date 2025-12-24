"""Comprehensive tests for metrics module."""

from datetime import datetime, timedelta, timezone

import pytest

from roadmap.common.metrics import (
    MetricsCollector,
    OperationMetric,
    get_metrics_collector,
)


class TestOperationMetric:
    """Tests for OperationMetric dataclass."""

    def test_create_successful_metric(self):
        """Test creating a metric for successful operation."""
        metric = OperationMetric(
            operation="save_file",
            duration_ms=125.5,
            success=True,
        )
        assert metric.operation == "save_file"
        assert metric.duration_ms == 125.5
        assert metric.success
        assert metric.error is None

    def test_create_failed_metric(self):
        """Test creating a metric for failed operation."""
        metric = OperationMetric(
            operation="api_call",
            duration_ms=500.0,
            success=False,
            error="Connection timeout",
        )
        assert metric.operation == "api_call"
        assert not metric.success
        assert metric.error == "Connection timeout"

    def test_default_timestamp(self):
        """Test that timestamp defaults to current UTC time."""
        before = datetime.now(timezone.utc)
        metric = OperationMetric(
            operation="test",
            duration_ms=1.0,
            success=True,
        )
        after = datetime.now(timezone.utc)

        assert before <= metric.timestamp <= after

    def test_custom_timestamp(self):
        """Test setting custom timestamp."""
        custom_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        metric = OperationMetric(
            operation="test",
            duration_ms=1.0,
            success=True,
            timestamp=custom_time,
        )
        assert metric.timestamp == custom_time

    def test_metadata_field(self):
        """Test metadata field."""
        metadata = {"user_id": "123", "retry_count": 2}
        metric = OperationMetric(
            operation="test",
            duration_ms=1.0,
            success=True,
            metadata=metadata,
        )
        assert metric.metadata == metadata

    def test_empty_metadata_by_default(self):
        """Test metadata is empty dict by default."""
        metric = OperationMetric(
            operation="test",
            duration_ms=1.0,
            success=True,
        )
        assert metric.metadata == {}


class TestMetricsCollector:
    """Tests for MetricsCollector class."""

    def test_initialization(self):
        """Test MetricsCollector initializes with empty metrics list."""
        collector = MetricsCollector()
        assert collector.metrics == []

    def test_record_single_metric(self):
        """Test recording a single metric."""
        collector = MetricsCollector()
        metric = OperationMetric(
            operation="test",
            duration_ms=100.0,
            success=True,
        )
        collector.record(metric)

        assert len(collector.metrics) == 1
        assert collector.metrics[0] == metric

    def test_record_multiple_metrics(self):
        """Test recording multiple metrics."""
        collector = MetricsCollector()
        metrics = [
            OperationMetric(operation="op1", duration_ms=100.0, success=True),
            OperationMetric(operation="op2", duration_ms=200.0, success=False),
            OperationMetric(operation="op3", duration_ms=150.0, success=True),
        ]

        for metric in metrics:
            collector.record(metric)

        assert len(collector.metrics) == 3

    def test_get_stats_empty_collector(self):
        """Test getting stats from empty collector."""
        collector = MetricsCollector()
        stats = collector.get_stats()

        assert stats["total_operations"] == 0
        assert stats["success_rate"] == 0.0
        assert stats["avg_duration_ms"] == 0.0
        assert stats["errors"] == []
        assert stats["operations_by_type"] == {}

    def test_get_stats_all_successful(self):
        """Test stats when all operations successful."""
        collector = MetricsCollector()
        metrics = [
            OperationMetric(operation="save", duration_ms=100.0, success=True),
            OperationMetric(operation="save", duration_ms=150.0, success=True),
            OperationMetric(operation="load", duration_ms=50.0, success=True),
        ]

        for metric in metrics:
            collector.record(metric)

        stats = collector.get_stats()
        assert stats["total_operations"] == 3
        assert stats["success_rate"] == 1.0
        assert stats["avg_duration_ms"] == 100.0  # (100 + 150 + 50) / 3
        assert stats["errors"] == []
        assert stats["operations_by_type"]["save"] == 2
        assert stats["operations_by_type"]["load"] == 1

    def test_get_stats_with_failures(self):
        """Test stats with some failed operations."""
        collector = MetricsCollector()
        metrics = [
            OperationMetric(operation="api", duration_ms=100.0, success=True),
            OperationMetric(
                operation="api", duration_ms=200.0, success=False, error="Timeout"
            ),
            OperationMetric(operation="api", duration_ms=150.0, success=True),
        ]

        for metric in metrics:
            collector.record(metric)

        stats = collector.get_stats()
        assert stats["total_operations"] == 3
        assert stats["success_rate"] == pytest.approx(2 / 3)
        assert len(stats["errors"]) == 1
        assert stats["errors"][0].operation == "api"
        assert stats["errors"][0].error == "Timeout"

    def test_get_stats_avg_duration(self):
        """Test average duration calculation."""
        collector = MetricsCollector()
        metrics = [
            OperationMetric(operation="test", duration_ms=10.0, success=True),
            OperationMetric(operation="test", duration_ms=20.0, success=True),
            OperationMetric(operation="test", duration_ms=30.0, success=True),
        ]

        for metric in metrics:
            collector.record(metric)

        stats = collector.get_stats()
        assert stats["avg_duration_ms"] == 20.0  # (10 + 20 + 30) / 3

    def test_clear_metrics(self):
        """Test clearing all metrics."""
        collector = MetricsCollector()
        metrics = [
            OperationMetric(operation="test", duration_ms=100.0, success=True),
            OperationMetric(operation="test", duration_ms=200.0, success=True),
        ]

        for metric in metrics:
            collector.record(metric)

        assert len(collector.metrics) == 2
        collector.clear()
        assert len(collector.metrics) == 0

    def test_get_error_rate_no_metrics(self):
        """Test error rate with no metrics."""
        collector = MetricsCollector()
        assert collector.get_error_rate() == 0.0

    def test_get_error_rate_all_success(self):
        """Test error rate when all operations succeed."""
        collector = MetricsCollector()
        for _ in range(3):
            collector.record(
                OperationMetric(operation="test", duration_ms=100.0, success=True)
            )

        assert collector.get_error_rate() == 0.0

    def test_get_error_rate_with_failures(self):
        """Test error rate calculation."""
        collector = MetricsCollector()
        collector.record(
            OperationMetric(operation="test", duration_ms=100.0, success=True)
        )
        collector.record(
            OperationMetric(
                operation="test", duration_ms=200.0, success=False, error="Error"
            )
        )

        assert collector.get_error_rate() == pytest.approx(0.5)

    def test_get_operation_stats_unknown_operation(self):
        """Test getting stats for non-existent operation."""
        collector = MetricsCollector()
        collector.record(
            OperationMetric(operation="test", duration_ms=100.0, success=True)
        )

        stats = collector.get_operation_stats("unknown")
        assert stats["count"] == 0
        assert stats["success_rate"] == 0.0
        assert stats["avg_duration_ms"] == 0.0
        assert stats["errors"] == []

    def test_get_operation_stats_specific_operation(self):
        """Test getting stats for specific operation type."""
        collector = MetricsCollector()
        metrics = [
            OperationMetric(operation="save", duration_ms=100.0, success=True),
            OperationMetric(operation="load", duration_ms=50.0, success=True),
            OperationMetric(operation="save", duration_ms=150.0, success=False),
            OperationMetric(operation="save", duration_ms=200.0, success=True),
        ]

        for metric in metrics:
            collector.record(metric)

        save_stats = collector.get_operation_stats("save")
        assert save_stats["count"] == 3
        assert save_stats["success_rate"] == pytest.approx(2 / 3)
        assert save_stats["avg_duration_ms"] == pytest.approx(
            150.0
        )  # (100 + 150 + 200) / 3
        assert len(save_stats["errors"]) == 1

    def test_get_operation_stats_all_failed(self):
        """Test operation stats when all operations failed."""
        collector = MetricsCollector()
        metrics = [
            OperationMetric(
                operation="api", duration_ms=100.0, success=False, error="Error 1"
            ),
            OperationMetric(
                operation="api", duration_ms=200.0, success=False, error="Error 2"
            ),
        ]

        for metric in metrics:
            collector.record(metric)

        stats = collector.get_operation_stats("api")
        assert stats["count"] == 2
        assert stats["success_rate"] == 0.0
        assert len(stats["errors"]) == 2


class TestGlobalMetricsCollector:
    """Tests for global metrics collector instance."""

    def test_get_metrics_collector_creates_instance(self):
        """Test that get_metrics_collector creates an instance."""
        # Clear any existing global instance by creating a new one
        collector1 = get_metrics_collector()
        assert collector1 is not None
        assert isinstance(collector1, MetricsCollector)

    def test_get_metrics_collector_returns_same_instance(self):
        """Test that get_metrics_collector returns the same instance."""
        # This test verifies singleton behavior
        import roadmap.common.metrics as metrics_module

        # Reset global instance for test
        metrics_module._global_collector = None

        collector1 = metrics_module.get_metrics_collector()
        collector2 = metrics_module.get_metrics_collector()

        assert collector1 is collector2

    def test_global_collector_can_record_metrics(self):
        """Test that global collector can record metrics."""
        import roadmap.common.metrics as metrics_module

        # Reset global instance
        metrics_module._global_collector = None

        collector = get_metrics_collector()
        metric = OperationMetric(
            operation="global_test",
            duration_ms=50.0,
            success=True,
        )
        collector.record(metric)

        stats = collector.get_stats()
        assert stats["total_operations"] == 1


class TestMetricsIntegration:
    """Integration tests for metrics module."""

    def test_complete_workflow(self):
        """Test complete metrics collection workflow - collection and stats."""
        collector = MetricsCollector()

        # Simulate various operations
        operations = [
            ("fetch_user", 150.0, True, None),
            ("fetch_user", 180.0, True, None),
            ("fetch_user", 5000.0, False, "Timeout"),
            ("save_data", 50.0, True, None),
            ("save_data", 75.0, True, None),
            ("delete_cache", 10.0, True, None),
        ]

        for op_name, duration, success, error in operations:
            metric = OperationMetric(
                operation=op_name,
                duration_ms=duration,
                success=success,
                error=error,
            )
            collector.record(metric)

        # Verify overall stats
        stats = collector.get_stats()
        assert stats["total_operations"] == 6
        assert stats["success_rate"] == pytest.approx(5 / 6)

    def test_complete_workflow_errors(self):
        """Test complete metrics collection workflow - error tracking."""
        collector = MetricsCollector()

        # Simulate various operations
        operations = [
            ("fetch_user", 150.0, True, None),
            ("fetch_user", 180.0, True, None),
            ("fetch_user", 5000.0, False, "Timeout"),
            ("save_data", 50.0, True, None),
            ("save_data", 75.0, True, None),
            ("delete_cache", 10.0, True, None),
        ]

        for op_name, duration, success, error in operations:
            metric = OperationMetric(
                operation=op_name,
                duration_ms=duration,
                success=success,
                error=error,
            )
            collector.record(metric)

        # Verify errors and operations
        stats = collector.get_stats()
        assert len(stats["errors"]) == 1
        assert len(stats["operations_by_type"]) == 3

    def test_complete_workflow_operation_stats(self):
        """Test complete metrics collection workflow - operation-specific stats."""
        collector = MetricsCollector()

        # Simulate various operations
        operations = [
            ("fetch_user", 150.0, True, None),
            ("fetch_user", 180.0, True, None),
            ("fetch_user", 5000.0, False, "Timeout"),
            ("save_data", 50.0, True, None),
            ("save_data", 75.0, True, None),
            ("delete_cache", 10.0, True, None),
        ]

        for op_name, duration, success, error in operations:
            metric = OperationMetric(
                operation=op_name,
                duration_ms=duration,
                success=success,
                error=error,
            )
            collector.record(metric)

        # Verify operation-specific stats
        fetch_stats = collector.get_operation_stats("fetch_user")
        assert fetch_stats["count"] == 3
        assert fetch_stats["success_rate"] == pytest.approx(2 / 3)

        save_stats = collector.get_operation_stats("save_data")
        assert save_stats["count"] == 2
        assert save_stats["success_rate"] == 1.0

    def test_metadata_tracking(self):
        """Test that metadata is properly tracked."""
        collector = MetricsCollector()

        metric1 = OperationMetric(
            operation="api_call",
            duration_ms=100.0,
            success=True,
            metadata={"endpoint": "/users", "status_code": 200},
        )

        metric2 = OperationMetric(
            operation="api_call",
            duration_ms=500.0,
            success=False,
            error="Connection error",
            metadata={"endpoint": "/data", "retry_count": 3},
        )

        collector.record(metric1)
        collector.record(metric2)

        stats = collector.get_stats()
        errors = stats["errors"]
        assert len(errors) == 1
        assert errors[0].metadata["retry_count"] == 3

    def test_timestamp_ordering(self):
        """Test that timestamps are properly recorded."""
        collector = MetricsCollector()

        base_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        for i in range(3):
            metric = OperationMetric(
                operation="test",
                duration_ms=100.0,
                success=True,
                timestamp=base_time + timedelta(seconds=i),
            )
            collector.record(metric)

        assert len(collector.metrics) == 3
        assert collector.metrics[0].timestamp < collector.metrics[1].timestamp
        assert collector.metrics[1].timestamp < collector.metrics[2].timestamp
