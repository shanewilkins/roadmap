"""Health status formatting and presentation utilities.

Provides health-specific formatting built on top of generic status utilities.
"""

from roadmap.core.domain.health import HealthStatus


class HealthStatusFormatter:
    """Formats and presents health check results."""

    @staticmethod
    def summarize_health_checks(
        checks: dict[str, tuple[HealthStatus, str]],
    ) -> dict[str, int]:
        """Summarize health check results into status counts.

        Args:
            checks: Dict mapping check names to (status, message) tuples

        Returns:
            Dict with counts: {
                "total": count,
                "healthy": count,
                "degraded": count,
                "unhealthy": count,
            }
        """
        statuses = [status for _, (status, _) in checks.items()]

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

    @staticmethod
    def get_status_color(status: HealthStatus) -> str:
        """Get terminal color for health status.

        Args:
            status: HealthStatus to format

        Returns:
            ANSI color code string
        """
        if status == HealthStatus.HEALTHY:
            return "\033[92m"  # Green
        elif status == HealthStatus.DEGRADED:
            return "\033[93m"  # Yellow
        elif status == HealthStatus.UNHEALTHY:
            return "\033[91m"  # Red
        return "\033[0m"  # Reset

    @staticmethod
    def format_status_display(status: HealthStatus) -> str:
        """Get human-readable display for health status.

        Args:
            status: HealthStatus to format

        Returns:
            Formatted status string
        """
        return status.value.upper()
