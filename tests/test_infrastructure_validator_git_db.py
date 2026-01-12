"""
Tests for infrastructure validators.

Covers:
- RoadmapDirectoryValidator
- StateFileValidator
- IssuesDirectoryValidator
- MilestonesDirectoryValidator
- GitRepositoryValidator
- DatabaseIntegrityValidator
- InfrastructureValidator orchestrator
"""

from unittest.mock import MagicMock, patch

import pytest

from roadmap.core.services.health.infrastructure_validator_service import (
    DatabaseIntegrityValidator,
    GitRepositoryValidator,
    HealthStatus,
    InfrastructureValidator,
    IssuesDirectoryValidator,
    MilestonesDirectoryValidator,
    RoadmapDirectoryValidator,
    StateFileValidator,
)


class TestIssuesDirectoryValidator:
    """Tests for IssuesDirectoryValidator."""

    @patch("roadmap.core.services.health.infrastructure_validator_service.Path")
    @pytest.mark.parametrize(
        "mock_setup,expected_status,expected_message_part",
        [
            ("healthy", HealthStatus.HEALTHY, "accessible"),
            ("not_exists", HealthStatus.DEGRADED, "not found"),
            ("not_directory", HealthStatus.UNHEALTHY, "not a directory"),
            ("not_readable", HealthStatus.UNHEALTHY, "Cannot read"),
            ("exception", HealthStatus.UNHEALTHY, "Error checking"),
        ],
    )
    def test_check_issues_directory(
        self, mock_path, mock_setup, expected_status, expected_message_part
    ):
        """Test issues directory validation with various scenarios."""
        mock_dir = MagicMock()

        if mock_setup == "healthy":
            mock_dir.exists.return_value = True
            mock_dir.is_dir.return_value = True
            mock_dir.iterdir.return_value = iter([])
            mock_path.return_value = mock_dir

        elif mock_setup == "not_exists":
            mock_dir.exists.return_value = False
            mock_path.return_value = mock_dir

        elif mock_setup == "not_directory":
            mock_dir.exists.return_value = True
            mock_dir.is_dir.return_value = False
            mock_path.return_value = mock_dir

        elif mock_setup == "not_readable":
            mock_dir.exists.return_value = True
            mock_dir.is_dir.return_value = True
            mock_dir.iterdir.side_effect = OSError("Permission denied")
            mock_path.return_value = mock_dir

        elif mock_setup == "exception":
            mock_path.side_effect = Exception("Unexpected error")

        status, message = IssuesDirectoryValidator.check()

        assert status == expected_status
        assert expected_message_part.lower() in message.lower()


class TestMilestonesDirectoryValidator:
    """Tests for MilestonesDirectoryValidator."""

    @patch("roadmap.core.services.health.infrastructure_validator_service.Path")
    @pytest.mark.parametrize(
        "mock_setup,expected_status,expected_message_part",
        [
            ("healthy", HealthStatus.HEALTHY, "accessible"),
            ("not_exists", HealthStatus.DEGRADED, "not found"),
            ("not_directory", HealthStatus.UNHEALTHY, "not a directory"),
            ("not_readable", HealthStatus.UNHEALTHY, "Cannot read"),
            ("exception", HealthStatus.UNHEALTHY, "Error checking"),
        ],
    )
    def test_check_milestones_directory(
        self, mock_path, mock_setup, expected_status, expected_message_part
    ):
        """Test milestones directory validation with various scenarios."""
        mock_dir = MagicMock()

        if mock_setup == "healthy":
            mock_dir.exists.return_value = True
            mock_dir.is_dir.return_value = True
            mock_dir.iterdir.return_value = iter([])
            mock_path.return_value = mock_dir

        elif mock_setup == "not_exists":
            mock_dir.exists.return_value = False
            mock_path.return_value = mock_dir

        elif mock_setup == "not_directory":
            mock_dir.exists.return_value = True
            mock_dir.is_dir.return_value = False
            mock_path.return_value = mock_dir

        elif mock_setup == "not_readable":
            mock_dir.exists.return_value = True
            mock_dir.is_dir.return_value = True
            mock_dir.iterdir.side_effect = OSError("Permission denied")
            mock_path.return_value = mock_dir

        elif mock_setup == "exception":
            mock_path.side_effect = Exception("Unexpected error")

        status, message = MilestonesDirectoryValidator.check()

        assert status == expected_status
        assert expected_message_part.lower() in message.lower()


