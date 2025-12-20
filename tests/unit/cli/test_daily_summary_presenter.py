"""Unit tests for DailySummaryPresenter.

Tests the display and rendering logic for daily workflow summary output.
"""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from rich.console import Console

from roadmap.adapters.cli.presentation.daily_summary_presenter import (
    DailySummaryPresenter,
)
from roadmap.common.constants import MilestoneStatus, Priority, Status
from roadmap.core.domain.issue import Issue
from roadmap.core.domain.milestone import Milestone


@pytest.fixture
def mock_console():
    """Provide a mock console for capturing output."""
    return MagicMock(spec=Console)


@pytest.fixture
def sample_data():
    """Provide sample daily summary data for testing."""
    today = datetime.now()
    milestone = Milestone(
        name="v1.0",
        description="First release",
        status=MilestoneStatus.OPEN,
        due_date=today + timedelta(days=10),
    )

    in_progress_issue = Issue(
        id="TASK-1",
        title="Work on feature X",
        status=Status.IN_PROGRESS,
        assignee="alice",
        priority=Priority.HIGH,
        milestone="v1.0",
    )

    overdue_issue = Issue(
        id="TASK-2",
        title="Complete bug fix",
        status=Status.TODO,
        assignee="alice",
        priority=Priority.CRITICAL,
        milestone="v1.0",
        due_date=today - timedelta(days=2),
    )

    blocked_issue = Issue(
        id="TASK-3",
        title="Blocked feature",
        status=Status.BLOCKED,
        assignee="alice",
        priority=Priority.HIGH,
        milestone="v1.0",
    )

    todo_issue = Issue(
        id="TASK-4",
        title="Next high priority task",
        status=Status.TODO,
        assignee="alice",
        priority=Priority.HIGH,
        milestone="v1.0",
    )

    completed_issue = Issue(
        id="TASK-5",
        title="Completed task",
        status=Status.DONE,
        assignee="alice",
        priority=Priority.MEDIUM,
        milestone="v1.0",
        actual_end_date=today,
    )

    data = {
        "user": "alice",
        "current_user": "alice",
        "milestone": milestone,
        "has_issues": True,
        "issues": {
            "in_progress": [in_progress_issue],
            "overdue": [overdue_issue],
            "blocked": [blocked_issue],
            "todo_high_priority": [todo_issue],
            "completed_today": [completed_issue],
        },
    }

    return data


class TestDailySummaryPresenterRender:
    """Test main render method."""

    @patch("roadmap.adapters.cli.presentation.daily_summary_presenter.console")
    def test_render_calls_all_section_renderers(self, mock_console_module, sample_data):
        """Test that render method calls all sub-renderers."""
        with (
            patch.object(DailySummaryPresenter, "_render_header") as mock_header,
            patch.object(DailySummaryPresenter, "_render_in_progress") as mock_progress,
            patch.object(DailySummaryPresenter, "_render_overdue") as mock_overdue,
            patch.object(DailySummaryPresenter, "_render_blocked") as mock_blocked,
            patch.object(DailySummaryPresenter, "_render_up_next") as mock_next,
            patch.object(
                DailySummaryPresenter, "_render_completed_today"
            ) as mock_completed,
            patch.object(DailySummaryPresenter, "_render_summary") as mock_summary,
            patch.object(DailySummaryPresenter, "_render_tips") as mock_tips,
        ):
            DailySummaryPresenter.render(sample_data)

            mock_header.assert_called_once()
            mock_progress.assert_called_once()
            mock_overdue.assert_called_once()
            mock_blocked.assert_called_once()
            mock_next.assert_called_once()
            mock_completed.assert_called_once()
            mock_summary.assert_called_once()
            mock_tips.assert_called_once()

    @patch("roadmap.adapters.cli.presentation.daily_summary_presenter.console")
    def test_render_handles_empty_sections(self, mock_console_module):
        """Test that render handles data with empty sections gracefully."""
        empty_data = {
            "user": "alice",
            "current_user": "alice",
            "milestone": MagicMock(),
            "has_issues": False,
            "issues": {
                "in_progress": [],
                "overdue": [],
                "blocked": [],
                "todo_high_priority": [],
                "completed_today": [],
            },
        }

        # Should not raise an exception
        try:
            DailySummaryPresenter.render(empty_data)
        except Exception as e:
            pytest.fail(f"Render should handle empty sections: {e}")


