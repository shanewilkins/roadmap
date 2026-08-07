"""Health status utilities for validators.

Common utilities for determining overall health status from individual checks.
"""

from roadmap.core.services.validator_base import HealthStatus


def get_overall_status(checks: dict) -> str:
    """Get overall status from all validation checks.

    Args:
        checks: Dictionary of check results with (status, message) tuples

    Returns:
        Overall status: 'healthy', 'degraded', or 'unhealthy'
    """
    if not checks:
        return HealthStatus.UNHEALTHY

    statuses = [status for status, _ in checks.values()]

    if HealthStatus.UNHEALTHY in statuses:
        return HealthStatus.UNHEALTHY
    elif HealthStatus.DEGRADED in statuses:
        return HealthStatus.DEGRADED
    else:
        return HealthStatus.HEALTHY
