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
    def summarize_checks(checks: dict[str, tuple[Enum, str]]) -> dict[str, int]:
        """Get summary counts from health checks dict.

        Aggregates check results into overall counts by status.

        Args:
            checks: Dict of {check_name: (status_enum, message)}

        Returns:
            Dict with counts: {
                "total": count,
                "healthy": count,
                "degraded": count,
                "unhealthy": count,
            }

        Example:
            checks = {
                "roadmap_dir": (HealthStatus.HEALTHY, "OK"),
                "database": (HealthStatus.DEGRADED, "Lag"),
                "git": (HealthStatus.UNHEALTHY, "Not a repo"),
            }
            summary = StatusSummary.summarize_checks(checks)
            # Returns: {
            #     "total": 3,
            #     "healthy": 1,
            #     "degraded": 1,
            #     "unhealthy": 1,
            # }
        """
        statuses = [status for _, (status, _) in checks.items()]

        # Import here to avoid circular dependency
        from roadmap.infrastructure.health import HealthStatus

        total = len(statuses)
        healthy = sum(1 for s in statuses if s == HealthStatus.HEALTHY)
        degraded = sum(1 for s in statuses if s == HealthStatus.DEGRADED)
        unhealthy = sum(1 for s in statuses if s == HealthStatus.UNHEALTHY)

        return {
            "total": total,
            "healthy": healthy,
            "degraded": degraded,
            "unhealthy": unhealthy,
        }
