"""Tests for health status utilities."""

from roadmap.core.services.base_validator import HealthStatus
from roadmap.core.services.validators.health_status_utils import get_overall_status


class TestGetOverallStatus:
    """Test get_overall_status function."""

    def test_get_overall_status_empty_checks(self):
        """Test with empty checks returns UNHEALTHY."""
        result = get_overall_status({})
        assert result == HealthStatus.UNHEALTHY

    def test_get_overall_status_all_healthy(self):
        """Test with all healthy checks returns HEALTHY."""
        checks = {
            "check1": (HealthStatus.HEALTHY, "All good"),
            "check2": (HealthStatus.HEALTHY, "All good"),
            "check3": (HealthStatus.HEALTHY, "All good"),
        }
        result = get_overall_status(checks)
        assert result == HealthStatus.HEALTHY

    def test_get_overall_status_single_unhealthy(self):
        """Test with one unhealthy check returns UNHEALTHY."""
        checks = {
            "check1": (HealthStatus.HEALTHY, "All good"),
            "check2": (HealthStatus.UNHEALTHY, "Problem found"),
            "check3": (HealthStatus.HEALTHY, "All good"),
        }
        result = get_overall_status(checks)
        assert result == HealthStatus.UNHEALTHY

    def test_get_overall_status_all_unhealthy(self):
        """Test with all unhealthy checks returns UNHEALTHY."""
        checks = {
            "check1": (HealthStatus.UNHEALTHY, "Problem 1"),
            "check2": (HealthStatus.UNHEALTHY, "Problem 2"),
        }
        result = get_overall_status(checks)
        assert result == HealthStatus.UNHEALTHY

    def test_get_overall_status_degraded_priority(self):
        """Test that UNHEALTHY takes priority over DEGRADED."""
        checks = {
            "check1": (HealthStatus.DEGRADED, "Minor issue"),
            "check2": (HealthStatus.UNHEALTHY, "Major issue"),
            "check3": (HealthStatus.HEALTHY, "All good"),
        }
        result = get_overall_status(checks)
        assert result == HealthStatus.UNHEALTHY

    def test_get_overall_status_degraded_no_unhealthy(self):
        """Test with degraded but no unhealthy returns DEGRADED."""
        checks = {
            "check1": (HealthStatus.DEGRADED, "Minor issue"),
            "check2": (HealthStatus.HEALTHY, "All good"),
            "check3": (HealthStatus.HEALTHY, "All good"),
        }
        result = get_overall_status(checks)
        assert result == HealthStatus.DEGRADED

    def test_get_overall_status_multiple_degraded(self):
        """Test with multiple degraded checks returns DEGRADED."""
        checks = {
            "check1": (HealthStatus.DEGRADED, "Issue 1"),
            "check2": (HealthStatus.DEGRADED, "Issue 2"),
            "check3": (HealthStatus.HEALTHY, "All good"),
        }
        result = get_overall_status(checks)
        assert result == HealthStatus.DEGRADED

    def test_get_overall_status_single_check(self):
        """Test with single check."""
        checks = {"check1": (HealthStatus.DEGRADED, "Some issue")}
        result = get_overall_status(checks)
        assert result == HealthStatus.DEGRADED

    def test_get_overall_status_preserves_message_tuples(self):
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
