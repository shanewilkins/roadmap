"""
Unit tests for ProjectStatusPresenter.

Tests cover:
- Milestone progress display
- Issue status table rendering
- Roadmap summary display
- Error message display
"""

from unittest.mock import MagicMock, patch

from roadmap.adapters.cli.presentation.project_status_presenter import (
    IssueStatusPresenter,
    MilestoneProgressPresenter,
    RoadmapStatusPresenter,
)
from roadmap.core.domain import Status


class TestMilestoneProgressPresenter:
    """Tests for milestone progress display."""

    @patch("roadmap.adapters.cli.presentation.project_status_presenter.console")
    def test_show_milestone_header(self, mock_console):
        """Test displaying milestone header."""
        MilestoneProgressPresenter.show_milestone_header()

        mock_console.print.assert_called_once()
        call_args = mock_console.print.call_args
        assert "Milestones" in str(call_args)

    @patch("roadmap.adapters.cli.presentation.project_status_presenter.console")
    def test_show_milestone_progress_no_issues(self, mock_console):
        """Test displaying milestone with no issues."""
        progress = {"total": 0, "completed": 0}

        MilestoneProgressPresenter.show_milestone_progress("v1.0", progress)

        calls = str(mock_console.print.call_args_list)
        assert "v1.0" in calls
        assert "No issues" in calls or "assigned" in calls

    @patch("roadmap.adapters.cli.presentation.project_status_presenter.Progress")
    @patch("roadmap.adapters.cli.presentation.project_status_presenter.console")
    def test_show_milestone_progress_with_issues(self, mock_console, mock_progress):
        """Test displaying milestone with progress."""
        progress = {"total": 10, "completed": 7}

        MilestoneProgressPresenter.show_milestone_progress("v1.0", progress)

        # Should have printed milestone name
        calls = [call[0][0] for call in mock_console.print.call_args_list]
        assert any("v1.0" in str(call) for call in calls)

    @patch(
        "roadmap.adapters.cli.presentation.project_status_presenter.MilestoneProgressPresenter.show_milestone_progress"
    )
    @patch(
        "roadmap.adapters.cli.presentation.project_status_presenter.MilestoneProgressPresenter.show_milestone_header"
    )
    def test_show_all_milestones(self, mock_header, mock_progress):
        """Test displaying all milestones."""
        mock_milestones = [
            MagicMock(name="v1.0"),
            MagicMock(name="v2.0"),
        ]
        milestone_progress = {
            "v1.0": {"total": 10, "completed": 5},
            "v2.0": {"total": 20, "completed": 20},
        }

        MilestoneProgressPresenter.show_all_milestones(
            mock_milestones, milestone_progress
        )

        mock_header.assert_called_once()
        assert mock_progress.call_count == 2


class TestIssueStatusPresenter:
    """Tests for issue status display."""

    def test_get_status_style_todo(self):
        """Test getting style for TODO status."""
        style = IssueStatusPresenter.get_status_style(Status.TODO)
        assert style == "white"

    def test_get_status_style_in_progress(self):
        """Test getting style for IN_PROGRESS status."""
        style = IssueStatusPresenter.get_status_style(Status.IN_PROGRESS)
        assert style == "yellow"

    def test_get_status_style_blocked(self):
        """Test getting style for BLOCKED status."""
        style = IssueStatusPresenter.get_status_style(Status.BLOCKED)
        assert style == "red"

    def test_get_status_style_review(self):
        """Test getting style for REVIEW status."""
        style = IssueStatusPresenter.get_status_style(Status.REVIEW)
        assert style == "blue"

    def test_get_status_style_closed(self):
        """Test getting style for CLOSED status."""
        style = IssueStatusPresenter.get_status_style(Status.DONE)
        assert style == "green"

    @patch("roadmap.adapters.cli.presentation.project_status_presenter.console")
    def test_show_issue_status_header(self, mock_console):
        """Test displaying issue status header."""
        IssueStatusPresenter.show_issue_status_header()

        mock_console.print.assert_called_once()
        call_args = mock_console.print.call_args
        assert "Issues by Status" in str(call_args)

    @patch("roadmap.adapters.cli.presentation.project_status_presenter.console")
    def test_show_issue_status_table_empty(self, mock_console):
        """Test displaying table when no issues."""
        IssueStatusPresenter.show_issue_status_table({})

        calls = str(mock_console.print.call_args_list)
        assert "No issues" in calls

    @patch("roadmap.adapters.cli.presentation.project_status_presenter.console")
    def test_show_issue_status_table_with_issues(self, mock_console):
        """Test displaying table with issue counts."""
        issue_counts = {
            Status.TODO: 5,
            Status.IN_PROGRESS: 2,
            Status.DONE: 3,
        }

        IssueStatusPresenter.show_issue_status_table(issue_counts)

        mock_console.print.assert_called()

    @patch(
        "roadmap.adapters.cli.presentation.project_status_presenter.IssueStatusPresenter.show_issue_status_table"
    )
    @patch(
        "roadmap.adapters.cli.presentation.project_status_presenter.IssueStatusPresenter.show_issue_status_header"
    )
    def test_show_all_issue_statuses(self, mock_header, mock_table):
        """Test displaying all issue statuses."""
        issue_counts = {Status.TODO: 5, Status.DONE: 3}

        IssueStatusPresenter.show_all_issue_statuses(issue_counts)

        mock_header.assert_called_once()
        mock_table.assert_called_once_with(issue_counts)