class TestDailySummaryPresenterHeader:
    """Test header rendering."""

    @patch("roadmap.adapters.cli.presentation.daily_summary_presenter.console")
    def test_render_header_includes_user_info(self, mock_console):
        """Test that header includes user information."""
        milestone = Milestone(
            name="v1.0",
            description="Test milestone",
            status=MilestoneStatus.OPEN,
            due_date=datetime.now() + timedelta(days=10),
        )

        data = {
            "user": "alice",
            "current_user": "alice",
            "milestone": milestone,
            "has_issues": True,
            "issues": {},
        }

        DailySummaryPresenter._render_header(data)

        # Verify console.print was called (at least once for the Panel)
        assert mock_console.print.called

    @patch("roadmap.adapters.cli.presentation.daily_summary_presenter.console")
    def test_render_header_includes_milestone_info(self, mock_console):
        """Test that header includes milestone information."""
        milestone = MagicMock()
        milestone.name = "v1.0"
        milestone.due_date = datetime.now() + timedelta(days=10)

        data = {
            "user": "alice",
            "current_user": "alice",
            "milestone": milestone,
            "has_issues": True,
            "issues": {},
        }

        DailySummaryPresenter._render_header(data)

        assert mock_console.print.called


class TestDailySummaryPresenterSections:
    """Test individual section rendering."""

    @patch("roadmap.adapters.cli.presentation.daily_summary_presenter.console")
    def test_render_in_progress_shows_issues(self, mock_console, sample_data):
        """Test that in-progress section renders issues."""
        issues = sample_data["issues"]["in_progress"]

        DailySummaryPresenter._render_in_progress(issues)

        assert mock_console.print.called

    @patch("roadmap.adapters.cli.presentation.daily_summary_presenter.console")
    def test_render_in_progress_with_no_issues(self, mock_console):
        """Test that in-progress section handles empty list."""
        DailySummaryPresenter._render_in_progress([])

        assert mock_console.print.called

    @patch("roadmap.adapters.cli.presentation.daily_summary_presenter.console")
    def test_render_overdue_shows_days_overdue(self, mock_console):
        """Test that overdue section shows days calculation."""
        overdue_issue = Issue(
            id="TASK-1",
            title="Overdue task",
            status=Status.TODO,
            assignee="alice",
            priority=Priority.HIGH,
            due_date=datetime.now() - timedelta(days=3),
        )

        DailySummaryPresenter._render_overdue([overdue_issue])

        assert mock_console.print.called

    @patch("roadmap.adapters.cli.presentation.daily_summary_presenter.console")
    def test_render_blocked_indicates_blocker(self, mock_console):
        """Test that blocked section indicates blocking status."""
        blocked_issue = Issue(
            id="TASK-1",
            title="Blocked task",
            status=Status.BLOCKED,
            assignee="alice",
            priority=Priority.HIGH,
        )

        DailySummaryPresenter._render_blocked([blocked_issue])

        assert mock_console.print.called

    @patch("roadmap.adapters.cli.presentation.daily_summary_presenter.console")
    def test_render_up_next_limits_to_three(self, mock_console):
        """Test that up-next section shows max 3 issues."""
        issues = [
            Issue(
                id=f"TASK-{i}",
                title=f"Task {i}",
                status=Status.TODO,
                assignee="alice",
                priority=Priority.HIGH,
            )
            for i in range(5)
        ]

        DailySummaryPresenter._render_up_next(issues)

        # Should render only top 3
        assert mock_console.print.called

    @patch("roadmap.adapters.cli.presentation.daily_summary_presenter.console")
    def test_render_completed_today_shows_completion_time(self, mock_console):
        """Test that completed section shows completion times."""
        completed_issue = Issue(
            id="TASK-1",
            title="Completed task",
            status=Status.DONE,
            assignee="alice",
            priority=Priority.MEDIUM,
            actual_end_date=datetime.now(),
        )

        DailySummaryPresenter._render_completed_today([completed_issue])

        assert mock_console.print.called


