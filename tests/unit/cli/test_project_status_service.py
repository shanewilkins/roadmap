"""Unit tests for ProjectStatusService.

Tests cover:
- Status data gathering
- Milestone progress computation
- Issue statistics
- Roadmap summary generation
"""

from unittest.mock import MagicMock, patch

from roadmap.adapters.cli.services.project_status_service import (
    IssueStatisticsService,
    MilestoneProgressService,
    RoadmapSummaryService,
    StatusDataService,
)
from roadmap.core.domain import Status
from tests.unit.domain.test_data_factory_generation import TestDataFactory


class TestStatusDataService:
    """Tests for gathering status data."""

    def test_gather_status_data_empty(self):
        """Test gathering data when no issues or milestones."""
        mock_core = TestDataFactory.create_mock_core(is_initialized=True)
        mock_core.issues.list.return_value = []
        mock_core.milestones.list.return_value = []

        result = StatusDataService.gather_status_data(mock_core)

        assert not result["has_data"]
        assert result["issue_count"] == 0
        assert result["milestone_count"] == 0
        assert result["issues"] == []
        assert result["milestones"] == []

    def test_gather_status_data_with_issues(self):
        """Test gathering data with issues."""
        mock_core = TestDataFactory.create_mock_core(is_initialized=True)
        mock_issues = [MagicMock(), MagicMock(), MagicMock()]
        mock_core.issues.list.return_value = mock_issues
        mock_core.milestones.list.return_value = []

        result = StatusDataService.gather_status_data(mock_core)

        assert result["has_data"]
        assert result["issue_count"] == 3
        assert result["milestone_count"] == 0
        assert result["issues"] == mock_issues

    def test_gather_status_data_with_milestones(self):
        """Test gathering data with milestones."""
        mock_core = TestDataFactory.create_mock_core(is_initialized=True)
        mock_milestones = [MagicMock(), MagicMock()]
        mock_core.issues.list.return_value = []
        mock_core.milestones.list.return_value = mock_milestones

        result = StatusDataService.gather_status_data(mock_core)

        assert result["has_data"]
        assert result["issue_count"] == 0
        assert result["milestone_count"] == 2
        assert result["milestones"] == mock_milestones

    def test_gather_status_data_with_both(self):
        """Test gathering data with both issues and milestones."""
        mock_core = TestDataFactory.create_mock_core(is_initialized=True)
        mock_issues = [MagicMock(), MagicMock()]
        mock_milestones = [MagicMock()]
        mock_core.issues.list.return_value = mock_issues
        mock_core.milestones.list.return_value = mock_milestones

        result = StatusDataService.gather_status_data(mock_core)

        assert result["has_data"]
        assert result["issue_count"] == 2
        assert result["milestone_count"] == 1

    def test_gather_status_data_handles_exception(self):
        """Test that exceptions are handled gracefully."""
        mock_core = TestDataFactory.create_mock_core(is_initialized=True)
        mock_core.issues.list.side_effect = Exception("Database error")

        result = StatusDataService.gather_status_data(mock_core)

        assert not result["has_data"]
        assert result["issue_count"] == 0
        assert result["issues"] == []