class TestGitRepositoryValidator:
    """Tests for GitRepositoryValidator."""

    @patch("roadmap.core.services.health.infrastructure_validator_service.Path")
    @pytest.mark.parametrize(
        "mock_setup,expected_status,expected_message_part",
        [
            ("healthy", HealthStatus.HEALTHY, "accessible"),
            ("not_exists", HealthStatus.DEGRADED, ".git not found"),
            ("not_directory", HealthStatus.UNHEALTHY, "not a directory"),
            ("exception", HealthStatus.UNHEALTHY, "Error checking"),
        ],
    )
    def test_check_git_repository(
        self, mock_path, mock_setup, expected_status, expected_message_part
    ):
        """Test git repository validation with various scenarios."""
        mock_dir = MagicMock()

        if mock_setup == "healthy":
            mock_dir.exists.return_value = True
            mock_dir.is_dir.return_value = True
            mock_path.return_value = mock_dir

        elif mock_setup == "not_exists":
            mock_dir.exists.return_value = False
            mock_path.return_value = mock_dir

        elif mock_setup == "not_directory":
            mock_dir.exists.return_value = True
            mock_dir.is_dir.return_value = False
            mock_path.return_value = mock_dir

        elif mock_setup == "exception":
            mock_path.side_effect = Exception("Unexpected error")

        status, message = GitRepositoryValidator.check()

        assert status == expected_status
        assert expected_message_part.lower() in message.lower()


class TestDatabaseIntegrityValidator:
    """Tests for DatabaseIntegrityValidator."""

    @patch("roadmap.adapters.persistence.storage.StateManager")
    @pytest.mark.parametrize(
        "mock_setup,expected_status,expected_message_part",
        [
            ("healthy", HealthStatus.HEALTHY, "accessible"),
            ("query_failed", HealthStatus.UNHEALTHY, "Database query failed"),
            ("init_failed", HealthStatus.UNHEALTHY, "query failed"),
        ],
    )
    def test_check_database_integrity(
        self,
        mock_state_manager_class,
        mock_setup,
        expected_status,
        expected_message_part,
    ):
        """Test database integrity validation with various scenarios."""
        if mock_setup == "healthy":
            mock_state_mgr = MagicMock()
            mock_conn = MagicMock()
            mock_state_mgr._get_connection.return_value = mock_conn
            mock_state_manager_class.return_value = mock_state_mgr

        elif mock_setup == "query_failed":
            mock_state_mgr = MagicMock()
            mock_conn = MagicMock()
            mock_conn.execute.side_effect = Exception("Database locked")
            mock_state_mgr._get_connection.return_value = mock_conn
            mock_state_manager_class.return_value = mock_state_mgr

        elif mock_setup == "init_failed":
            mock_state_manager_class.side_effect = Exception("Cannot connect")

        status, message = DatabaseIntegrityValidator.check()

        assert status == expected_status
        assert expected_message_part.lower() in message.lower()


