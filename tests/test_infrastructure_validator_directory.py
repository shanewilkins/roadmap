"""Tests for infrastructure validators.

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
    HealthStatus,
    RoadmapDirectoryValidator,
    StateFileValidator,
)


class TestRoadmapDirectoryValidator:
    """Tests for RoadmapDirectoryValidator."""

    @patch("roadmap.core.services.health.infrastructure_validator_service.Path")
    @pytest.mark.parametrize(
        "mock_setup,expected_status,expected_message_part",
        [
            ("healthy", HealthStatus.HEALTHY, "accessible"),
            ("not_exists", HealthStatus.DEGRADED, "not initialized"),
            ("not_directory", HealthStatus.UNHEALTHY, "not a directory"),
            ("not_writable", HealthStatus.DEGRADED, "not writable"),
            ("exception", HealthStatus.UNHEALTHY, "Error checking roadmap_directory"),
        ],
    )
    def test_check_roadmap_directory(
        self, mock_path, mock_setup, expected_status, expected_message_part
    ):
        """Test roadmap directory validation with various scenarios."""
        mock_dir = MagicMock()

        if mock_setup == "healthy":
            mock_dir.exists.return_value = True
            mock_dir.is_dir.return_value = True
            mock_test_file = MagicMock()
            mock_dir.__truediv__.return_value = mock_test_file
            mock_path.return_value = mock_dir

        elif mock_setup == "not_exists":
            mock_dir.exists.return_value = False
            mock_path.return_value = mock_dir

        elif mock_setup == "not_directory":
            mock_dir.exists.return_value = True
            mock_dir.is_dir.return_value = False
            mock_path.return_value = mock_dir

        elif mock_setup == "not_writable":
            mock_dir.exists.return_value = True
            mock_dir.is_dir.return_value = True
            mock_test_file = MagicMock()
            mock_test_file.touch.side_effect = OSError("Permission denied")
            mock_dir.__truediv__.return_value = mock_test_file
            mock_path.return_value = mock_dir

        elif mock_setup == "exception":
            mock_path.side_effect = Exception("Unexpected error")

        status, message = RoadmapDirectoryValidator.check()

        assert status == expected_status
        assert expected_message_part.lower() in message.lower()


class TestStateFileValidator:
    """Tests for StateFileValidator."""

    @patch("roadmap.core.services.health.infrastructure_validator_service.Path")
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
            status, message = StateFileValidator.check()

        assert status == HealthStatus.HEALTHY
        assert "accessible" in message.lower()

    @patch("roadmap.core.services.health.infrastructure_validator_service.Path")
    def test_check_state_file_not_exists(self, mock_path):
        """Test missing state.db file."""
        mock_file = MagicMock()
        mock_file.exists.return_value = False
        mock_path.return_value = mock_file

        status, message = StateFileValidator.check()

        assert status == HealthStatus.DEGRADED
        assert "not found" in message.lower()

    @patch("roadmap.core.services.health.infrastructure_validator_service.Path")
    def test_check_state_file_empty(self, mock_path):
        """Test empty state.db file."""
        mock_file = MagicMock()
        mock_file.exists.return_value = True
        mock_file.stat.return_value.st_size = 0
        mock_path.return_value = mock_file

        status, message = StateFileValidator.check()

        assert status == HealthStatus.DEGRADED
        assert "empty" in message.lower()

    @patch("builtins.open", side_effect=OSError("Permission denied"))
    @patch("roadmap.core.services.health.infrastructure_validator_service.Path")
    def test_check_state_file_not_readable(self, mock_path, mock_open):
        """Test state.db file is not readable."""
        mock_file = MagicMock()
        mock_file.exists.return_value = True
        mock_file.stat.return_value.st_size = 1024
        mock_path.return_value = mock_file

        status, message = StateFileValidator.check()

        assert status == HealthStatus.UNHEALTHY
        assert "Cannot read state.db" in message

    @patch("roadmap.core.services.health.infrastructure_validator_service.Path")
    def test_check_state_file_exception(self, mock_path):
        """Test exception handling in state file check."""
        mock_path.side_effect = Exception("Unexpected error")

        status, message = StateFileValidator.check()

        assert status == HealthStatus.UNHEALTHY
        assert "Error checking state_file" in message
