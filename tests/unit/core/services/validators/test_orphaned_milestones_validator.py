"""Tests for OrphanedMilestonesValidator."""

from unittest.mock import MagicMock, patch

from roadmap.core.services.validator_base import HealthStatus
from roadmap.core.services.validators import OrphanedMilestonesValidator
from tests.factories.domain import MilestoneBuilder, ProjectBuilder


class TestOrphanedMilestonesValidator:
    """Test OrphanedMilestonesValidator."""

    def test_get_check_name(self):
        """Test get_check_name returns correct identifier."""
        assert OrphanedMilestonesValidator.get_check_name() == "orphaned_milestones"

    def test_scan_for_orphaned_milestones_none_orphaned(self):
        """Test scan_for_orphaned_milestones when all milestones are assigned."""
        # Create mock core
        mock_core = MagicMock()

        # Create a project with milestones
        project = ProjectBuilder().with_milestones(["sprint-1", "sprint-2"]).build()

        # Create milestones
        milestone1 = MilestoneBuilder().with_name("sprint-1").build()
        milestone2 = MilestoneBuilder().with_name("sprint-2").build()

        mock_core.projects.list.return_value = [project]
        mock_core.milestones.list.return_value = [milestone1, milestone2]

        orphaned = OrphanedMilestonesValidator.scan_for_orphaned_milestones(mock_core)

        assert len(orphaned) == 0

    def test_scan_for_orphaned_milestones_finds_orphaned(self):
        """Test scan_for_orphaned_milestones finds unassigned milestones."""
        mock_core = MagicMock()

        # Create a project with one milestone
        project = ProjectBuilder().with_milestones(["sprint-1"]).build()

        # Create milestones
        milestone1 = MilestoneBuilder().with_name("sprint-1").build()
        milestone2 = MilestoneBuilder().with_name("orphaned-sprint").build()

        mock_core.projects.list.return_value = [project]
        mock_core.milestones.list.return_value = [milestone1, milestone2]

        orphaned = OrphanedMilestonesValidator.scan_for_orphaned_milestones(mock_core)

        assert len(orphaned) == 1
        assert orphaned[0]["name"] == "orphaned-sprint"

    def test_perform_check_healthy(self):
        """Test perform_check returns HEALTHY when no orphans found."""
        mock_core = MagicMock()

        project = ProjectBuilder().with_milestones(["v1-0"]).build()
        milestone = MilestoneBuilder().with_name("v1-0").build()

        mock_core.projects.list.return_value = [project]
        mock_core.milestones.list.return_value = [milestone]

        with patch(
            "roadmap.core.services.validators.orphaned_milestones_validator.RoadmapCore"
        ) as mock_core_class:
            mock_core_class.return_value = mock_core
            status, message = OrphanedMilestonesValidator.perform_check()

            assert status == HealthStatus.HEALTHY
            assert "No orphaned milestones found" in message

    def test_perform_check_degraded(self):
        """Test perform_check returns DEGRADED when orphans found."""
        mock_core = MagicMock()

        # Create a project with one milestone
        project = ProjectBuilder().with_milestones(["sprint-1"]).build()

        # Create two milestones, only one assigned
        milestone1 = MilestoneBuilder().with_name("sprint-1").build()
        milestone2 = MilestoneBuilder().with_name("abandoned").build()

        mock_core.projects.list.return_value = [project]
        mock_core.milestones.list.return_value = [milestone1, milestone2]

        with patch(
            "roadmap.core.services.validators.orphaned_milestones_validator.RoadmapCore"
        ) as mock_core_class:
            mock_core_class.return_value = mock_core
            status, message = OrphanedMilestonesValidator.perform_check()

            assert status == HealthStatus.DEGRADED
            assert "1 orphaned milestone(s) found" in message

    def test_perform_check_multiple_orphaned(self):
        """Test perform_check with multiple orphaned milestones."""
        mock_core = MagicMock()

        # Create project with one milestone
        project = ProjectBuilder().with_milestones(["v1-0"]).build()

        # Create three milestones, only one assigned
        milestone1 = MilestoneBuilder().with_name("v1-0").build()
        milestone2 = MilestoneBuilder().with_name("v2-0").build()
        milestone3 = MilestoneBuilder().with_name("v3-0").build()

        mock_core.projects.list.return_value = [project]
        mock_core.milestones.list.return_value = [milestone1, milestone2, milestone3]

        with patch(
            "roadmap.core.services.validators.orphaned_milestones_validator.RoadmapCore"
        ) as mock_core_class:
            mock_core_class.return_value = mock_core
            status, message = OrphanedMilestonesValidator.perform_check()

            assert status == HealthStatus.DEGRADED
            assert "2 orphaned milestone(s) found" in message

    def test_perform_check_no_projects(self):
        """Test perform_check when no projects exist (all milestones orphaned)."""
        mock_core = MagicMock()

        # Create milestones without any projects
        milestone1 = MilestoneBuilder().with_name("sprint-1").build()
        milestone2 = MilestoneBuilder().with_name("sprint-2").build()

        mock_core.projects.list.return_value = []
        mock_core.milestones.list.return_value = [milestone1, milestone2]

        with patch(
            "roadmap.core.services.validators.orphaned_milestones_validator.RoadmapCore"
        ) as mock_core_class:
            mock_core_class.return_value = mock_core
            status, message = OrphanedMilestonesValidator.perform_check()

            assert status == HealthStatus.DEGRADED
            assert "2 orphaned milestone(s) found" in message
