"""Tests for ProjectInitializationService."""

from unittest.mock import Mock, patch

import pytest

from roadmap.core.services.initialization_service import (
    ProjectInitializationService,
)
from roadmap.infrastructure.core import RoadmapCore


class TestProjectInitializationService:
    """Test suite for ProjectInitializationService."""

    @pytest.fixture
    def mock_core(self):
        """Create a mock RoadmapCore."""
        return Mock(spec=RoadmapCore)

    @pytest.fixture
    def service(self, mock_core):
        """Create a service instance with mocked core."""
        with patch(
            "roadmap.core.services.initialization_service.InitializationWorkflow"
        ):
            return ProjectInitializationService(core=mock_core)

    def test_init_stores_core(self, mock_core):
        """Test that core is stored during initialization."""
        with patch(
            "roadmap.core.services.initialization_service.InitializationWorkflow"
        ):
            service = ProjectInitializationService(core=mock_core)
        assert service.core is mock_core

    def test_validate_prerequisites_returns_tuple(self, service):
        """Test that validate_prerequisites returns a tuple."""
        with patch(
            "roadmap.core.services.initialization_service.InitializationValidator"
        ) as mock_validator:
            mock_validator.validate_lockfile.return_value = (True, "")
            mock_validator.check_existing_roadmap.return_value = (True, "")

            result = service.validate_prerequisites(force=False)
            assert isinstance(result, tuple)
            assert len(result) == 2
            assert isinstance(result[0], bool)
            assert isinstance(result[1], str)

    def test_validate_prerequisites_force_flag(self, service):
        """Test that force flag is passed correctly."""
        with patch(
            "roadmap.core.services.initialization_service.InitializationValidator"
        ) as mock_validator:
            mock_validator.validate_lockfile.return_value = (True, "")
            mock_validator.check_existing_roadmap.return_value = (True, "")

            service.validate_prerequisites(force=True)
            mock_validator.check_existing_roadmap.assert_called_once_with(
                service.core, True
            )

    def test_service_has_core_attribute(self, service):
        """Test that service has core attribute."""
        assert hasattr(service, "core")
        assert service.core is not None

    def test_service_has_workflow_attribute(self, service):
        """Test that service has workflow attribute."""
        assert hasattr(service, "workflow")

    def test_validate_prerequisites_lockfile_validation(self, service):
        """Test lockfile validation in prerequisites."""
        with patch(
            "roadmap.core.services.initialization_service.InitializationValidator"
        ) as mock_validator:
            mock_validator.validate_lockfile.return_value = (False, "Lock file exists")
            mock_validator.check_existing_roadmap.return_value = (True, "")

            is_valid, error_msg = service.validate_prerequisites(force=False)
            assert not is_valid
            assert "Lock file" in error_msg

    def test_validate_prerequisites_existing_roadmap_check(self, service):
        """Test existing roadmap check in prerequisites."""
        with patch(
            "roadmap.core.services.initialization_service.InitializationValidator"
        ) as mock_validator:
            mock_validator.validate_lockfile.return_value = (True, "")
            mock_validator.check_existing_roadmap.return_value = (
                False,
                "Roadmap already exists",
            )

            is_valid, error_msg = service.validate_prerequisites(force=False)
            assert not is_valid
            assert "exists" in error_msg

    def test_service_integration_basic_workflow(self, service):
        """Test basic initialization workflow."""
        with patch(
            "roadmap.core.services.initialization_service.InitializationValidator"
        ) as mock_validator:
            mock_validator.validate_lockfile.return_value = (True, "")
            mock_validator.check_existing_roadmap.return_value = (True, "")

            # Validate prerequisites
            is_valid, error_msg = service.validate_prerequisites(force=False)
            assert is_valid

    def test_validate_prerequisites_without_force(self, service):
        """Test prerequisite validation without force flag."""
        with patch(
            "roadmap.core.services.initialization_service.InitializationValidator"
        ) as mock_validator:
            mock_validator.validate_lockfile.return_value = (True, "")
            mock_validator.check_existing_roadmap.return_value = (True, "")

            result = service.validate_prerequisites()
            assert result == (True, "")

    def test_service_maintains_core_reference(self, mock_core, service):
        """Test that service maintains core reference throughout lifecycle."""
        with patch(
            "roadmap.core.services.initialization_service.InitializationValidator"
        ) as mock_validator:
            mock_validator.validate_lockfile.return_value = (True, "")
            mock_validator.check_existing_roadmap.return_value = (True, "")

            service.validate_prerequisites(force=False)
            # Core reference should remain
            assert service.core is mock_core

    def test_error_handling_in_prerequisites(self, service):
        """Test error handling in validate_prerequisites."""
        with patch(
            "roadmap.core.services.initialization_service.InitializationValidator"
        ) as mock_validator:
            mock_validator.validate_lockfile.side_effect = ValueError(
                "Lockfile read error"
            )

            with pytest.raises(ValueError, match="Lockfile read error"):
                service.validate_prerequisites(force=False)

    def test_multiple_prerequisite_validation_calls(self, service):
        """Test that validate_prerequisites can be called multiple times."""
        with patch(
            "roadmap.core.services.initialization_service.InitializationValidator"
        ) as mock_validator:
            mock_validator.validate_lockfile.return_value = (True, "")
            mock_validator.check_existing_roadmap.return_value = (True, "")

            result1 = service.validate_prerequisites(force=False)
            result2 = service.validate_prerequisites(force=True)

            assert result1 == (True, "")
            assert result2 == (True, "")