class TestMilestoneProgressService:
    """Tests for computing milestone progress."""

    def test_get_milestone_progress_zero_total(self):
        """Test progress when milestone has no issues."""
        mock_core = TestDataFactory.create_mock_core(is_initialized=True)
        mock_core.db.get_milestone_progress.return_value = {"total": 0, "completed": 0}

        result = MilestoneProgressService.get_milestone_progress(mock_core, "v1.0")

        assert result["total"] == 0
        assert result["completed"] == 0
        assert result["percentage"] == 0

    def test_get_milestone_progress_partial(self):
        """Test progress when milestone is partially completed."""
        mock_core = TestDataFactory.create_mock_core(is_initialized=True)
        mock_core.db.get_milestone_progress.return_value = {"total": 10, "completed": 3}

        result = MilestoneProgressService.get_milestone_progress(mock_core, "v1.0")

        assert result["total"] == 10
        assert result["completed"] == 3
        assert result["percentage"] == 30.0

    def test_get_milestone_progress_complete(self):
        """Test progress when milestone is completed."""
        mock_core = TestDataFactory.create_mock_core(is_initialized=True)
        mock_core.db.get_milestone_progress.return_value = {"total": 5, "completed": 5}

        result = MilestoneProgressService.get_milestone_progress(mock_core, "v1.0")

        assert result["total"] == 5
        assert result["completed"] == 5
        assert result["percentage"] == 100.0

    def test_get_all_milestones_progress(self):
        """Test getting progress for multiple milestones."""
        mock_core = TestDataFactory.create_mock_core(is_initialized=True)

        def progress_side_effect(name):
            if name == "v1.0":
                return {"total": 10, "completed": 5}
            elif name == "v2.0":
                return {"total": 20, "completed": 20}
            return {"total": 0, "completed": 0}

        mock_core.db.get_milestone_progress.side_effect = progress_side_effect

        # Create mock milestones with .name attribute
        mock_milestone_1 = MagicMock()
        mock_milestone_1.name = "v1.0"
        mock_milestone_2 = MagicMock()
        mock_milestone_2.name = "v2.0"
        mock_milestones = [mock_milestone_1, mock_milestone_2]

        result = MilestoneProgressService.get_all_milestones_progress(
            mock_core, mock_milestones
        )

        assert "v1.0" in result
        assert "v2.0" in result
        assert result["v1.0"]["percentage"] == 50.0
        assert result["v2.0"]["percentage"] == 100.0

    def test_get_milestone_progress_handles_exception(self):
        """Test that exceptions are handled gracefully."""
        mock_core = TestDataFactory.create_mock_core(is_initialized=True)
        mock_core.db.get_milestone_progress.side_effect = Exception("DB error")

        result = MilestoneProgressService.get_milestone_progress(mock_core, "v1.0")

        assert result["total"] == 0
        assert result["completed"] == 0
        assert result["percentage"] == 0


class TestIssueStatisticsService:
    """Tests for computing issue statistics."""

    def test_get_issue_status_counts_empty(self):
        """Test counting when no issues."""
        result = IssueStatisticsService.get_issue_status_counts([])

        assert result == {}

    def test_get_issue_status_counts_single_status(self):
        """Test counting issues with single status."""
        mock_issues = [
            MagicMock(status=Status.TODO),
            MagicMock(status=Status.TODO),
            MagicMock(status=Status.TODO),
        ]

        result = IssueStatisticsService.get_issue_status_counts(mock_issues)

        assert result[Status.TODO] == 3
        assert len(result) == 1

    def test_get_issue_status_counts_multiple_statuses(self):
        """Test counting issues with multiple statuses."""
        mock_issues = [
            MagicMock(status=Status.TODO),
            MagicMock(status=Status.TODO),
            MagicMock(status=Status.IN_PROGRESS),
            MagicMock(status=Status.CLOSED),
            MagicMock(status=Status.CLOSED),
            MagicMock(status=Status.CLOSED),
        ]

        result = IssueStatisticsService.get_issue_status_counts(mock_issues)

        assert result[Status.TODO] == 2
        assert result[Status.IN_PROGRESS] == 1
        assert result[Status.CLOSED] == 3

    def test_get_status_styling(self):
        """Test that all statuses have styling."""
        styles = IssueStatisticsService.get_status_styling()

        assert Status.TODO in styles
        assert Status.IN_PROGRESS in styles
        assert Status.BLOCKED in styles
        assert Status.REVIEW in styles
        assert Status.CLOSED in styles

    def test_get_all_status_counts_fills_zeros(self):
        """Test that all statuses are represented including zeros."""
        mock_issues = [
            MagicMock(status=Status.TODO),
            MagicMock(status=Status.CLOSED),
        ]

        result = IssueStatisticsService.get_all_status_counts(mock_issues)

        # All status values should be present
        for status in Status:
            assert status in result

        assert result[Status.TODO] == 1
        assert result[Status.CLOSED] == 1
        assert result[Status.IN_PROGRESS] == 0
        assert result[Status.BLOCKED] == 0
        assert result[Status.REVIEW] == 0

    def test_get_active_issue_count(self):
        """Test counting active (non-closed) issues."""
        mock_issues = [
            MagicMock(status=Status.TODO),
            MagicMock(status=Status.IN_PROGRESS),
            MagicMock(status=Status.CLOSED),
            MagicMock(status=Status.CLOSED),
            MagicMock(status=Status.REVIEW),
        ]

        result = IssueStatisticsService.get_active_issue_count(mock_issues)

        assert result == 3

    def test_get_blocked_issue_count(self):
        """Test counting blocked issues."""
        mock_issues = [
            MagicMock(status=Status.TODO),
            MagicMock(status=Status.BLOCKED),
            MagicMock(status=Status.BLOCKED),
            MagicMock(status=Status.CLOSED),
        ]

        result = IssueStatisticsService.get_blocked_issue_count(mock_issues)

        assert result == 2


