"""Tests for DuplicateMilestonesValidator."""

from unittest.mock import MagicMock, patch

from roadmap.core.services.base_validator import HealthStatus
from roadmap.core.services.validators import DuplicateMilestonesValidator
from tests.factories.domain import MilestoneBuilder


class TestDuplicateMilestonesValidator:
    """Test DuplicateMilestonesValidator."""

    def test_get_check_name(self):
        """Test get_check_name returns correct identifier."""
        assert DuplicateMilestonesValidator.get_check_name() == "duplicate_milestones"

    def test_scan_for_duplicate_files_no_duplicates(self, tmp_path):
        """Test scan_for_duplicate_files when no duplicates exist."""
        milestones_dir = tmp_path / "milestones"
        milestones_dir.mkdir()

        # Create unique milestone files
        (milestones_dir / "sprint-1.md").write_text("# Sprint 1")
        (milestones_dir / "sprint-2.md").write_text("# Sprint 2")

        duplicates = DuplicateMilestonesValidator.scan_for_duplicate_files(
            milestones_dir
        )

        assert len(duplicates) == 0

    def test_scan_for_duplicate_names_no_duplicates(self):
        """Test scan_for_duplicate_names when all names are unique."""
        mock_core = MagicMock()

        milestone1 = MilestoneBuilder().with_name("sprint-1").build()
        milestone2 = MilestoneBuilder().with_name("sprint-2").build()
        mock_core.milestones.list.return_value = [milestone1, milestone2]

        duplicates = DuplicateMilestonesValidator.scan_for_duplicate_names(mock_core)

        assert len(duplicates) == 0

    def test_scan_for_duplicate_names_finds_duplicates(self):
        """Test scan_for_duplicate_names finds milestones with same name."""
        mock_core = MagicMock()

        milestone1 = MilestoneBuilder().with_name("sprint-1").build()
        milestone2 = MilestoneBuilder().with_name("sprint-1").build()  # Duplicate name

        mock_core.milestones.list.return_value = [milestone1, milestone2]

        duplicates = DuplicateMilestonesValidator.scan_for_duplicate_names(mock_core)

        assert len(duplicates) == 1
        assert duplicates[0]["name"] == "sprint-1"
        assert duplicates[0]["count"] == 2

    def test_perform_check_not_initialized(self):
        """Test perform_check when milestones directory doesn't exist."""
        with patch(
            "roadmap.core.services.validators.duplicate_milestones_validator.Path"
        ) as mock_path_class:
            mock_path = MagicMock()
            mock_path.exists.return_value = False
            mock_path_class.return_value = mock_path

            status, message = DuplicateMilestonesValidator.perform_check()

            assert status == HealthStatus.HEALTHY
            assert "not initialized yet" in message

    def test_perform_check_healthy(self):
        """Test perform_check returns HEALTHY when no duplicates found."""
        mock_core = MagicMock()
        milestone1 = MilestoneBuilder().with_name("v1.0").build()
        milestone2 = MilestoneBuilder().with_name("v2.0").build()
        mock_core.milestones.list.return_value = [milestone1, milestone2]

        with patch(
            "roadmap.core.services.validators.duplicate_milestones_validator.Path"
        ) as mock_path_class:
            mock_path = MagicMock()
            mock_path.exists.return_value = True
            mock_path.glob.return_value = []
            mock_path_class.return_value = mock_path

            with patch(
                "roadmap.core.services.validators.duplicate_milestones_validator.RoadmapCore"
            ) as mock_core_class:
                mock_core_class.return_value = mock_core
                status, message = DuplicateMilestonesValidator.perform_check()

                assert status == HealthStatus.HEALTHY
                assert "No duplicate milestones found" in message

    def test_perform_check_with_name_duplicates(self):
        """Test perform_check detects duplicate milestone names."""
        mock_core = MagicMock()

        milestone1 = MilestoneBuilder().with_name("sprint-1").build()
        milestone2 = MilestoneBuilder().with_name("sprint-1").build()  # Duplicate name
        mock_core.milestones.list.return_value = [milestone1, milestone2]

        with patch(
            "roadmap.core.services.validators.duplicate_milestones_validator.Path"
        ) as mock_path_class:
            mock_path = MagicMock()
            mock_path.exists.return_value = True
            mock_path.glob.return_value = []  # No file duplicates
            mock_path_class.return_value = mock_path

            with patch(
                "roadmap.core.services.validators.duplicate_milestones_validator.RoadmapCore"
            ) as mock_core_class:
                mock_core_class.return_value = mock_core
                status, message = DuplicateMilestonesValidator.perform_check()

                assert status == HealthStatus.DEGRADED
                assert "multiple times" in message.lower()
