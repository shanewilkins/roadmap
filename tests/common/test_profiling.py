"""Unit tests for the profiling module."""

import time
import pytest

from roadmap.common.profiling import (
    OperationProfile,
    PerformanceProfiler,
    PerformanceReport,
    get_profiler,
)


class TestOperationProfile:
    """Test OperationProfile data class."""

    def test_profile_creation(self):
        """Test creating a profile."""
        profile = OperationProfile("test_op")

        assert profile.operation == "test_op"
        assert profile.count == 0
        assert profile.total_time_ms == 0.0

    def test_record_operation(self):
        """Test recording an operation."""
        profile = OperationProfile("test_op")

        profile.record(50.0)
        profile.record(75.0)
        profile.record(25.0)

        assert profile.count == 3
        assert profile.total_time_ms == 150.0
        assert profile.min_time_ms == 25.0
        assert profile.max_time_ms == 75.0

    def test_average_time(self):
        """Test average time calculation."""
        profile = OperationProfile("test_op")

        profile.record(50.0)
        profile.record(100.0)

        assert profile.avg_time_ms == 75.0

    def test_average_time_empty(self):
        """Test average time for empty profile."""
        profile = OperationProfile("test_op")

        assert profile.avg_time_ms == 0.0

    def test_throughput_calculation(self):
        """Test operations per second calculation."""
        profile = OperationProfile("test_op")

        # 4 operations in 1000ms = 4 ops/sec
        profile.record(250.0)
        profile.record(250.0)
        profile.record(250.0)
        profile.record(250.0)

        assert profile.throughput_per_sec == 4.0

    def test_error_recording(self):
        """Test recording operations with errors."""
        profile = OperationProfile("test_op")

        profile.record(50.0, error=False)
        profile.record(75.0, error=True)
        profile.record(25.0, error=False)

        assert profile.count == 3
        assert profile.errors == 1


class TestPerformanceProfiler:
    """Test PerformanceProfiler functionality."""

    def test_profiler_creation(self):
        """Test creating a profiler."""
        profiler = PerformanceProfiler()

        assert len(profiler._profiles) == 0

    def test_start_and_end_operation(self):
        """Test timing an operation."""
        profiler = PerformanceProfiler()

        profiler.start_operation("test_op")
        time.sleep(0.1)
        duration = profiler.end_operation("test_op")

        # Should be approximately 100ms (within tolerance)
        assert 80 < duration < 150

    def test_operation_with_error(self):
        """Test recording operation with error."""
        profiler = PerformanceProfiler()

        profiler.start_operation("test_op")
        time.sleep(0.05)
        profiler.end_operation("test_op", error=True)

        profile = profiler.get_profile("test_op")
        assert profile.errors == 1
        assert profile.count == 1

    def test_get_profile(self):
        """Test retrieving a profile."""
        profiler = PerformanceProfiler()

        profiler.start_operation("op1")
        profiler.end_operation("op1")

        profile = profiler.get_profile("op1")
        assert profile is not None
        assert profile.operation == "op1"
        assert profile.count == 1

    def test_get_profile_nonexistent(self):
        """Test getting non-existent profile returns None."""
        profiler = PerformanceProfiler()

        assert profiler.get_profile("nonexistent") is None

    def test_slowest_operations(self):
        """Test getting slowest operations."""
        profiler = PerformanceProfiler()

        # Create profiles with different timings
        for name, times in [
            ("fast", [10, 15, 12]),
            ("slow", [100, 105, 102]),
            ("medium", [50, 55, 48]),
        ]:
            profiler.start_operation(name)
            for t in times:
                profiler._profiles[name] = OperationProfile(name)
                profiler._profiles[name].record(t)

        slowest = profiler.get_slowest_operations(2)

        assert len(slowest) == 2
        assert slowest[0].operation == "slow"
        assert slowest[1].operation == "medium"

    def test_multiple_operations(self):
        """Test profiling multiple operations."""
        profiler = PerformanceProfiler()

        for op in ["op1", "op2", "op3"]:
            profiler.start_operation(op)
            time.sleep(0.01)
            profiler.end_operation(op)

        report = profiler.get_report()
        assert report.total_operations == 3

    def test_clear(self):
        """Test clearing profiler."""
        profiler = PerformanceProfiler()

        profiler.start_operation("op1")
        profiler.end_operation("op1")
        profiler.start_operation("op2")
        profiler.end_operation("op2")

        profiler.clear()

        assert len(profiler._profiles) == 0
        assert len(profiler._start_times) == 0

    def test_operation_not_started(self):
        """Test ending operation that wasn't started."""
        profiler = PerformanceProfiler()

        # Should not raise, returns 0
        duration = profiler.end_operation("never_started")
        assert duration == 0.0


class TestPerformanceReport:
    """Test PerformanceReport functionality."""

    def test_report_creation(self):
        """Test creating a report."""
        profiles = {
            "op1": OperationProfile("op1"),
            "op2": OperationProfile("op2"),
        }
        profiles["op1"].record(50.0)
        profiles["op2"].record(100.0)

        report = PerformanceReport(
            profiles=profiles,
            total_time_ms=150.0,
            total_operations=2,
            total_errors=0,
        )

        assert report.total_operations == 2
        assert report.total_time_ms == 150.0

    def test_success_rate(self):
        """Test success rate calculation."""
        report = PerformanceReport(
            profiles={},
            total_time_ms=100.0,
            total_operations=10,
            total_errors=2,
        )

        assert report.success_rate == 0.8  # 8 out of 10

    def test_success_rate_all_failures(self):
        """Test success rate with all failures."""
        report = PerformanceReport(
            profiles={},
            total_time_ms=100.0,
            total_operations=5,
            total_errors=5,
        )

        assert report.success_rate == 0.0

    def test_success_rate_all_success(self):
        """Test success rate with all successes."""
        report = PerformanceReport(
            profiles={},
            total_time_ms=100.0,
            total_operations=5,
            total_errors=0,
        )

        assert report.success_rate == 1.0

    def test_format_report(self):
        """Test report formatting."""
        profiles = {
            "operation1": OperationProfile("operation1"),
        }
        profiles["operation1"].record(50.0)

        report = PerformanceReport(
            profiles=profiles,
            total_time_ms=50.0,
            total_operations=1,
            total_errors=0,
        )

        formatted = report.format()

        assert "PERFORMANCE REPORT" in formatted
        assert "operation1" in formatted
        assert "Total Time:" in formatted
        assert "Success Rate:" in formatted

    def test_get_dict(self):
        """Test converting report to dictionary."""
        profiles = {
            "op1": OperationProfile("op1"),
        }
        profiles["op1"].record(50.0)
        profiles["op1"].record(75.0)

        report = PerformanceReport(
            profiles=profiles,
            total_time_ms=125.0,
            total_operations=2,
            total_errors=0,
        )

        report_dict = report.get_dict()

        assert report_dict["total_time_ms"] == 125.0
        assert report_dict["total_operations"] == 2
        assert "op1" in report_dict["operations"]
        assert report_dict["operations"]["op1"]["count"] == 2
        assert report_dict["operations"]["op1"]["avg_ms"] == 62.5


class TestGlobalProfiler:
    """Test the global profiler instance."""

    def test_get_global_profiler(self):
        """Test getting the global profiler."""
        profiler1 = get_profiler()
        profiler2 = get_profiler()

        # Should be same instance
        assert profiler1 is profiler2
