"""Health check service for roadmap CLI.

This module handles system health checking and reporting, providing
component status information and overall system health assessment.
"""

from typing import Any

from roadmap.common.logging import get_logger
from roadmap.core.domain.health import HealthStatus
from roadmap.infrastructure.core import RoadmapCore
from roadmap.infrastructure.health import HealthCheck

logger = get_logger(__name__)


class HealthCheckService:
    """Manages system health checks and reporting."""

    def __init__(self, core: RoadmapCore):
        """Initialize the service.

        Args:
            core: RoadmapCore instance
        """
        self.core = core

    def run_all_checks(self) -> dict[str, tuple[HealthStatus, str]]:
        """Run all system health checks.

        Returns:
            Dictionary mapping check names to (status, message) tuples
        """
        try:
            checks = HealthCheck.run_all_checks(self.core)
            logger.debug("health_checks_completed", check_count=len(checks))
            return checks
        except Exception as e:
            logger.error("health_checks_failed", error=str(e))
            return {}

    def get_overall_status(
        self, checks: dict[str, tuple[HealthStatus, str]] | None = None
    ) -> HealthStatus:
        """Get overall system health status.

        Args:
            checks: Optional dict of checks. If None, runs checks first.

        Returns:
            Overall HealthStatus
        """
        try:
            if checks is None:
                checks = self.run_all_checks()

            overall = HealthCheck.get_overall_status(checks)
            logger.debug("overall_status_calculated", status=overall.value)
            return overall
        except Exception as e:
            logger.error("overall_status_failed", error=str(e))
            return HealthStatus.UNHEALTHY

    def get_check_status(self, check_name: str) -> tuple[HealthStatus, str] | None:
        """Get status of a specific health check.

        Args:
            check_name: Name of the check to retrieve

        Returns:
            Tuple of (status, message) or None if check not found
        """
        try:
            checks = self.run_all_checks()
            return checks.get(check_name)
        except Exception as e:
            logger.error("get_check_status_failed", check_name=check_name, error=str(e))
            return None

    def get_health_summary(self) -> dict[str, Any]:
        """Get comprehensive health summary.

        Returns:
            Dictionary with health summary data
        """
        try:
            checks = self.run_all_checks()
            overall_status = self.get_overall_status(checks)

            healthy_count = sum(
                1 for _, (status, _) in checks.items() if status == HealthStatus.HEALTHY
            )
            degraded_count = sum(
                1
                for _, (status, _) in checks.items()
                if status == HealthStatus.DEGRADED
            )
            unhealthy_count = sum(
                1
                for _, (status, _) in checks.items()
                if status == HealthStatus.UNHEALTHY
            )

            return {
                "overall_status": overall_status.value,
                "checks": checks,
                "summary": {
                    "total": len(checks),
                    "healthy": healthy_count,
                    "degraded": degraded_count,
                    "unhealthy": unhealthy_count,
                },
            }
        except Exception as e:
            logger.error("health_summary_failed", error=str(e))
            return {"error": str(e)}

    def is_healthy(self) -> bool:
        """Check if system is in healthy state.

        Returns:
            True if overall status is HEALTHY
        """
        try:
            overall_status = self.get_overall_status()
            return overall_status == HealthStatus.HEALTHY
        except Exception as e:
            logger.error("is_healthy_check_failed", error=str(e))
            return False

    def is_degraded(self) -> bool:
        """Check if system is in degraded state.

        Returns:
            True if overall status is DEGRADED
        """
        try:
            overall_status = self.get_overall_status()
            return overall_status == HealthStatus.DEGRADED
        except Exception as e:
            logger.error("is_degraded_check_failed", error=str(e))
            return False

    def is_unhealthy(self) -> bool:
        """Check if system is in unhealthy state.

        Returns:
            True if overall status is UNHEALTHY
        """
        try:
            overall_status = self.get_overall_status()
            return overall_status == HealthStatus.UNHEALTHY
        except Exception as e:
            logger.error("is_unhealthy_check_failed", error=str(e))
            return True  # Fail safe: assume unhealthy on error
