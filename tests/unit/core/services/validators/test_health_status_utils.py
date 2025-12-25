"""Tests for health status utilities."""

import pytest

from roadmap.core.services.base_validator import HealthStatus
from roadmap.core.services.validators.health_status_utils import get_overall_status


class TestGetOverallStatus:
    """Test get_overall_status function."""

    @pytest.mark.parametrize(
        "checks,expected_status",
        [
            ({}, HealthStatus.UNHEALTHY),  # empty
            (
                {
                    "check1": (HealthStatus.HEALTHY, "All good"),
                    "check2": (HealthStatus.HEALTHY, "All good"),
                    "check3": (HealthStatus.HEALTHY, "All good"),
                },
                HealthStatus.HEALTHY,
            ),  # all healthy
            (
                {
                    "check1": (HealthStatus.HEALTHY, "All good"),
                    "check2": (HealthStatus.UNHEALTHY, "Problem found"),
                    "check3": (HealthStatus.HEALTHY, "All good"),
                },
                HealthStatus.UNHEALTHY,
            ),  # one unhealthy
            (
                {
                    "check1": (HealthStatus.UNHEALTHY, "Problem 1"),
                    "check2": (HealthStatus.UNHEALTHY, "Problem 2"),
                },
                HealthStatus.UNHEALTHY,
            ),  # all unhealthy
            (
                {
                    "check1": (HealthStatus.DEGRADED, "Minor issue"),
                    "check2": (HealthStatus.UNHEALTHY, "Major issue"),
                    "check3": (HealthStatus.HEALTHY, "All good"),
                },
                HealthStatus.UNHEALTHY,
            ),  # degraded + unhealthy priority
            (
                {
                    "check1": (HealthStatus.DEGRADED, "Minor issue"),
                    "check2": (HealthStatus.HEALTHY, "All good"),
                    "check3": (HealthStatus.HEALTHY, "All good"),
                },
                HealthStatus.DEGRADED,
            ),  # degraded no unhealthy
            (
                {
                    "check1": (HealthStatus.DEGRADED, "Issue 1"),
                    "check2": (HealthStatus.DEGRADED, "Issue 2"),
                    "check3": (HealthStatus.HEALTHY, "All good"),
                },
                HealthStatus.DEGRADED,
            ),  # multiple degraded
            (
                {"check1": (HealthStatus.DEGRADED, "Some issue")},
                HealthStatus.DEGRADED,
            ),  # single check
        ],
    )
    def test_get_overall_status(self, checks, expected_status):
        """Test get_overall_status with various check combinations."""
        result = get_overall_status(checks)
        assert result == expected_status
        """Test that message part of tuple is preserved."""
        checks = {
            "check1": (HealthStatus.HEALTHY, "First message"),
            "check2": (HealthStatus.HEALTHY, "Second message"),
        }
        result = get_overall_status(checks)
        assert result == HealthStatus.HEALTHY
        # Messages are in the original checks dict
        assert checks["check1"][1] == "First message"
        assert checks["check2"][1] == "Second message"
