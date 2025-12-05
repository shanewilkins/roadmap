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

from roadmap.application.services.infrastructure_validator_service import (
    DatabaseIntegrityValidator,
    GitRepositoryValidator,
    HealthStatus,
    InfrastructureValidator,
    IssuesDirectoryValidator,
    MilestonesDirectoryValidator,
    RoadmapDirectoryValidator,
    StateFileValidator,
)


class TestRoadmapDirectoryValidator:
    """Tests for RoadmapDirectoryValidator."""

    @patch("roadmap.application.services.infrastructure_validator_service.Path")
    def test_check_roadmap_directory_healthy(self, mock_path):
        """Test healthy .roadmap directory."""
        mock_dir = MagicMock()
        mock_dir.exists.return_value = True
        mock_dir.is_dir.return_value = True
        mock_test_file = MagicMock()
        mock_dir.__truediv__.return_value = mock_test_file
        mock_path.return_value = mock_dir

        status, message = RoadmapDirectoryValidator.check_roadmap_directory()

        assert status == HealthStatus.HEALTHY
        assert "accessible" in message.lower()
        mock_test_file.touch.assert_called_once()
        mock_test_file.unlink.assert_called_once()

    @patch("roadmap.application.services.infrastructure_validator_service.Path")
    def test_check_roadmap_directory_not_exists(self, mock_path):
        """Test missing .roadmap directory."""
        mock_dir = MagicMock()
        mock_dir.exists.return_value = False
        mock_path.return_value = mock_dir

        status, message = RoadmapDirectoryValidator.check_roadmap_directory()

        assert status == HealthStatus.DEGRADED
        assert "not initialized" in message.lower()

    @patch("roadmap.application.services.infrastructure_validator_service.Path")
    def test_check_roadmap_directory_not_a_directory(self, mock_path):
        """Test .roadmap exists but is not a directory."""
        mock_dir = MagicMock()
        mock_dir.exists.return_value = True
        mock_dir.is_dir.return_value = False
        mock_path.return_value = mock_dir

        status, message = RoadmapDirectoryValidator.check_roadmap_directory()

        assert status == HealthStatus.UNHEALTHY
        assert "not a directory" in message.lower()

    @patch("roadmap.application.services.infrastructure_validator_service.Path")
    def test_check_roadmap_directory_not_writable(self, mock_path):
        """Test .roadmap directory is not writable."""
        mock_dir = MagicMock()
        mock_dir.exists.return_value = True
        mock_dir.is_dir.return_value = True
        mock_test_file = MagicMock()
        mock_test_file.touch.side_effect = OSError("Permission denied")
        mock_dir.__truediv__.return_value = mock_test_file
        mock_path.return_value = mock_dir

        status, message = RoadmapDirectoryValidator.check_roadmap_directory()

        assert status == HealthStatus.DEGRADED
        assert "not writable" in message.lower()

    @patch("roadmap.application.services.infrastructure_validator_service.Path")
    def test_check_roadmap_directory_exception(self, mock_path):
        """Test exception handling in roadmap directory check."""
        mock_path.side_effect = Exception("Unexpected error")

        status, message = RoadmapDirectoryValidator.check_roadmap_directory()

        assert status == HealthStatus.UNHEALTHY
        assert "Error checking .roadmap directory" in message


