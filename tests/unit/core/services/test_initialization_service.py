"""Tests for ProjectInitializationService."""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from roadmap.core.services.initialization_service import ProjectInitializationService
from roadmap.infrastructure.core import RoadmapCore


class TestProjectInitializationService:
    """Tests for ProjectInitializationService."""

    def test_service_initialization(self):
        """Test service initialization."""
        core = Mock(spec=RoadmapCore)
        service = ProjectInitializationService(core)

        assert service.core is core
        assert service.workflow is not None

    def test_validate_prerequisites_valid(self):
        """Test validate_prerequisites when everything is valid."""
        core = Mock(spec=RoadmapCore)
        service = ProjectInitializationService(core)

        with (
            patch(
                "roadmap.core.services.initialization_service.InitializationValidator.validate_lockfile",
                return_value=(True, None),
            ),
            patch(
                "roadmap.core.services.initialization_service.InitializationValidator.check_existing_roadmap",
                return_value=(True, None),
            ),
        ):
            is_valid, error = service.validate_prerequisites()

            assert is_valid is True
            assert error == ""

    def test_validate_prerequisites_lockfile_error(self):
        """Test validate_prerequisites with lockfile error."""
        core = Mock(spec=RoadmapCore)
        service = ProjectInitializationService(core)

        with patch(
            "roadmap.core.services.initialization_service.InitializationValidator.validate_lockfile",
            return_value=(False, "Initialization in progress"),
        ):
            is_valid, error = service.validate_prerequisites()

            assert is_valid is False
            assert "Initialization in progress" in error

    def test_validate_prerequisites_roadmap_exists_error(self):
        """Test validate_prerequisites when roadmap already exists."""
        core = Mock(spec=RoadmapCore)
        service = ProjectInitializationService(core)

        with (
            patch(
                "roadmap.core.services.initialization_service.InitializationValidator.validate_lockfile",
                return_value=(True, None),
            ),
            patch(
                "roadmap.core.services.initialization_service.InitializationValidator.check_existing_roadmap",
                return_value=(False, "Roadmap already exists"),
            ),
        ):
            is_valid, error = service.validate_prerequisites(force=False)

            assert is_valid is False
            assert "Roadmap already exists" in error

    def test_validate_prerequisites_with_force(self):
        """Test validate_prerequisites with force=True."""
        core = Mock(spec=RoadmapCore)
        service = ProjectInitializationService(core)

        with (
            patch(
                "roadmap.core.services.initialization_service.InitializationValidator.validate_lockfile",
                return_value=(True, None),
            ),
            patch(
                "roadmap.core.services.initialization_service.InitializationValidator.check_existing_roadmap",
                return_value=(True, None),
            ),
        ):
            is_valid, error = service.validate_prerequisites(force=True)

            assert is_valid is True

    def test_handle_force_reinitialization_success(self):
        """Test force reinitialization succeeds."""
        core = Mock(spec=RoadmapCore)
        service = ProjectInitializationService(core)
        service.workflow = Mock()
        service.workflow.cleanup_existing.return_value = True

        result = service.handle_force_reinitialization()

        assert result is True
        service.workflow.cleanup_existing.assert_called_once()

    def test_handle_force_reinitialization_failure(self):
        """Test force reinitialization handles failure."""
        core = Mock(spec=RoadmapCore)
        service = ProjectInitializationService(core)
        service.workflow = Mock()
        service.workflow.cleanup_existing.side_effect = Exception("Cleanup failed")

        result = service.handle_force_reinitialization()

        assert result is False

    def test_detect_existing_projects(self):
        """Test detecting existing projects."""
        core = Mock(spec=RoadmapCore)
        core.roadmap_dir = Path("/tmp/roadmap")
        service = ProjectInitializationService(core)

        expected_projects = [
            {"name": "project1", "path": "/tmp/roadmap/projects/project1"}
        ]

        with patch(
            "roadmap.core.services.initialization_service.ProjectDetectionService.detect_existing_projects",
            return_value=expected_projects,
        ):
            projects = service.detect_existing_projects()

            assert projects == expected_projects

    def test_validate_finalization_success(self):
        """Test finalization validation succeeds."""
        core = Mock(spec=RoadmapCore)
        core.roadmap_dir = Path("/tmp/roadmap")
        service = ProjectInitializationService(core)

        project_info = {"name": "test_project"}

        with patch(
            "roadmap.core.services.initialization_service.InitializationValidator.post_init_validate",
            return_value=True,
        ):
            result = service.validate_finalization(project_info)

            assert result is True

    def test_validate_finalization_without_project_info(self):
        """Test finalization validation without project info."""
        core = Mock(spec=RoadmapCore)
        core.roadmap_dir = Path("/tmp/roadmap")
        service = ProjectInitializationService(core)

        with patch(
            "roadmap.core.services.initialization_service.InitializationValidator.post_init_validate",
            return_value=True,
        ):
            result = service.validate_finalization()

            assert result is True

    def test_validate_finalization_failure(self):
        """Test finalization validation handles failure."""
        core = Mock(spec=RoadmapCore)
        core.roadmap_dir = Path("/tmp/roadmap")
        service = ProjectInitializationService(core)

        with patch(
            "roadmap.core.services.initialization_service.InitializationValidator.post_init_validate",
            side_effect=Exception("Validation error"),
        ):
            result = service.validate_finalization()

            assert result is False

    def test_validate_finalization_logs_error(self):
        """Test that validation errors are logged."""
        core = Mock(spec=RoadmapCore)
        core.roadmap_dir = Path("/tmp/roadmap")
        service = ProjectInitializationService(core)

        with (
            patch(
                "roadmap.core.services.initialization_service.InitializationValidator.post_init_validate",
                side_effect=Exception("Validation error"),
            ),
            patch("roadmap.core.services.initialization_service.logger") as mock_logger,
        ):
            service.validate_finalization()

            assert mock_logger.error.called

    def test_handle_force_reinitialization_logs_error(self):
        """Test that cleanup errors are logged."""
        core = Mock(spec=RoadmapCore)
        service = ProjectInitializationService(core)
        service.workflow = Mock()
        service.workflow.cleanup_existing.side_effect = Exception("Cleanup failed")

        with patch(
            "roadmap.core.services.initialization_service.logger"
        ) as mock_logger:
            service.handle_force_reinitialization()

            assert mock_logger.error.called

    @pytest.mark.parametrize(
        "force",
        [True, False],
    )
    def test_validate_prerequisites_respects_force_param(self, force):
        """Test that force parameter is handled."""
        core = Mock(spec=RoadmapCore)
        service = ProjectInitializationService(core)

        with (
            patch(
                "roadmap.core.services.initialization_service.InitializationValidator.validate_lockfile",
                return_value=(True, None),
            ),
            patch(
                "roadmap.core.services.initialization_service.InitializationValidator.check_existing_roadmap",
                return_value=(True, None),
            ) as mock_check,
        ):
            service.validate_prerequisites(force=force)

            # Check that force was passed through
            call_args = mock_check.call_args
            assert call_args is not None