class TestRoadmapStatusPresenter:
    """Tests for overall roadmap status display."""

    @patch("roadmap.adapters.cli.presentation.project_status_presenter.console")
    def test_show_empty_state(self, mock_console):
        """Test displaying empty state."""
        RoadmapStatusPresenter.show_empty_state()

        calls = str(mock_console.print.call_args_list)
        assert "No issues" in calls

    @patch("roadmap.adapters.cli.presentation.project_status_presenter.console")
    def test_show_status_header(self, mock_console):
        """Test displaying status header."""
        RoadmapStatusPresenter.show_status_header()

        mock_console.print.assert_called_once()
        call_args = mock_console.print.call_args
        assert "Status" in str(call_args)

    @patch("roadmap.adapters.cli.presentation.project_status_presenter.console")
    def test_show_roadmap_summary_basic(self, mock_console):
        """Test displaying basic roadmap summary."""
        summary = {
            "total_issues": 10,
            "active_issues": 7,
            "blocked_issues": 1,
            "total_milestones": 3,
            "completed_milestones": 1,
        }

        RoadmapStatusPresenter.show_roadmap_summary(summary)

        calls = str(mock_console.print.call_args_list)
        assert "Total Issues" in calls or "10" in calls
        assert "Active Issues" in calls or "7" in calls

    @patch("roadmap.adapters.cli.presentation.project_status_presenter.console")
    def test_show_roadmap_summary_no_blocked(self, mock_console):
        """Test summary display skips blocked when zero."""
        summary = {
            "total_issues": 10,
            "active_issues": 10,
            "blocked_issues": 0,
            "total_milestones": 2,
            "completed_milestones": 0,
        }

        RoadmapStatusPresenter.show_roadmap_summary(summary)

        # Should not print blocked count for 0
        mock_console.print.assert_called()

    @patch("roadmap.adapters.cli.presentation.project_status_presenter.console")
    def test_show_error(self, mock_console):
        """Test displaying error message."""
        error_msg = "Database connection failed"

        RoadmapStatusPresenter.show_error(error_msg)

        mock_console.print.assert_called()
        call_args = str(mock_console.print.call_args)
        assert error_msg in call_args or "Failed" in call_args

    @patch("roadmap.adapters.cli.presentation.project_status_presenter.console")
    def test_show_roadmap_summary_complete(self, mock_console):
        """Test summary with all fields populated."""
        summary = {
            "total_issues": 20,
            "active_issues": 12,
            "blocked_issues": 2,
            "total_milestones": 5,
            "completed_milestones": 3,
            "issue_status_counts": {
                Status.TODO: 8,
                Status.IN_PROGRESS: 4,
                Status.BLOCKED: 2,
                Status.REVIEW: 0,
                Status.DONE: 6,
            },
            "milestone_details": [
                {"name": "v1.0", "progress": {"percentage": 100}},
                {"name": "v2.0", "progress": {"percentage": 50}},
            ],
        }

        RoadmapStatusPresenter.show_roadmap_summary(summary)

        mock_console.print.assert_called()
        calls = str(mock_console.print.call_args_list)
        # Should show summary information
        assert "Summary" in calls or "20" in calls or "Issues" in calls
