"""Health status domain models.

This module defines health status enumerations used across the application
for reporting system and component health states.
"""

from enum import Enum


class HealthStatus(Enum):
    """Health status levels for system components."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
