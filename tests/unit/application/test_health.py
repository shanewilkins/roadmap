"""Tests for health check system."""

from pathlib import Path
from unittest.mock import patch

from roadmap.application.health import HealthCheck, HealthStatus


class TestHealthCheck:
    """Tests for HealthCheck class methods."""

    def test_check_roadmap_directory_healthy(self, tmp_path):
        """Test health check when .roadmap directory exists and is writable."""
        roadmap_dir = tmp_path / ".roadmap"
        roadmap_dir.mkdir()

        with patch("roadmap.application.health.Path") as mock_path:
            mock_path.return_value = roadmap_dir

            status, message = HealthCheck.check_roadmap_directory()

            assert status == HealthStatus.HEALTHY
            assert "accessible and writable" in message

    def test_check_roadmap_directory_not_initialized(self, tmp_path):
        """Test health check when .roadmap directory doesn't exist."""
        with patch("roadmap.application.health.Path") as mock_path:
            mock_path.return_value = tmp_path / "nonexistent"

            status, message = HealthCheck.check_roadmap_directory()

            assert status == HealthStatus.DEGRADED
            assert "not initialized" in message

    def test_check_roadmap_directory_not_directory(self, tmp_path):
        """Test health check when .roadmap exists but is not a directory."""
        roadmap_file = tmp_path / ".roadmap"
        roadmap_file.write_text("not a directory")

        with patch("roadmap.application.health.Path") as mock_path:
            mock_path.return_value = roadmap_file

            status, message = HealthCheck.check_roadmap_directory()

            assert status == HealthStatus.UNHEALTHY
            assert "not a directory" in message

    def test_check_state_file_healthy(self, tmp_path):
        """Test health check when state.yaml exists and is readable."""
        roadmap_dir = tmp_path / ".roadmap"
        roadmap_dir.mkdir()
        state_file = roadmap_dir / "state.yaml"
        state_file.write_text("project: test")

        with patch("roadmap.application.health.Path") as mock_path:
            mock_path.return_value = state_file

            status, message = HealthCheck.check_state_file()

            assert status == HealthStatus.HEALTHY
            assert "accessible and readable" in message

    def test_check_state_file_not_found(self, tmp_path):
        """Test health check when state.yaml doesn't exist."""
        with patch("roadmap.application.health.Path") as mock_path:
            mock_path.return_value = tmp_path / ".roadmap" / "state.yaml"

            status, message = HealthCheck.check_state_file()

            assert status == HealthStatus.DEGRADED
            assert "not found" in message

    def test_check_state_file_empty(self, tmp_path):
        """Test health check when state.yaml is empty."""
        roadmap_dir = tmp_path / ".roadmap"
        roadmap_dir.mkdir()
        state_file = roadmap_dir / "state.yaml"
        state_file.write_text("")

        with patch("roadmap.application.health.Path") as mock_path:
            mock_path.return_value = state_file

            status, message = HealthCheck.check_state_file()

            assert status == HealthStatus.DEGRADED
            assert "empty" in message

    def test_check_issues_directory_healthy(self, tmp_path):
        """Test health check when issues directory exists and is accessible."""
        issues_dir = tmp_path / ".roadmap" / "issues"
        issues_dir.mkdir(parents=True)

        with patch("roadmap.application.health.Path") as mock_path:
            mock_path.return_value = issues_dir

            status, message = HealthCheck.check_issues_directory()

            assert status == HealthStatus.HEALTHY
            assert "accessible" in message

    def test_check_issues_directory_not_found(self, tmp_path):
        """Test health check when issues directory doesn't exist."""
        with patch("roadmap.application.health.Path") as mock_path:
            mock_path.return_value = tmp_path / ".roadmap" / "issues"

            status, message = HealthCheck.check_issues_directory()

            assert status == HealthStatus.DEGRADED
            assert "not found" in message

    def test_check_milestones_directory_healthy(self, tmp_path):
        """Test health check when milestones directory exists and is accessible."""
        milestones_dir = tmp_path / ".roadmap" / "milestones"
        milestones_dir.mkdir(parents=True)

        with patch("roadmap.application.health.Path") as mock_path:
            mock_path.return_value = milestones_dir

            status, message = HealthCheck.check_milestones_directory()

            assert status == HealthStatus.HEALTHY
            assert "accessible" in message

    def test_check_milestones_directory_not_found(self, tmp_path):
        """Test health check when milestones directory doesn't exist."""
        with patch("roadmap.application.health.Path") as mock_path:
            mock_path.return_value = tmp_path / ".roadmap" / "milestones"

            status, message = HealthCheck.check_milestones_directory()

            assert status == HealthStatus.DEGRADED
            assert "not found" in message

    def test_check_git_repository_healthy(self, tmp_path):
        """Test health check when .git directory exists with HEAD."""
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        head_file = git_dir / "HEAD"
        head_file.write_text("ref: refs/heads/master")

        with patch("roadmap.application.health.Path") as mock_path:
            mock_path.side_effect = lambda p: (
                git_dir
                if str(p) == ".git"
                else head_file
                if str(p).endswith("HEAD")
                else Path(str(p))
            )

            status, message = HealthCheck.check_git_repository()

            assert status == HealthStatus.HEALTHY
            assert "accessible" in message

    def test_check_git_repository_not_initialized(self, tmp_path):
        """Test health check when Git repository doesn't exist."""
        with patch("roadmap.application.health.Path") as mock_path:
            mock_path.return_value = tmp_path / ".git"

            status, message = HealthCheck.check_git_repository()

            assert status == HealthStatus.DEGRADED
            assert "not initialized" in message

    def test_run_all_checks(self):
        """Test running all health checks."""
        with (
            patch.object(HealthCheck, "check_roadmap_directory") as mock_roadmap,
            patch.object(HealthCheck, "check_state_file") as mock_state,
            patch.object(HealthCheck, "check_issues_directory") as mock_issues,
            patch.object(HealthCheck, "check_milestones_directory") as mock_milestones,
            patch.object(HealthCheck, "check_git_repository") as mock_git,
        ):
            # Set up mock returns
            mock_roadmap.return_value = (HealthStatus.HEALTHY, "OK")
            mock_state.return_value = (HealthStatus.HEALTHY, "OK")
            mock_issues.return_value = (HealthStatus.HEALTHY, "OK")
            mock_milestones.return_value = (HealthStatus.HEALTHY, "OK")
            mock_git.return_value = (HealthStatus.HEALTHY, "OK")

            checks = HealthCheck.run_all_checks()

            # Verify all checks were called
            mock_roadmap.assert_called_once()
            mock_state.assert_called_once()
            mock_issues.assert_called_once()
            mock_milestones.assert_called_once()
            mock_git.assert_called_once()

            # Verify results structure
            assert "roadmap_directory" in checks
            assert "state_file" in checks
            assert "issues_directory" in checks
            assert "milestones_directory" in checks
            assert "git_repository" in checks

            # All should be healthy
            for status, _ in checks.values():
                assert status == HealthStatus.HEALTHY

    def test_get_overall_status_all_healthy(self):
        """Test overall status when all checks are healthy."""
        checks = {
            "check1": (HealthStatus.HEALTHY, "OK"),
            "check2": (HealthStatus.HEALTHY, "OK"),
            "check3": (HealthStatus.HEALTHY, "OK"),
        }

        overall = HealthCheck.get_overall_status(checks)

        assert overall == HealthStatus.HEALTHY

    def test_get_overall_status_one_degraded(self):
        """Test overall status when one check is degraded."""
        checks = {
            "check1": (HealthStatus.HEALTHY, "OK"),
            "check2": (HealthStatus.DEGRADED, "Warning"),
            "check3": (HealthStatus.HEALTHY, "OK"),
        }

        overall = HealthCheck.get_overall_status(checks)

        assert overall == HealthStatus.DEGRADED

    def test_get_overall_status_one_unhealthy(self):
        """Test overall status when one check is unhealthy."""
        checks = {
            "check1": (HealthStatus.HEALTHY, "OK"),
            "check2": (HealthStatus.DEGRADED, "Warning"),
            "check3": (HealthStatus.UNHEALTHY, "Error"),
        }

        overall = HealthCheck.get_overall_status(checks)

        assert overall == HealthStatus.UNHEALTHY

    def test_get_overall_status_multiple_unhealthy(self):
        """Test overall status with multiple unhealthy checks."""
        checks = {
            "check1": (HealthStatus.UNHEALTHY, "Error 1"),
            "check2": (HealthStatus.DEGRADED, "Warning"),
            "check3": (HealthStatus.UNHEALTHY, "Error 2"),
        }

        overall = HealthCheck.get_overall_status(checks)

        assert overall == HealthStatus.UNHEALTHY


class TestHealthStatusEnum:
    """Tests for HealthStatus enum."""

    def test_health_status_values(self):
        """Test that HealthStatus enum has expected values."""
        assert HealthStatus.HEALTHY.value == "healthy"
        assert HealthStatus.DEGRADED.value == "degraded"
        assert HealthStatus.UNHEALTHY.value == "unhealthy"

    def test_health_status_comparison(self):
        """Test comparing health statuses."""
        assert HealthStatus.HEALTHY == HealthStatus.HEALTHY
        assert HealthStatus.HEALTHY != HealthStatus.DEGRADED
        assert HealthStatus.DEGRADED != HealthStatus.UNHEALTHY
