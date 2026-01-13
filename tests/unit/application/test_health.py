"""Tests for health check system."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from roadmap.core.domain.health import HealthStatus
from roadmap.infrastructure.health import HealthCheck
from tests.unit.domain.test_data_factory_generation import TestDataFactory


class TestHealthCheck:
    """Tests for HealthCheck class methods."""

    def test_check_roadmap_directory_healthy(self, tmp_path):
        """Test health check when .roadmap directory exists and is writable."""
        roadmap_dir = tmp_path / ".roadmap"
        roadmap_dir.mkdir()

        with patch(
            "roadmap.core.services.health.infrastructure_validator_service.Path"
        ) as mock_path:
            mock_dir = mock_path.return_value
            mock_dir.exists.return_value = True
            mock_dir.is_dir.return_value = True
            mock_dir.__truediv__.return_value = MagicMock()

            status, message = HealthCheck.check_roadmap_directory()

            assert status == HealthStatus.HEALTHY
            assert "accessible" in message.lower()

    def test_check_roadmap_directory_not_initialized(self, tmp_path):
        """Test health check when .roadmap directory doesn't exist."""
        with patch(
            "roadmap.core.services.health.infrastructure_validator_service.Path"
        ) as mock_path:
            mock_dir = mock_path.return_value
            mock_dir.exists.return_value = False

            status, message = HealthCheck.check_roadmap_directory()

            assert status == HealthStatus.DEGRADED
            assert "not initialized" in message

    def test_check_roadmap_directory_not_directory(self, tmp_path):
        """Test health check when .roadmap exists but is not a directory."""
        with patch(
            "roadmap.core.services.health.infrastructure_validator_service.Path"
        ) as mock_path:
            mock_dir = mock_path.return_value
            mock_dir.exists.return_value = True
            mock_dir.is_dir.return_value = False

            status, message = HealthCheck.check_roadmap_directory()

            assert status == HealthStatus.UNHEALTHY
            assert "not a directory" in message

    def test_check_state_file_healthy(self, tmp_path):
        """Test health check when state.db exists and is readable."""
        roadmap_dir = tmp_path / ".roadmap"
        db_dir = roadmap_dir / "db"
        db_dir.mkdir(parents=True)
        # Create a valid SQLite database file
        import sqlite3

        db_file = db_dir / "state.db"
        conn = sqlite3.connect(str(db_file))
        conn.execute("CREATE TABLE test (id INTEGER)")
        conn.close()

        with patch(
            "roadmap.core.services.health.infrastructure_validator_service.Path"
        ) as mock_path:
            mock_path.return_value = db_file

            status, message = HealthCheck.check_state_file()

            assert status == HealthStatus.HEALTHY
            assert "accessible and readable" in message

    def test_check_state_file_not_found(self, tmp_path):
        """Test health check when state.db doesn't exist."""
        with patch(
            "roadmap.core.services.health.infrastructure_validator_service.Path"
        ) as mock_path:
            mock_path.return_value = tmp_path / ".roadmap" / "db" / "state.db"

            status, message = HealthCheck.check_state_file()

            assert status == HealthStatus.DEGRADED
            assert "not found" in message

    def test_check_state_file_empty(self, tmp_path):
        """Test health check when state.db is empty."""
        roadmap_dir = tmp_path / ".roadmap"
        db_dir = roadmap_dir / "db"
        db_dir.mkdir(parents=True)
        state_file = db_dir / "state.db"
        state_file.write_text("")

        with patch(
            "roadmap.core.services.health.infrastructure_validator_service.Path"
        ) as mock_path:
            mock_path.return_value = state_file

            status, message = HealthCheck.check_state_file()

            assert status == HealthStatus.DEGRADED
            assert "empty" in message

    def test_check_issues_directory_healthy(self, tmp_path):
        """Test health check when issues directory exists and is accessible."""
        issues_dir = tmp_path / ".roadmap" / "issues"
        issues_dir.mkdir(parents=True)

        with patch(
            "roadmap.core.services.health.infrastructure_validator_service.Path"
        ) as mock_path:
            mock_path.return_value = issues_dir

            status, message = HealthCheck.check_issues_directory()

            assert status == HealthStatus.HEALTHY
            assert "accessible" in message

    def test_check_issues_directory_not_found(self, tmp_path):
        """Test health check when issues directory doesn't exist."""
        with patch(
            "roadmap.core.services.health.infrastructure_validator_service.Path"
        ) as mock_path:
            mock_path.return_value = tmp_path / ".roadmap" / "issues"

            status, message = HealthCheck.check_issues_directory()

            assert status == HealthStatus.DEGRADED
            assert "not found" in message

    def test_check_milestones_directory_healthy(self, tmp_path):
        """Test health check when milestones directory exists and is accessible."""
        milestones_dir = tmp_path / ".roadmap" / "milestones"
        milestones_dir.mkdir(parents=True)

        with patch(
            "roadmap.core.services.health.infrastructure_validator_service.Path"
        ) as mock_path:
            mock_path.return_value = milestones_dir

            status, message = HealthCheck.check_milestones_directory()

            assert status == HealthStatus.HEALTHY
            assert "accessible" in message

    def test_check_milestones_directory_not_found(self, tmp_path):
        """Test health check when milestones directory doesn't exist."""
        with patch(
            "roadmap.core.services.health.infrastructure_validator_service.Path"
        ) as mock_path:
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

        with patch(
            "roadmap.core.services.health.infrastructure_validator_service.Path"
        ) as mock_path:
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
        with patch(
            "roadmap.core.services.health.infrastructure_validator_service.Path"
        ) as mock_path:
            mock_dir = mock_path.return_value
            mock_dir.exists.return_value = False

            status, message = HealthCheck.check_git_repository()

            assert status == HealthStatus.DEGRADED
            assert ".git not found" in message

    def test_run_all_checks_calls_no_param_checks(self):
        """Test that run_all_checks calls checks that take no parameters."""

        with (
            patch.object(HealthCheck, "check_roadmap_directory") as mock_roadmap,
            patch.object(HealthCheck, "check_state_file") as mock_state,
            patch.object(HealthCheck, "check_issues_directory") as mock_issues,
            patch.object(HealthCheck, "check_milestones_directory") as mock_milestones,
            patch.object(HealthCheck, "check_git_repository") as mock_git,
            patch.object(HealthCheck, "check_database_integrity") as mock_db,
            patch.object(HealthCheck, "check_data_integrity") as mock_data,
            patch.object(HealthCheck, "check_duplicate_issues") as mock_duplicates,
            patch.object(HealthCheck, "check_folder_structure") as mock_folders,
            patch.object(HealthCheck, "check_orphaned_issues") as mock_orphaned,
            patch.object(HealthCheck, "check_old_backups") as mock_backups,
            patch.object(HealthCheck, "check_archivable_issues") as mock_arch_issues,
            patch.object(
                HealthCheck, "check_archivable_milestones"
            ) as mock_arch_milestones,
        ):
            # Set up mock returns
            ok_status: tuple[HealthStatus, str] = (HealthStatus.HEALTHY, "OK")
            mock_roadmap.return_value = ok_status
            mock_state.return_value = ok_status
            mock_issues.return_value = ok_status
            mock_milestones.return_value = ok_status
            mock_git.return_value = ok_status
            mock_db.return_value = ok_status
            mock_data.return_value = ok_status
            mock_duplicates.return_value = ok_status
            mock_folders.return_value = ok_status
            mock_orphaned.return_value = ok_status
            mock_backups.return_value = ok_status
            mock_arch_issues.return_value = ok_status
            mock_arch_milestones.return_value = ok_status

            # Create mock core
            mock_core = TestDataFactory.create_mock_core(is_initialized=True)

            HealthCheck.run_all_checks(mock_core)

            # Verify no-param checks were called
            mock_roadmap.assert_called_once()
            mock_state.assert_called_once()
            mock_issues.assert_called_once()
            mock_milestones.assert_called_once()
            mock_git.assert_called_once()
            mock_db.assert_called_once()
            mock_data.assert_called_once()
            mock_backups.assert_called_once()

    def test_run_all_checks_calls_core_param_checks(self):
        """Test that run_all_checks calls checks that take core parameter."""

        with (
            patch.object(HealthCheck, "check_roadmap_directory") as mock_roadmap,
            patch.object(HealthCheck, "check_state_file") as mock_state,
            patch.object(HealthCheck, "check_issues_directory") as mock_issues,
            patch.object(HealthCheck, "check_milestones_directory") as mock_milestones,
            patch.object(HealthCheck, "check_git_repository") as mock_git,
            patch.object(HealthCheck, "check_database_integrity") as mock_db,
            patch.object(HealthCheck, "check_data_integrity") as mock_data,
            patch.object(HealthCheck, "check_duplicate_issues") as mock_duplicates,
            patch.object(HealthCheck, "check_folder_structure") as mock_folders,
            patch.object(HealthCheck, "check_orphaned_issues") as mock_orphaned,
            patch.object(HealthCheck, "check_old_backups") as mock_backups,
            patch.object(HealthCheck, "check_archivable_issues") as mock_arch_issues,
            patch.object(
                HealthCheck, "check_archivable_milestones"
            ) as mock_arch_milestones,
        ):
            # Set up mock returns
            ok_status: tuple[HealthStatus, str] = (HealthStatus.HEALTHY, "OK")
            mock_roadmap.return_value = ok_status
            mock_state.return_value = ok_status
            mock_issues.return_value = ok_status
            mock_milestones.return_value = ok_status
            mock_git.return_value = ok_status
            mock_db.return_value = ok_status
            mock_data.return_value = ok_status
            mock_duplicates.return_value = ok_status
            mock_folders.return_value = ok_status
            mock_orphaned.return_value = ok_status
            mock_backups.return_value = ok_status
            mock_arch_issues.return_value = ok_status
            mock_arch_milestones.return_value = ok_status

            # Create mock core
            mock_core = TestDataFactory.create_mock_core(is_initialized=True)

            HealthCheck.run_all_checks(mock_core)

            # Verify core-param checks were called with core
            mock_duplicates.assert_called_once_with(mock_core)
            mock_folders.assert_called_once_with(mock_core)
            mock_orphaned.assert_called_once_with(mock_core)
            mock_arch_issues.assert_called_once_with(mock_core)
            mock_arch_milestones.assert_called_once_with(mock_core)

    def test_run_all_checks_returns_expected_structure(self):
        """Test that run_all_checks returns checks with expected keys."""

        with (
            patch.object(HealthCheck, "check_roadmap_directory") as mock_roadmap,
            patch.object(HealthCheck, "check_state_file") as mock_state,
            patch.object(HealthCheck, "check_issues_directory") as mock_issues,
            patch.object(HealthCheck, "check_milestones_directory") as mock_milestones,
            patch.object(HealthCheck, "check_git_repository") as mock_git,
            patch.object(HealthCheck, "check_database_integrity") as mock_db,
            patch.object(HealthCheck, "check_data_integrity") as mock_data,
            patch.object(HealthCheck, "check_duplicate_issues") as mock_duplicates,
            patch.object(HealthCheck, "check_folder_structure") as mock_folders,
            patch.object(HealthCheck, "check_orphaned_issues") as mock_orphaned,
            patch.object(HealthCheck, "check_old_backups") as mock_backups,
            patch.object(HealthCheck, "check_archivable_issues") as mock_arch_issues,
            patch.object(
                HealthCheck, "check_archivable_milestones"
            ) as mock_arch_milestones,
        ):
            # Set up mock returns
            ok_status: tuple[HealthStatus, str] = (HealthStatus.HEALTHY, "OK")
            mock_roadmap.return_value = ok_status
            mock_state.return_value = ok_status
            mock_issues.return_value = ok_status
            mock_milestones.return_value = ok_status
            mock_git.return_value = ok_status
            mock_db.return_value = ok_status
            mock_data.return_value = ok_status
            mock_duplicates.return_value = ok_status
            mock_folders.return_value = ok_status
            mock_orphaned.return_value = ok_status
            mock_backups.return_value = ok_status
            mock_arch_issues.return_value = ok_status
            mock_arch_milestones.return_value = ok_status

            # Create mock core
            mock_core = TestDataFactory.create_mock_core(is_initialized=True)

            checks = HealthCheck.run_all_checks(mock_core)

            # Verify results structure
            assert "roadmap_directory" in checks
            assert "state_file" in checks
            assert "issues_directory" in checks
            assert "milestones_directory" in checks
            assert "git_repository" in checks
            assert "duplicate_issues" in checks
            assert "folder_structure" in checks

    def test_run_all_checks_all_healthy(self):
        """Test that run_all_checks returns all healthy statuses."""

        with (
            patch.object(HealthCheck, "check_roadmap_directory") as mock_roadmap,
            patch.object(HealthCheck, "check_state_file") as mock_state,
            patch.object(HealthCheck, "check_issues_directory") as mock_issues,
            patch.object(HealthCheck, "check_milestones_directory") as mock_milestones,
            patch.object(HealthCheck, "check_git_repository") as mock_git,
            patch.object(HealthCheck, "check_database_integrity") as mock_db,
            patch.object(HealthCheck, "check_data_integrity") as mock_data,
            patch.object(HealthCheck, "check_duplicate_issues") as mock_duplicates,
            patch.object(
                HealthCheck, "check_duplicate_milestones"
            ) as mock_dup_milestones,
            patch.object(HealthCheck, "check_folder_structure") as mock_folders,
            patch.object(HealthCheck, "check_orphaned_issues") as mock_orphaned,
            patch.object(
                HealthCheck, "check_orphaned_milestones"
            ) as mock_orp_milestones,
            patch.object(HealthCheck, "check_old_backups") as mock_backups,
            patch.object(HealthCheck, "check_archivable_issues") as mock_arch_issues,
            patch.object(
                HealthCheck, "check_archivable_milestones"
            ) as mock_arch_milestones,
            patch.object(HealthCheck, "check_unlinked_issues") as mock_unlinked,
        ):
            # Set up mock returns
            ok_status: tuple[HealthStatus, str] = (HealthStatus.HEALTHY, "OK")
            mock_roadmap.return_value = ok_status
            mock_state.return_value = ok_status
            mock_issues.return_value = ok_status
            mock_milestones.return_value = ok_status
            mock_git.return_value = ok_status
            mock_db.return_value = ok_status
            mock_data.return_value = ok_status
            mock_duplicates.return_value = ok_status
            mock_dup_milestones.return_value = ok_status
            mock_folders.return_value = ok_status
            mock_orphaned.return_value = ok_status
            mock_orp_milestones.return_value = ok_status
            mock_backups.return_value = ok_status
            mock_arch_issues.return_value = ok_status
            mock_arch_milestones.return_value = ok_status
            mock_unlinked.return_value = ok_status

            # Create mock core
            mock_core = TestDataFactory.create_mock_core(is_initialized=True)

            checks = HealthCheck.run_all_checks(mock_core)

            # All should be healthy
            for status, _ in checks.values():
                assert status == HealthStatus.HEALTHY

    def test_get_overall_status_all_healthy(self):
        """Test overall status when all checks are healthy."""
        checks: dict[str, tuple[HealthStatus, str]] = {
            "check1": (HealthStatus.HEALTHY, "OK"),
            "check2": (HealthStatus.HEALTHY, "OK"),
            "check3": (HealthStatus.HEALTHY, "OK"),
        }

        overall = HealthCheck.get_overall_status(checks)

        assert overall == HealthStatus.HEALTHY

    def test_get_overall_status_one_degraded(self):
        """Test overall status when one check is degraded."""
        checks: dict[str, tuple[HealthStatus, str]] = {
            "check1": (HealthStatus.HEALTHY, "OK"),
            "check2": (HealthStatus.DEGRADED, "Warning"),
            "check3": (HealthStatus.HEALTHY, "OK"),
        }

        overall = HealthCheck.get_overall_status(checks)

        assert overall == HealthStatus.DEGRADED

    def test_get_overall_status_one_unhealthy(self):
        """Test overall status when one check is unhealthy."""
        checks: dict[str, tuple[HealthStatus, str]] = {
            "check1": (HealthStatus.HEALTHY, "OK"),
            "check2": (HealthStatus.DEGRADED, "Warning"),
            "check3": (HealthStatus.UNHEALTHY, "Error"),
        }

        overall = HealthCheck.get_overall_status(checks)

        assert overall == HealthStatus.UNHEALTHY

    def test_get_overall_status_multiple_unhealthy(self):
        """Test overall status with multiple unhealthy checks."""
        checks: dict[str, tuple[HealthStatus, str]] = {
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