class TestStateFileValidator:
    """Tests for StateFileValidator."""

    @patch("roadmap.application.services.infrastructure_validator_service.Path")
    @patch("builtins.open", create=True)
    def test_check_state_file_healthy(self, mock_open_func, mock_path):
        """Test healthy state.db file."""
        mock_file = MagicMock()
        mock_file.stat.return_value.st_size = 1024
        mock_file.read.return_value = b"SQLite format 3"
        mock_path.return_value = mock_file
        mock_file.exists.return_value = True
        mock_file.stat.return_value.st_size = 1024

        mock_open_func.return_value.__enter__ = MagicMock(return_value=mock_file)
        mock_open_func.return_value.__exit__ = MagicMock(return_value=False)

        # Mock open
        with patch(
            "builtins.open",
            MagicMock(
                return_value=MagicMock(
                    __enter__=MagicMock(
                        return_value=MagicMock(read=MagicMock(return_value=b"SQLite"))
                    ),
                    __exit__=MagicMock(return_value=False),
                )
            ),
        ):
            status, message = StateFileValidator.check_state_file()

        assert status == HealthStatus.HEALTHY
        assert "accessible" in message.lower()

    @patch("roadmap.application.services.infrastructure_validator_service.Path")
    def test_check_state_file_not_exists(self, mock_path):
        """Test missing state.db file."""
        mock_file = MagicMock()
        mock_file.exists.return_value = False
        mock_path.return_value = mock_file

        status, message = StateFileValidator.check_state_file()

        assert status == HealthStatus.DEGRADED
        assert "not found" in message.lower()

    @patch("roadmap.application.services.infrastructure_validator_service.Path")
    def test_check_state_file_empty(self, mock_path):
        """Test empty state.db file."""
        mock_file = MagicMock()
        mock_file.exists.return_value = True
        mock_file.stat.return_value.st_size = 0
        mock_path.return_value = mock_file

        status, message = StateFileValidator.check_state_file()

        assert status == HealthStatus.DEGRADED
        assert "empty" in message.lower()

    @patch("builtins.open", side_effect=OSError("Permission denied"))
    @patch("roadmap.application.services.infrastructure_validator_service.Path")
    def test_check_state_file_not_readable(self, mock_path, mock_open):
        """Test state.db file is not readable."""
        mock_file = MagicMock()
        mock_file.exists.return_value = True
        mock_file.stat.return_value.st_size = 1024
        mock_path.return_value = mock_file

        status, message = StateFileValidator.check_state_file()

        assert status == HealthStatus.UNHEALTHY
        assert "Cannot read state.db" in message

    @patch("roadmap.application.services.infrastructure_validator_service.Path")
    def test_check_state_file_exception(self, mock_path):
        """Test exception handling in state file check."""
        mock_path.side_effect = Exception("Unexpected error")

        status, message = StateFileValidator.check_state_file()

        assert status == HealthStatus.UNHEALTHY
        assert "Error checking state.db" in message


class TestIssuesDirectoryValidator:
    """Tests for IssuesDirectoryValidator."""

    @patch("roadmap.application.services.infrastructure_validator_service.Path")
    def test_check_issues_directory_healthy(self, mock_path):
        """Test healthy issues directory."""
        mock_dir = MagicMock()
        mock_dir.exists.return_value = True
        mock_dir.is_dir.return_value = True
        mock_dir.iterdir.return_value = iter([])
        mock_path.return_value = mock_dir

        status, message = IssuesDirectoryValidator.check_issues_directory()

        assert status == HealthStatus.HEALTHY
        assert "accessible" in message.lower()

    @patch("roadmap.application.services.infrastructure_validator_service.Path")
    def test_check_issues_directory_not_exists(self, mock_path):
        """Test missing issues directory."""
        mock_dir = MagicMock()
        mock_dir.exists.return_value = False
        mock_path.return_value = mock_dir

        status, message = IssuesDirectoryValidator.check_issues_directory()

        assert status == HealthStatus.DEGRADED
        assert "not found" in message.lower()

    @patch("roadmap.application.services.infrastructure_validator_service.Path")
    def test_check_issues_directory_not_a_directory(self, mock_path):
        """Test issues path exists but is not a directory."""
        mock_dir = MagicMock()
        mock_dir.exists.return_value = True
        mock_dir.is_dir.return_value = False
        mock_path.return_value = mock_dir

        status, message = IssuesDirectoryValidator.check_issues_directory()

        assert status == HealthStatus.UNHEALTHY
        assert "not a directory" in message.lower()

    @patch("roadmap.application.services.infrastructure_validator_service.Path")
    def test_check_issues_directory_not_readable(self, mock_path):
        """Test issues directory is not readable."""
        mock_dir = MagicMock()
        mock_dir.exists.return_value = True
        mock_dir.is_dir.return_value = True
        mock_dir.iterdir.side_effect = OSError("Permission denied")
        mock_path.return_value = mock_dir

        status, message = IssuesDirectoryValidator.check_issues_directory()

        assert status == HealthStatus.UNHEALTHY
        assert "Cannot read issues directory" in message

    @patch("roadmap.application.services.infrastructure_validator_service.Path")
    def test_check_issues_directory_exception(self, mock_path):
        """Test exception handling in issues directory check."""
        mock_path.side_effect = Exception("Unexpected error")

        status, message = IssuesDirectoryValidator.check_issues_directory()

        assert status == HealthStatus.UNHEALTHY
        assert "Error checking issues directory" in message


