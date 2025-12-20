"""Utilities for status summary calculations.

Consolidates repeated patterns for aggregating status counts from
health checks and validation results.

Eliminates duplicate status counting logic from:
- HealthCheckService.get_health_summary()
- Infrastructure validators
- Data integrity validators
- Other status aggregation code
"""

from collections import Counter
from enum import Enum


class StatusSummary:
    """Utility for computing status summaries from check results.

    Provides consistent methods for:
    - Counting items by status enum value
    - Aggregating health check results
    - Creating summary dictionaries

    Usage:

        # Count items by status
        counts = StatusSummary.count_by_status([
            ("check1", HealthStatus.HEALTHY),
            ("check2", HealthStatus.DEGRADED),
            ("check3", HealthStatus.HEALTHY),
        ])
        # Returns: {"healthy": 2, "degraded": 1}

        # Summarize health checks dict
        summary = StatusSummary.summarize_checks({
            "roadmap_dir": (HealthStatus.HEALTHY, "OK"),
            "database": (HealthStatus.DEGRADED, "Lag detected"),
            "git": (HealthStatus.UNHEALTHY, "Not a repo"),
        })
        # Returns: {
        #     "total": 3,
        #     "healthy": 1,
        #     "degraded": 1,
        #     "unhealthy": 1,
        # }
    """

    @staticmethod
    def count_by_status(items: list[tuple[str, Enum]]) -> dict[str, int]:
        """Count items by status enum value.

        Args:
            items: List of (label, status_enum) tuples

        Returns:
            Dict mapping status values to counts

        Example:
            items = [
                ("check1", HealthStatus.HEALTHY),
                ("check2", HealthStatus.HEALTHY),
                ("check3", HealthStatus.DEGRADED),
            ]
            counts = StatusSummary.count_by_status(items)
            # Returns: {"healthy": 2, "degraded": 1}
        """
        counter = Counter(status.value for _, status in items)
        return dict(counter)

    @staticmethod
    def summarize_checks(
        checks: dict[str, tuple[Enum, str]], status_enum_class=None
    ) -> dict[str, int]:
        """Get summary counts from checks dict with generic status enum.

        Aggregates check results into overall counts by status, without
        hardcoding specific status values. The method is generic and works
        with any status enum.

        Args:
            checks: Dict of {check_name: (status_enum, message)}
            status_enum_class: Optional status enum class for type validation.
                             If provided, all unique status values will be counted.

        Returns:
            Dict with counts: {
                "total": count,
                "status1": count,
                "status2": count,
                ...
            }

        Example:
            from roadmap.core.domain.health import HealthStatus

            checks = {
                "roadmap_dir": (HealthStatus.HEALTHY, "OK"),
                "database": (HealthStatus.DEGRADED, "Lag"),
                "git": (HealthStatus.UNHEALTHY, "Not a repo"),
            }
            summary = StatusSummary.summarize_checks(checks, HealthStatus)
            # Returns: {
            #     "total": 3,
            #     "healthy": 1,
            #     "degraded": 1,
            #     "unhealthy": 1,
            # }
        """
        statuses = [status for _, (status, _) in checks.items()]

        total = len(statuses)
        counts = {"total": total}

        # Count by status value
        counter = Counter(s.value for s in statuses)
        counts.update(dict(counter))

        # If no explicit enum class, try to infer from first status
        if not status_enum_class and statuses:
            status_enum_class = type(statuses[0])

        # Ensure all enum values are represented (with 0 count if missing)
        if status_enum_class:
            for member in status_enum_class:
                if member.value not in counts:
                    counts[member.value] = 0

        return counts
