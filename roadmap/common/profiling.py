"""Performance benchmarking and profiling utilities.

This module provides tools for measuring and analyzing performance of CLI operations,
including execution timing, memory usage, and operation throughput.
"""

import time
from dataclasses import dataclass
from typing import Any

from .logging import get_logger

logger = get_logger(__name__)


@dataclass
class OperationProfile:
    """Profile data for a single operation type.

    Attributes:
        operation: Name of the operation
        count: Number of times operation was executed
        total_time_ms: Total execution time in milliseconds
        min_time_ms: Minimum single execution time
        max_time_ms: Maximum single execution time
    """

    operation: str
    count: int = 0
    total_time_ms: float = 0.0
    min_time_ms: float = float("inf")
    max_time_ms: float = 0.0
    errors: int = 0

    @property
    def avg_time_ms(self) -> float:
        """Calculate average execution time."""
        return self.total_time_ms / self.count if self.count > 0 else 0.0

    @property
    def throughput_per_sec(self) -> float:
        """Calculate operations per second."""
        if self.total_time_ms <= 0:
            return 0.0
        return (self.count / self.total_time_ms) * 1000

    def record(self, duration_ms: float, error: bool = False) -> None:
        """Record a single operation execution.

        Args:
            duration_ms: Execution time in milliseconds
            error: Whether the operation failed
        """
        self.count += 1
        self.total_time_ms += duration_ms
        self.min_time_ms = min(self.min_time_ms, duration_ms)
        self.max_time_ms = max(self.max_time_ms, duration_ms)
        if error:
            self.errors += 1


class PerformanceProfiler:
    """Profiles operation performance metrics across a session.

    Tracks execution time, error rates, and throughput for all operations,
    providing detailed performance insights.

    Example:
        profiler = PerformanceProfiler()
        profiler.start_operation("fetch_issues")
        # ... do work
        profiler.end_operation("fetch_issues")

        report = profiler.get_report()
        print(report.format())
    """

    def __init__(self) -> None:
        """Initialize profiler with no operations."""
        self._profiles: dict[str, OperationProfile] = {}
        self._start_times: dict[str, float] = {}
        logger.debug("profiler_initialized")

    def start_operation(self, operation: str) -> None:
        """Mark the start of an operation.

        Args:
            operation: Name of the operation

        Example:
            profiler.start_operation("sync_all")
        """
        self._start_times[operation] = time.perf_counter()

    def end_operation(self, operation: str, error: bool = False) -> float:
        """Mark the end of an operation and record metrics.

        Args:
            operation: Name of the operation
            error: Whether the operation failed

        Returns:
            Duration in milliseconds

        Example:
            try:
                # ... do work
                profiler.end_operation("sync_all")
            except Exception:
                profiler.end_operation("sync_all", error=True)
                raise
        """
        if operation not in self._start_times:
            logger.warning("operation_not_started", operation=operation)
            return 0.0

        start = self._start_times.pop(operation)
        duration_ms = (time.perf_counter() - start) * 1000

        if operation not in self._profiles:
            self._profiles[operation] = OperationProfile(operation)

        self._profiles[operation].record(duration_ms, error=error)
        logger.debug(
            "operation_profiled",
            operation=operation,
            duration_ms=duration_ms,
            error=error,
        )

        return duration_ms

    def get_profile(self, operation: str) -> OperationProfile | None:
        """Get profile for a specific operation.

        Args:
            operation: Name of the operation

        Returns:
            OperationProfile if found, None otherwise
        """
        return self._profiles.get(operation)

    def get_slowest_operations(self, limit: int = 10) -> list[OperationProfile]:
        """Get the slowest operations by average execution time.

        Args:
            limit: Maximum number of results to return

        Returns:
            List of operations sorted by average time (slowest first)
        """
        sorted_ops = sorted(
            self._profiles.values(), key=lambda p: p.avg_time_ms, reverse=True
        )
        return sorted_ops[:limit]

    def get_report(self) -> "PerformanceReport":
        """Generate a performance report for all operations.

        Returns:
            PerformanceReport with aggregated metrics
        """
        total_time_ms = sum(p.total_time_ms for p in self._profiles.values())
        total_count = sum(p.count for p in self._profiles.values())
        total_errors = sum(p.errors for p in self._profiles.values())

        return PerformanceReport(
            profiles=self._profiles.copy(),
            total_time_ms=total_time_ms,
            total_operations=total_count,
            total_errors=total_errors,
        )

    def clear(self) -> None:
        """Clear all profiles."""
        self._profiles.clear()
        self._start_times.clear()
        logger.debug("profiler_cleared")


@dataclass
class PerformanceReport:
    """Aggregated performance metrics for a session.

    Attributes:
        profiles: Dictionary of operation profiles
        total_time_ms: Total execution time
        total_operations: Total operations executed
        total_errors: Total failed operations
    """

    profiles: dict[str, OperationProfile]
    total_time_ms: float
    total_operations: int
    total_errors: int

    @property
    def success_rate(self) -> float:
        """Calculate overall success rate (0.0-1.0)."""
        if self.total_operations == 0:
            return 0.0
        return (self.total_operations - self.total_errors) / self.total_operations

    def format(self) -> str:
        """Format report as human-readable string.

        Returns:
            Formatted performance report

        Example:
            report = profiler.get_report()
            print(report.format())
        """
        lines = [
            "═" * 70,
            "PERFORMANCE REPORT",
            "═" * 70,
            f"Total Time: {self.total_time_ms:.2f}ms",
            f"Total Operations: {self.total_operations}",
            f"Success Rate: {self.success_rate:.1%}",
            "",
            "Operation Breakdown:",
            "-" * 70,
        ]

        # Sort by total time
        sorted_ops = sorted(
            self.profiles.values(), key=lambda p: p.total_time_ms, reverse=True
        )

        for profile in sorted_ops:
            pct = (
                (profile.total_time_ms / self.total_time_ms * 100)
                if self.total_time_ms > 0
                else 0
            )
            error_str = f" ({profile.errors} errors)" if profile.errors > 0 else ""

            lines.append(
                f"{profile.operation:30} {profile.count:5} ops  "
                f"{profile.avg_time_ms:8.2f}ms avg  {pct:5.1f}%{error_str}"
            )

        lines.append("═" * 70)
        return "\n".join(lines)

    def get_dict(self) -> dict[str, Any]:
        """Convert report to dictionary format.

        Returns:
            Dictionary representation of the report
        """
        return {
            "total_time_ms": self.total_time_ms,
            "total_operations": self.total_operations,
            "success_rate": self.success_rate,
            "total_errors": self.total_errors,
            "operations": {
                name: {
                    "count": profile.count,
                    "total_ms": profile.total_time_ms,
                    "avg_ms": profile.avg_time_ms,
                    "min_ms": profile.min_time_ms if profile.count > 0 else 0,
                    "max_ms": profile.max_time_ms,
                    "throughput_ops_per_sec": profile.throughput_per_sec,
                    "errors": profile.errors,
                }
                for name, profile in self.profiles.items()
            },
        }


# Global profiler instance
_profiler = PerformanceProfiler()


def get_profiler() -> PerformanceProfiler:
    """Get the global profiler instance.

    Returns:
        The singleton PerformanceProfiler instance

    Example:
        profiler = get_profiler()
        profiler.start_operation("my_op")
    """
    return _profiler