class TestMilestonesDirectoryValidator:
    """Tests for MilestonesDirectoryValidator."""

    @patch("roadmap.application.services.infrastructure_validator_service.Path")
    def test_check_milestones_directory_healthy(self, mock_path):
        """Test healthy milestones directory."""
        mock_dir = MagicMock()
        mock_dir.exists.return_value = True
        mock_dir.is_dir.return_value = True
        mock_dir.iterdir.return_value = iter([])
        mock_path.return_value = mock_dir

        status, message = MilestonesDirectoryValidator.check_milestones_directory()

        assert status == HealthStatus.HEALTHY
        assert "accessible" in message.lower()

    @patch("roadmap.application.services.infrastructure_validator_service.Path")
    def test_check_milestones_directory_not_exists(self, mock_path):
        """Test missing milestones directory."""
        mock_dir = MagicMock()
        mock_dir.exists.return_value = False
        mock_path.return_value = mock_dir

        status, message = MilestonesDirectoryValidator.check_milestones_directory()

        assert status == HealthStatus.DEGRADED
        assert "not found" in message.lower()

    @patch("roadmap.application.services.infrastructure_validator_service.Path")
    def test_check_milestones_directory_not_a_directory(self, mock_path):
        """Test milestones path exists but is not a directory."""
        mock_dir = MagicMock()
        mock_dir.exists.return_value = True
        mock_dir.is_dir.return_value = False
        mock_path.return_value = mock_dir

        status, message = MilestonesDirectoryValidator.check_milestones_directory()

        assert status == HealthStatus.UNHEALTHY
        assert "not a directory" in message.lower()

    @patch("roadmap.application.services.infrastructure_validator_service.Path")
    def test_check_milestones_directory_not_readable(self, mock_path):
        """Test milestones directory is not readable."""
        mock_dir = MagicMock()
        mock_dir.exists.return_value = True
        mock_dir.is_dir.return_value = True
        mock_dir.iterdir.side_effect = OSError("Permission denied")
        mock_path.return_value = mock_dir

        status, message = MilestonesDirectoryValidator.check_milestones_directory()

        assert status == HealthStatus.UNHEALTHY
        assert "Cannot read milestones directory" in message

    @patch("roadmap.application.services.infrastructure_validator_service.Path")
    def test_check_milestones_directory_exception(self, mock_path):
        """Test exception handling in milestones directory check."""
        mock_path.side_effect = Exception("Unexpected error")

        status, message = MilestonesDirectoryValidator.check_milestones_directory()

        assert status == HealthStatus.UNHEALTHY
        assert "Error checking milestones directory" in message


class TestGitRepositoryValidator:
    """Tests for GitRepositoryValidator."""

    @patch("roadmap.application.services.infrastructure_validator_service.Path")
    def test_check_git_repository_healthy(self, mock_path):
        """Test healthy Git repository."""
        mock_dir = MagicMock()
        mock_dir.exists.return_value = True
        mock_dir.is_dir.return_value = True
        mock_path.return_value = mock_dir

        status, message = GitRepositoryValidator.check_git_repository()

        assert status == HealthStatus.HEALTHY
        assert "accessible" in message.lower()

    @patch("roadmap.application.services.infrastructure_validator_service.Path")
    def test_check_git_repository_not_exists(self, mock_path):
        """Test missing Git repository."""
        mock_dir = MagicMock()
        mock_dir.exists.return_value = False
        mock_path.return_value = mock_dir

        status, message = GitRepositoryValidator.check_git_repository()

        assert status == HealthStatus.DEGRADED
        assert ".git not found" in message

    @patch("roadmap.application.services.infrastructure_validator_service.Path")
    def test_check_git_repository_not_a_directory(self, mock_path):
        """Test .git exists but is not a directory."""
        mock_dir = MagicMock()
        mock_dir.exists.return_value = True
        mock_dir.is_dir.return_value = False
        mock_path.return_value = mock_dir

        status, message = GitRepositoryValidator.check_git_repository()

        assert status == HealthStatus.UNHEALTHY
        assert "not a directory" in message.lower()

    @patch("roadmap.application.services.infrastructure_validator_service.Path")
    def test_check_git_repository_exception(self, mock_path):
        """Test exception handling in Git repository check."""
        mock_path.side_effect = Exception("Unexpected error")

        status, message = GitRepositoryValidator.check_git_repository()

        assert status == HealthStatus.UNHEALTHY
        assert "Error checking Git repository" in message


