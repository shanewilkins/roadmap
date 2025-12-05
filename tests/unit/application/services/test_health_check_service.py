"""Tests for HealthCheckService."""

from unittest.mock import Mock, patch

import pytest

from roadmap.application.core import RoadmapCore
from roadmap.application.health import HealthCheck, HealthStatus
from roadmap.application.services.health_check_service import HealthCheckService


class TestHealthCheckService:
    """Test suite for HealthCheckService."""

    @pytest.fixture
    def mock_core(self):
        """Create a mock RoadmapCore."""
        return Mock(spec=RoadmapCore)

    @pytest.fixture
    def service(self, mock_core):
        """Create a service instance with mocked core."""
        return HealthCheckService(core=mock_core)

    @pytest.fixture
    def mock_checks(self):
        """Create mock health checks data."""
        return {
            "roadmap_directory": (HealthStatus.HEALTHY, "Roadmap directory OK"),
            "database": (HealthStatus.HEALTHY, "Database connection OK"),
            "file_sync": (HealthStatus.DEGRADED, "File sync lag detected"),
        }

    def test_init_stores_core(self, mock_core):
        """Test that core is stored during initialization."""
        service = HealthCheckService(core=mock_core)
        assert service.core is mock_core

    def test_run_all_checks_returns_dict(self, service, mock_checks):
        """Test that run_all_checks returns a dictionary."""
        with patch.object(HealthCheck, "run_all_checks", return_value=mock_checks):
            result = service.run_all_checks()
            assert isinstance(result, dict)
            assert len(result) == 3

    def test_run_all_checks_has_tuples(self, service, mock_checks):
        """Test that checks contain (status, message) tuples."""
        with patch.object(HealthCheck, "run_all_checks", return_value=mock_checks):
            checks = service.run_all_checks()
            for _, (status, message) in checks.items():
                assert isinstance(status, HealthStatus)
                assert isinstance(message, str)

    def test_get_overall_status_healthy(self, service, mock_checks):
        """Test overall status calculation for healthy system."""
        healthy_checks = {
            "check1": (HealthStatus.HEALTHY, "OK"),
            "check2": (HealthStatus.HEALTHY, "OK"),
        }
        with patch.object(
            HealthCheck, "get_overall_status", return_value=HealthStatus.HEALTHY
        ):
            status = service.get_overall_status(healthy_checks)
            assert status == HealthStatus.HEALTHY

    def test_get_overall_status_degraded(self, service, mock_checks):
        """Test overall status calculation for degraded system."""
        with patch.object(
            HealthCheck, "get_overall_status", return_value=HealthStatus.DEGRADED
        ):
            status = service.get_overall_status(mock_checks)
            assert status == HealthStatus.DEGRADED

    def test_get_overall_status_unhealthy(self, service):
        """Test overall status calculation for unhealthy system."""
        unhealthy_checks = {
            "check1": (HealthStatus.UNHEALTHY, "Failed"),
        }
        with patch.object(
            HealthCheck, "get_overall_status", return_value=HealthStatus.UNHEALTHY
        ):
            status = service.get_overall_status(unhealthy_checks)
            assert status == HealthStatus.UNHEALTHY

    def test_get_overall_status_runs_checks_if_none(self, service, mock_checks):
        """Test that get_overall_status runs checks if not provided."""
        with patch.object(HealthCheck, "run_all_checks", return_value=mock_checks):
            with patch.object(
                HealthCheck, "get_overall_status", return_value=HealthStatus.DEGRADED
            ):
                status = service.get_overall_status(checks=None)
                assert status == HealthStatus.DEGRADED

    def test_get_check_status_found(self, service, mock_checks):
        """Test retrieving a specific check status."""
        with patch.object(HealthCheck, "run_all_checks", return_value=mock_checks):
            result = service.get_check_status("database")
            assert result == (HealthStatus.HEALTHY, "Database connection OK")

    def test_get_check_status_not_found(self, service, mock_checks):
        """Test retrieving a non-existent check."""
        with patch.object(HealthCheck, "run_all_checks", return_value=mock_checks):
            result = service.get_check_status("nonexistent")
            assert result is None

    def test_get_health_summary_returns_dict(self, service, mock_checks):
        """Test that get_health_summary returns a dictionary."""
        with patch.object(HealthCheck, "run_all_checks", return_value=mock_checks):
            with patch.object(
                HealthCheck, "get_overall_status", return_value=HealthStatus.DEGRADED
            ):
                result = service.get_health_summary()
                assert isinstance(result, dict)

    def test_get_health_summary_contains_overall_status(self, service, mock_checks):
        """Test that summary contains overall_status."""
        with patch.object(HealthCheck, "run_all_checks", return_value=mock_checks):
            with patch.object(
                HealthCheck, "get_overall_status", return_value=HealthStatus.DEGRADED
            ):
                result = service.get_health_summary()
                assert "overall_status" in result
                assert result["overall_status"] == "degraded"

    def test_get_health_summary_contains_checks(self, service, mock_checks):
        """Test that summary contains check results."""
        with patch.object(HealthCheck, "run_all_checks", return_value=mock_checks):
            with patch.object(
                HealthCheck, "get_overall_status", return_value=HealthStatus.DEGRADED
            ):
                result = service.get_health_summary()
                assert "checks" in result
                assert result["checks"] == mock_checks

    def test_get_health_summary_contains_summary_stats(self, service, mock_checks):
        """Test that summary contains count statistics."""
        with patch.object(HealthCheck, "run_all_checks", return_value=mock_checks):
            with patch.object(
                HealthCheck, "get_overall_status", return_value=HealthStatus.DEGRADED
            ):
                result = service.get_health_summary()
                assert "summary" in result
                assert "total" in result["summary"]
                assert "healthy" in result["summary"]
                assert "degraded" in result["summary"]
                assert "unhealthy" in result["summary"]

    def test_get_health_summary_correct_counts(self, service, mock_checks):
        """Test that summary statistics are calculated correctly."""
        with patch.object(HealthCheck, "run_all_checks", return_value=mock_checks):
            with patch.object(
                HealthCheck, "get_overall_status", return_value=HealthStatus.DEGRADED
            ):
                result = service.get_health_summary()
                summary = result["summary"]
                assert summary["total"] == 3
                assert summary["healthy"] == 2
                assert summary["degraded"] == 1
                assert summary["unhealthy"] == 0

    def test_is_healthy_true(self, service):
        """Test is_healthy returns True for healthy system."""
        with patch.object(
            HealthCheck, "get_overall_status", return_value=HealthStatus.HEALTHY
        ):
            assert service.is_healthy() is True

    def test_is_healthy_false(self, service):
        """Test is_healthy returns False for non-healthy system."""
        with patch.object(
            HealthCheck, "get_overall_status", return_value=HealthStatus.DEGRADED
        ):
            assert service.is_healthy() is False

    def test_is_degraded_true(self, service):
        """Test is_degraded returns True for degraded system."""
        with patch.object(
            HealthCheck, "get_overall_status", return_value=HealthStatus.DEGRADED
        ):
            assert service.is_degraded() is True

    def test_is_degraded_false(self, service):
        """Test is_degraded returns False for non-degraded system."""
        with patch.object(
            HealthCheck, "get_overall_status", return_value=HealthStatus.HEALTHY
        ):
            assert service.is_degraded() is False

    def test_is_unhealthy_true(self, service):
        """Test is_unhealthy returns True for unhealthy system."""
        with patch.object(
            HealthCheck, "get_overall_status", return_value=HealthStatus.UNHEALTHY
        ):
            assert service.is_unhealthy() is True

    def test_is_unhealthy_false(self, service):
        """Test is_unhealthy returns False for healthy system."""
        with patch.object(
            HealthCheck, "get_overall_status", return_value=HealthStatus.HEALTHY
        ):
            assert service.is_unhealthy() is False

    def test_service_error_handling_run_checks(self, service):
        """Test error handling in run_all_checks."""
        with patch.object(
            HealthCheck, "run_all_checks", side_effect=Exception("Check failed")
        ):
            result = service.run_all_checks()
            assert isinstance(result, dict)
            assert len(result) == 0

    def test_service_error_handling_overall_status(self, service):
        """Test error handling in get_overall_status."""
        with patch.object(
            HealthCheck, "get_overall_status", side_effect=Exception("Status failed")
        ):
            result = service.get_overall_status({})
            assert result == HealthStatus.UNHEALTHY

    def test_service_error_handling_summary(self, service, mock_checks):
        """Test error handling in get_health_summary."""
        with patch.object(HealthCheck, "run_all_checks", return_value=mock_checks):
            with patch.object(
                HealthCheck, "get_overall_status", return_value=HealthStatus.DEGRADED
            ):
                # Service handles errors gracefully and returns dict
                result = service.get_health_summary()
                assert isinstance(result, dict)
                assert "overall_status" in result

    def test_service_maintains_core_reference(self, mock_core):
        """Test that service maintains core reference."""
        service = HealthCheckService(core=mock_core)
        assert service.core is mock_core

    def test_multiple_status_checks(self, service):
        """Test running multiple status checks."""
        with patch.object(
            HealthCheck, "get_overall_status", return_value=HealthStatus.HEALTHY
        ):
            result1 = service.is_healthy()
            result2 = service.is_degraded()
            result3 = service.is_unhealthy()

            assert result1 is True
            assert result2 is False
            assert result3 is False

    def test_check_status_error_handling(self, service):
        """Test error handling when retrieving specific check."""
        with patch.object(
            HealthCheck, "run_all_checks", side_effect=Exception("Check error")
        ):
            result = service.get_check_status("test")
            assert result is None

    def test_service_integration_full_workflow(self, service, mock_checks):
        """Test full health check workflow."""
        with patch.object(HealthCheck, "run_all_checks", return_value=mock_checks):
            with patch.object(
                HealthCheck, "get_overall_status", return_value=HealthStatus.DEGRADED
            ):
                # Run checks
                checks = service.run_all_checks()
                assert len(checks) > 0

                # Get overall status
                status = service.get_overall_status(checks)
                assert status == HealthStatus.DEGRADED

                # Get summary
                summary = service.get_health_summary()
                assert summary["overall_status"] == "degraded"

                # Check status flags
                assert service.is_degraded() is True
                assert service.is_healthy() is False
                assert service.is_unhealthy() is False