class TestInfrastructureValidator:
    """Tests for InfrastructureValidator orchestrator."""

    @patch.object(RoadmapDirectoryValidator, "check")
    @patch.object(StateFileValidator, "check")
    @patch.object(IssuesDirectoryValidator, "check")
    @patch.object(MilestonesDirectoryValidator, "check")
    @patch.object(GitRepositoryValidator, "check")
    @patch.object(DatabaseIntegrityValidator, "check")
    def test_run_all_infrastructure_checks_all_healthy(
        self,
        mock_db_check,
        mock_git_check,
        mock_milestones_check,
        mock_issues_check,
        mock_state_check,
        mock_roadmap_check,
    ):
        """Test all checks passing."""
        mock_roadmap_check.return_value = (HealthStatus.HEALTHY, "Roadmap OK")
        mock_state_check.return_value = (HealthStatus.HEALTHY, "State OK")
        mock_issues_check.return_value = (HealthStatus.HEALTHY, "Issues OK")
        mock_milestones_check.return_value = (HealthStatus.HEALTHY, "Milestones OK")
        mock_git_check.return_value = (HealthStatus.HEALTHY, "Git OK")
        mock_db_check.return_value = (HealthStatus.HEALTHY, "DB OK")

        validator = InfrastructureValidator()
        checks = validator.run_all_infrastructure_checks()

        assert checks["roadmap_directory"] == (HealthStatus.HEALTHY, "Roadmap OK")
        assert checks["state_file"] == (HealthStatus.HEALTHY, "State OK")
        assert checks["issues_directory"] == (HealthStatus.HEALTHY, "Issues OK")
        assert checks["milestones_directory"] == (HealthStatus.HEALTHY, "Milestones OK")
        assert checks["git_repository"] == (HealthStatus.HEALTHY, "Git OK")
        assert checks["database_integrity"] == (HealthStatus.HEALTHY, "DB OK")

    @patch.object(RoadmapDirectoryValidator, "check")
    @patch.object(StateFileValidator, "check")
    @patch.object(IssuesDirectoryValidator, "check")
    @patch.object(MilestonesDirectoryValidator, "check")
    @patch.object(GitRepositoryValidator, "check")
    @patch.object(DatabaseIntegrityValidator, "check")
    def test_run_all_infrastructure_checks_mixed_status(
        self,
        mock_db_check,
        mock_git_check,
        mock_milestones_check,
        mock_issues_check,
        mock_state_check,
        mock_roadmap_check,
    ):
        """Test checks with mixed status."""
        mock_roadmap_check.return_value = (HealthStatus.HEALTHY, "Roadmap OK")
        mock_state_check.return_value = (HealthStatus.DEGRADED, "State degraded")
        mock_issues_check.return_value = (HealthStatus.HEALTHY, "Issues OK")
        mock_milestones_check.return_value = (HealthStatus.UNHEALTHY, "Milestones FAIL")
        mock_git_check.return_value = (HealthStatus.HEALTHY, "Git OK")
        mock_db_check.return_value = (HealthStatus.HEALTHY, "DB OK")

        validator = InfrastructureValidator()
        checks = validator.run_all_infrastructure_checks()

        assert checks["roadmap_directory"][0] == HealthStatus.HEALTHY
        assert checks["state_file"][0] == HealthStatus.DEGRADED
        assert checks["issues_directory"][0] == HealthStatus.HEALTHY
        assert checks["milestones_directory"][0] == HealthStatus.UNHEALTHY
        assert checks["git_repository"][0] == HealthStatus.HEALTHY
        assert checks["database_integrity"][0] == HealthStatus.HEALTHY

    @patch.object(RoadmapDirectoryValidator, "check")
    @patch.object(StateFileValidator, "check")
    @patch.object(IssuesDirectoryValidator, "check")
    @patch.object(MilestonesDirectoryValidator, "check")
    @patch.object(GitRepositoryValidator, "check")
    @patch.object(DatabaseIntegrityValidator, "check")
    def test_run_all_infrastructure_checks_exception(
        self,
        mock_db_check,
        mock_git_check,
        mock_milestones_check,
        mock_issues_check,
        mock_state_check,
        mock_roadmap_check,
    ):
        """Test exception during checks."""
        mock_roadmap_check.side_effect = Exception("Unexpected error")
        mock_state_check.return_value = (HealthStatus.HEALTHY, "State OK")
        mock_issues_check.return_value = (HealthStatus.HEALTHY, "Issues OK")
        mock_milestones_check.return_value = (HealthStatus.HEALTHY, "Milestones OK")
        mock_git_check.return_value = (HealthStatus.HEALTHY, "Git OK")
        mock_db_check.return_value = (HealthStatus.HEALTHY, "DB OK")

        validator = InfrastructureValidator()
        checks = validator.run_all_infrastructure_checks()

        assert "error" in checks
        assert checks["error"][0] == HealthStatus.UNHEALTHY

    @patch.object(RoadmapDirectoryValidator, "check")
    @patch.object(StateFileValidator, "check")
    @patch.object(IssuesDirectoryValidator, "check")
    @patch.object(MilestonesDirectoryValidator, "check")
    @patch.object(GitRepositoryValidator, "check")
    @patch.object(DatabaseIntegrityValidator, "check")
    def test_get_overall_status_all_healthy(
        self,
        mock_db_check,
        mock_git_check,
        mock_milestones_check,
        mock_issues_check,
        mock_state_check,
        mock_roadmap_check,
    ):
        """Test overall status with all healthy."""
        mock_roadmap_check.return_value = (HealthStatus.HEALTHY, "OK")
        mock_state_check.return_value = (HealthStatus.HEALTHY, "OK")
        mock_issues_check.return_value = (HealthStatus.HEALTHY, "OK")
        mock_milestones_check.return_value = (HealthStatus.HEALTHY, "OK")
        mock_git_check.return_value = (HealthStatus.HEALTHY, "OK")
        mock_db_check.return_value = (HealthStatus.HEALTHY, "OK")

        validator = InfrastructureValidator()
        checks = validator.run_all_infrastructure_checks()
        overall_status = validator.get_overall_status(checks)

        assert overall_status == HealthStatus.HEALTHY

    @patch.object(RoadmapDirectoryValidator, "check")
    @patch.object(StateFileValidator, "check")
    @patch.object(IssuesDirectoryValidator, "check")
    @patch.object(MilestonesDirectoryValidator, "check")
    @patch.object(GitRepositoryValidator, "check")
    @patch.object(DatabaseIntegrityValidator, "check")
    def test_get_overall_status_degraded(
        self,
        mock_db_check,
        mock_git_check,
        mock_milestones_check,
        mock_issues_check,
        mock_state_check,
        mock_roadmap_check,
    ):
        """Test overall status with degraded."""
        mock_roadmap_check.return_value = (HealthStatus.HEALTHY, "OK")
        mock_state_check.return_value = (HealthStatus.DEGRADED, "Degraded")
        mock_issues_check.return_value = (HealthStatus.HEALTHY, "OK")
        mock_milestones_check.return_value = (HealthStatus.HEALTHY, "OK")
        mock_git_check.return_value = (HealthStatus.HEALTHY, "OK")
        mock_db_check.return_value = (HealthStatus.HEALTHY, "OK")

        validator = InfrastructureValidator()
        checks = validator.run_all_infrastructure_checks()
        overall_status = validator.get_overall_status(checks)

        assert overall_status == HealthStatus.DEGRADED

    @patch.object(RoadmapDirectoryValidator, "check")
    @patch.object(StateFileValidator, "check")
    @patch.object(IssuesDirectoryValidator, "check")
    @patch.object(MilestonesDirectoryValidator, "check")
    @patch.object(GitRepositoryValidator, "check")
    @patch.object(DatabaseIntegrityValidator, "check")
    def test_get_overall_status_unhealthy(
        self,
        mock_db_check,
        mock_git_check,
        mock_milestones_check,
        mock_issues_check,
        mock_state_check,
        mock_roadmap_check,
    ):
        """Test overall status with unhealthy."""
        mock_roadmap_check.return_value = (HealthStatus.HEALTHY, "OK")
        mock_state_check.return_value = (HealthStatus.UNHEALTHY, "Failed")
        mock_issues_check.return_value = (HealthStatus.HEALTHY, "OK")
        mock_milestones_check.return_value = (HealthStatus.HEALTHY, "OK")
        mock_git_check.return_value = (HealthStatus.HEALTHY, "OK")
        mock_db_check.return_value = (HealthStatus.HEALTHY, "OK")

        validator = InfrastructureValidator()
        checks = validator.run_all_infrastructure_checks()
        overall_status = validator.get_overall_status(checks)

        assert overall_status == HealthStatus.UNHEALTHY

    def test_get_overall_status_empty_checks(self):
        """Test overall status with empty checks."""
        validator = InfrastructureValidator()
        overall_status = validator.get_overall_status({})

        assert overall_status == HealthStatus.UNHEALTHY