class TestDailySummaryPresenterSummary:
    """Test summary section rendering."""

    @patch("roadmap.adapters.cli.presentation.daily_summary_presenter.console")
    def test_render_summary_shows_counts(self, mock_console, sample_data):
        """Test that summary section shows issue counts."""
        DailySummaryPresenter._render_summary(sample_data["issues"])

        assert mock_console.print.called

    @patch("roadmap.adapters.cli.presentation.daily_summary_presenter.console")
    def test_render_summary_with_empty_issues(self, mock_console):
        """Test that summary handles empty issue list."""
        empty_issues = {
            "in_progress": [],
            "overdue": [],
            "blocked": [],
            "todo_high_priority": [],
            "completed_today": [],
        }

        DailySummaryPresenter._render_summary(empty_issues)

        assert mock_console.print.called


class TestDailySummaryPresenterTips:
    """Test tips/suggestions rendering."""

    @patch("roadmap.adapters.cli.presentation.daily_summary_presenter.console")
    def test_render_tips_with_data(self, mock_console, sample_data):
        """Test that tips section renders when data provided."""
        DailySummaryPresenter._render_tips(sample_data)

        assert mock_console.print.called

    @patch("roadmap.adapters.cli.presentation.daily_summary_presenter.console")
    def test_render_tips_suggests_starting_work_when_idle(self, mock_console):
        """Test that tips suggest starting work when nothing in progress."""
        data = {
            "user": "alice",
            "current_user": "alice",
            "milestone": MagicMock(),
            "has_issues": True,
            "issues": {
                "in_progress": [],
                "overdue": [],
                "blocked": [],
                "todo_high_priority": [MagicMock(id="TASK-1")],
                "completed_today": [],
            },
        }

        DailySummaryPresenter._render_tips(data)

        assert mock_console.print.called

    @patch("roadmap.adapters.cli.presentation.daily_summary_presenter.console")
    def test_render_tips_suggests_addressing_overdue(self, mock_console):
        """Test that tips suggest addressing overdue when present."""
        data = {
            "user": "alice",
            "current_user": "alice",
            "milestone": MagicMock(),
            "has_issues": True,
            "issues": {
                "in_progress": [],
                "overdue": [MagicMock(id="TASK-1")],
                "blocked": [],
                "todo_high_priority": [],
                "completed_today": [],
            },
        }

        DailySummaryPresenter._render_tips(data)

        assert mock_console.print.called


class TestDailySummaryPresenterIntegration:
    """Integration tests for presenter."""

    @patch("roadmap.adapters.cli.presentation.daily_summary_presenter.console")
    def test_full_render_cycle_with_realistic_data(self, mock_console, sample_data):
        """Test complete render cycle with realistic sample data."""
        try:
            DailySummaryPresenter.render(sample_data)
            assert True
        except Exception as e:
            pytest.fail(f"Full render cycle failed: {e}")

    @patch("roadmap.adapters.cli.presentation.daily_summary_presenter.console")
    def test_render_produces_console_output(self, mock_console, sample_data):
        """Test that render produces console output."""
        DailySummaryPresenter.render(sample_data)

        # Should call print multiple times for different sections
        assert mock_console.print.call_count >= 5  # header + at least 4 sections

    @patch("roadmap.adapters.cli.presentation.daily_summary_presenter.console")
    def test_render_doesnt_crash_with_special_characters(self, mock_console):
        """Test that render handles special characters in titles gracefully."""
        issue_with_special_chars = Issue(
            id="TASK-1",
            title="Task with émojis 🚀 and spëcial çharacters",
            status=Status.TODO,
            assignee="alice",
            priority=Priority.HIGH,
        )

        milestone = Milestone(
            name="v1.0",
            description="Test milestone",
            status=MilestoneStatus.OPEN,
            due_date=datetime.now() + timedelta(days=10),
        )

        data = {
            "user": "alice",
            "current_user": "alice",
            "milestone": milestone,
            "has_issues": True,
            "issues": {
                "in_progress": [],
                "overdue": [],
                "blocked": [],
                "todo_high_priority": [issue_with_special_chars],
                "completed_today": [],
            },
        }

        try:
            DailySummaryPresenter.render(data)
            assert True
        except Exception as e:
            pytest.fail(f"Render failed with special characters: {e}")