class TestDatabaseIntegrityValidator:
    """Tests for DatabaseIntegrityValidator."""

    @patch("roadmap.infrastructure.storage.StateManager")
    def test_check_database_integrity_healthy(self, mock_state_manager_class):
        """Test healthy database."""
        mock_state_mgr = MagicMock()
        mock_conn = MagicMock()
        mock_state_mgr._get_connection.return_value = mock_conn
        mock_state_manager_class.return_value = mock_state_mgr

        status, message = DatabaseIntegrityValidator.check_database_integrity()

        assert status == HealthStatus.HEALTHY
        assert "accessible" in message.lower()
        mock_conn.execute.assert_called_once_with("SELECT 1")

    @patch("roadmap.infrastructure.storage.StateManager")
    def test_check_database_integrity_query_failed(self, mock_state_manager_class):
        """Test database query failure."""
        mock_state_mgr = MagicMock()
        mock_conn = MagicMock()
        mock_conn.execute.side_effect = Exception("Database locked")
        mock_state_mgr._get_connection.return_value = mock_conn
        mock_state_manager_class.return_value = mock_state_mgr

        status, message = DatabaseIntegrityValidator.check_database_integrity()

        assert status == HealthStatus.UNHEALTHY
        assert "Database query failed" in message

    @patch("roadmap.infrastructure.storage.StateManager")
    def test_check_database_integrity_initialization_failed(
        self, mock_state_manager_class
    ):
        """Test database initialization failure."""
        mock_state_manager_class.side_effect = Exception("Cannot connect")

        status, message = DatabaseIntegrityValidator.check_database_integrity()

        assert status == HealthStatus.UNHEALTHY
        # Can be either message since the exception can be caught at either level
        assert (
            "Error checking database integrity" in message
            or "Database query failed" in message
        )


class TestInfrastructureValidator:
    """Tests for InfrastructureValidator orchestrator."""

    @patch.object(RoadmapDirectoryValidator, "check_roadmap_directory")
    @patch.object(StateFileValidator, "check_state_file")
    @patch.object(IssuesDirectoryValidator, "check_issues_directory")
    @patch.object(MilestonesDirectoryValidator, "check_milestones_directory")
    @patch.object(GitRepositoryValidator, "check_git_repository")
    @patch.object(DatabaseIntegrityValidator, "check_database_integrity")
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

    @patch.object(RoadmapDirectoryValidator, "check_roadmap_directory")
    @patch.object(StateFileValidator, "check_state_file")
    @patch.object(IssuesDirectoryValidator, "check_issues_directory")
    @patch.object(MilestonesDirectoryValidator, "check_milestones_directory")
    @patch.object(GitRepositoryValidator, "check_git_repository")
    @patch.object(DatabaseIntegrityValidator, "check_database_integrity")
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

    @patch.object(RoadmapDirectoryValidator, "check_roadmap_directory")
    @patch.object(StateFileValidator, "check_state_file")
    @patch.object(IssuesDirectoryValidator, "check_issues_directory")
    @patch.object(MilestonesDirectoryValidator, "check_milestones_directory")
    @patch.object(GitRepositoryValidator, "check_git_repository")
    @patch.object(DatabaseIntegrityValidator, "check_database_integrity")
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

    @patch.object(RoadmapDirectoryValidator, "check_roadmap_directory")
    @patch.object(StateFileValidator, "check_state_file")
    @patch.object(IssuesDirectoryValidator, "check_issues_directory")
    @patch.object(MilestonesDirectoryValidator, "check_milestones_directory")
    @patch.object(GitRepositoryValidator, "check_git_repository")
    @patch.object(DatabaseIntegrityValidator, "check_database_integrity")
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

    @patch.object(RoadmapDirectoryValidator, "check_roadmap_directory")
    @patch.object(StateFileValidator, "check_state_file")
    @patch.object(IssuesDirectoryValidator, "check_issues_directory")
    @patch.object(MilestonesDirectoryValidator, "check_milestones_directory")
    @patch.object(GitRepositoryValidator, "check_git_repository")
    @patch.object(DatabaseIntegrityValidator, "check_database_integrity")
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

    @patch.object(RoadmapDirectoryValidator, "check_roadmap_directory")
    @patch.object(StateFileValidator, "check_state_file")
    @patch.object(IssuesDirectoryValidator, "check_issues_directory")
    @patch.object(MilestonesDirectoryValidator, "check_milestones_directory")
    @patch.object(GitRepositoryValidator, "check_git_repository")
    @patch.object(DatabaseIntegrityValidator, "check_database_integrity")
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
