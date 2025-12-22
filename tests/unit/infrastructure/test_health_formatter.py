"""Tests for health status formatter."""

from roadmap.core.domain.health import HealthStatus
from roadmap.infrastructure.health_formatter import HealthStatusFormatter


class TestHealthStatusFormatter:
    """Test HealthStatusFormatter class."""

    def test_summarize_health_checks_all_healthy(self):
        """Test summarizing all healthy checks."""
        checks = {
            "check1": (HealthStatus.HEALTHY, "All good"),
            "check2": (HealthStatus.HEALTHY, "All good"),
            "check3": (HealthStatus.HEALTHY, "All good"),
        }
        result = HealthStatusFormatter.summarize_health_checks(checks)
        assert result["total"] == 3
        assert result["healthy"] == 3
        assert result["degraded"] == 0
        assert result["unhealthy"] == 0

    def test_summarize_health_checks_all_unhealthy(self):
        """Test summarizing all unhealthy checks."""
        checks = {
            "check1": (HealthStatus.UNHEALTHY, "Critical error"),
            "check2": (HealthStatus.UNHEALTHY, "Critical error"),
        }
        result = HealthStatusFormatter.summarize_health_checks(checks)
        assert result["total"] == 2
        assert result["healthy"] == 0
        assert result["degraded"] == 0
        assert result["unhealthy"] == 2

    def test_summarize_health_checks_mixed(self):
        """Test summarizing mixed health status checks."""
        checks = {
            "check1": (HealthStatus.HEALTHY, "All good"),
            "check2": (HealthStatus.DEGRADED, "Minor issue"),
            "check3": (HealthStatus.UNHEALTHY, "Critical error"),
            "check4": (HealthStatus.HEALTHY, "All good"),
            "check5": (HealthStatus.DEGRADED, "Minor issue"),
        }
        result = HealthStatusFormatter.summarize_health_checks(checks)
        assert result["total"] == 5
        assert result["healthy"] == 2
        assert result["degraded"] == 2
        assert result["unhealthy"] == 1

    def test_summarize_health_checks_empty(self):
        """Test summarizing empty checks."""
        checks = {}
        result = HealthStatusFormatter.summarize_health_checks(checks)
        assert result["total"] == 0
        assert result["healthy"] == 0
        assert result["degraded"] == 0
        assert result["unhealthy"] == 0

    def test_get_status_color_healthy(self):
        """Test getting color for healthy status."""
        color = HealthStatusFormatter.get_status_color(HealthStatus.HEALTHY)
        assert color == "\033[92m"  # Green

    def test_get_status_color_degraded(self):
        """Test getting color for degraded status."""
        color = HealthStatusFormatter.get_status_color(HealthStatus.DEGRADED)
        assert color == "\033[93m"  # Yellow

    def test_get_status_color_unhealthy(self):
        """Test getting color for unhealthy status."""
        color = HealthStatusFormatter.get_status_color(HealthStatus.UNHEALTHY)
        assert color == "\033[91m"  # Red

    def test_format_status_display_healthy(self):
        """Test formatting healthy status display."""
        display = HealthStatusFormatter.format_status_display(HealthStatus.HEALTHY)
        assert display == "HEALTHY"

    def test_format_status_display_degraded(self):
        """Test formatting degraded status display."""
        display = HealthStatusFormatter.format_status_display(HealthStatus.DEGRADED)
        assert display == "DEGRADED"

    def test_format_status_display_unhealthy(self):
        """Test formatting unhealthy status display."""
        display = HealthStatusFormatter.format_status_display(HealthStatus.UNHEALTHY)
        assert display == "UNHEALTHY"