class TestRoadmapSummaryService:
    """Tests for computing roadmap summaries."""

    def test_compute_roadmap_summary_empty(self):
        """Test summary for empty roadmap."""
        mock_core = TestDataFactory.create_mock_core(is_initialized=True)

        result = RoadmapSummaryService.compute_roadmap_summary(mock_core, [], [])

        assert result["total_issues"] == 0
        assert result["active_issues"] == 0
        assert result["blocked_issues"] == 0
        assert result["total_milestones"] == 0
        assert result["completed_milestones"] == 0

    @patch(
        "roadmap.adapters.cli.services.project_status_service.MilestoneProgressService"
    )
    def test_compute_roadmap_summary_with_issues(self, mock_service_class):
        """Test summary with issues."""
        mock_core = TestDataFactory.create_mock_core(is_initialized=True)
        mock_service_class.get_all_milestones_progress.return_value = {}

        mock_issues = [
            MagicMock(status=Status.TODO),
            MagicMock(status=Status.IN_PROGRESS),
            MagicMock(status=Status.BLOCKED),
            MagicMock(status=Status.CLOSED),
        ]

        result = RoadmapSummaryService.compute_roadmap_summary(
            mock_core, mock_issues, []
        )

        assert result["total_issues"] == 4
        assert result["active_issues"] == 3  # All except closed
        assert result["blocked_issues"] == 1
        assert result["total_milestones"] == 0

    @patch(
        "roadmap.adapters.cli.services.project_status_service.MilestoneProgressService"
    )
    def test_compute_roadmap_summary_with_milestones(self, mock_service_class):
        """Test summary with milestones."""
        mock_core = TestDataFactory.create_mock_core(is_initialized=True)
        mock_service_class.get_all_milestones_progress.return_value = {
            "v1.0": {"total": 10, "completed": 10, "percentage": 100},
            "v2.0": {"total": 20, "completed": 15, "percentage": 75},
        }

        mock_milestones = [
            MagicMock(name="v1.0", due_date=None),
            MagicMock(name="v2.0", due_date=None),
        ]

        result = RoadmapSummaryService.compute_roadmap_summary(
            mock_core, [], mock_milestones
        )

        assert result["total_milestones"] == 2
        assert result["completed_milestones"] == 1  # Only v1.0 is 100%

    @patch(
        "roadmap.adapters.cli.services.project_status_service.MilestoneProgressService"
    )
    def test_compute_roadmap_summary_full(self, mock_service_class):
        """Test full summary with issues and milestones."""
        mock_core = TestDataFactory.create_mock_core(is_initialized=True)
        mock_service_class.get_all_milestones_progress.return_value = {
            "v1.0": {"total": 10, "completed": 10, "percentage": 100},
        }

        mock_issues = [
            MagicMock(status=Status.TODO),
            MagicMock(status=Status.IN_PROGRESS),
            MagicMock(status=Status.CLOSED),
        ]

        mock_milestones = [MagicMock(name="v1.0", due_date=None)]

        result = RoadmapSummaryService.compute_roadmap_summary(
            mock_core, mock_issues, mock_milestones
        )

        assert result["total_issues"] == 3
        assert result["active_issues"] == 2
        assert result["total_milestones"] == 1
        assert result["completed_milestones"] == 1
        assert len(result["milestone_details"]) == 1

    def test_compute_roadmap_summary_handles_exception(self):
        """Test that exceptions are handled gracefully."""
        mock_core = TestDataFactory.create_mock_core(is_initialized=True)
        mock_issues = [MagicMock(status=Status.TODO)]
        mock_milestones = []

        with patch(
            "roadmap.adapters.cli.services.project_status_service.MilestoneProgressService.get_all_milestones_progress"
        ) as mock_progress:
            mock_progress.side_effect = Exception("DB error")
            result = RoadmapSummaryService.compute_roadmap_summary(
                mock_core, mock_issues, mock_milestones
            )

        assert result["total_issues"] == 1
        assert result["milestone_progress"] == {}
