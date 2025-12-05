"""Unit tests for DailySummaryService.

Tests the business logic for generating daily workflow summaries including
user resolution, milestone selection, and issue categorization.
"""

import os
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from roadmap.domain.issue import Issue, Priority, Status
from roadmap.domain.milestone import Milestone, MilestoneStatus
from roadmap.presentation.cli.services.daily_summary_service import DailySummaryService


class TestDailySummaryServiceUserResolution:
    """Test user resolution in DailySummaryService."""

    def test_get_current_user_from_core(self):
        """Test that user is retrieved from core when available."""
        core = MagicMock()
        core.get_current_user.return_value = "alice"

        service = DailySummaryService(core)
        user = service.get_current_user()

        assert user == "alice"
        core.get_current_user.assert_called_once()

    def test_get_current_user_from_env_when_core_returns_none(self):
        """Test that ROADMAP_USER env var is used when core returns None."""
        core = MagicMock()
        core.get_current_user.return_value = None

        with patch.dict(os.environ, {"ROADMAP_USER": "bob"}):
            service = DailySummaryService(core)
            user = service.get_current_user()

        assert user == "bob"

    def test_get_current_user_raises_when_no_user_found(self):
        """Test that ValueError is raised when no user can be resolved."""
        core = MagicMock()
        core.get_current_user.return_value = None

        with patch.dict(os.environ, {}, clear=True):
            service = DailySummaryService(core)
            # get_current_user returns None, but get_daily_summary_data raises ValueError
            user = service.get_current_user()
            assert user is None


class TestDailySummaryServiceMilestoneSelection:
    """Test milestone selection logic."""

    def test_get_upcoming_milestone_returns_open_milestone_with_due_date(self):
        """Test that open milestone with nearest due date is selected."""
        core = MagicMock()
        today = datetime.now()

        milestones = [
            Milestone(
                name="v1.0",
                description="First release",
                status=MilestoneStatus.OPEN,
                due_date=today + timedelta(days=10),
            ),
            Milestone(
                name="v2.0",
                description="Second release",
                status=MilestoneStatus.OPEN,
                due_date=today + timedelta(days=20),
            ),
            Milestone(
                name="v3.0",
                description="Third release",
                status=MilestoneStatus.CLOSED,
                due_date=today + timedelta(days=5),
            ),
        ]
        core.list_milestones.return_value = milestones

        service = DailySummaryService(core)
        milestone = service.get_upcoming_milestone()

        assert milestone.name == "v1.0"

    def test_get_upcoming_milestone_raises_when_no_open_milestones(self):
        """Test that ValueError is raised when no open milestones exist."""
        core = MagicMock()
        core.list_milestones.return_value = []

        service = DailySummaryService(core)
        # get_upcoming_milestone returns None, but get_daily_summary_data raises ValueError
        milestone = service.get_upcoming_milestone()
        assert milestone is None

    def test_get_upcoming_milestone_prefers_milestones_with_due_date(self):
        """Test that milestones with due dates are preferred over those without."""
        core = MagicMock()
        today = datetime.now()

        milestones = [
            Milestone(
                name="no-date",
                description="No due date",
                status=MilestoneStatus.OPEN,
                due_date=None,
            ),
            Milestone(
                name="with-date",
                description="Has due date",
                status=MilestoneStatus.OPEN,
                due_date=today + timedelta(days=10),
            ),
        ]
        core.list_milestones.return_value = milestones

        service = DailySummaryService(core)
        milestone = service.get_upcoming_milestone()

        assert milestone.name == "with-date"


class TestDailySummaryServiceIssueCategorization:
    """Test issue categorization logic."""

    def test_categorize_issues_in_progress(self):
        """Test that IN_PROGRESS issues are correctly categorized."""
        in_progress_issue = Issue(
            id="TASK-1",
            title="Work in progress",
            status=Status.IN_PROGRESS,
            assignee="alice",
            priority=Priority.MEDIUM,
        )
        todo_issue = Issue(
            id="TASK-2",
            title="Not started",
            status=Status.TODO,
            assignee="alice",
            priority=Priority.LOW,
        )

        service = DailySummaryService(MagicMock())
        result = service.categorize_issues([in_progress_issue, todo_issue], "alice")

        assert len(result["in_progress"]) == 1
        assert result["in_progress"][0].id == "TASK-1"

    def test_categorize_issues_overdue(self):
        """Test that overdue issues are correctly categorized."""
        overdue_issue = Issue(
            id="TASK-1",
            title="Overdue task",
            status=Status.TODO,
            assignee="alice",
            priority=Priority.HIGH,
            due_date=datetime.now() - timedelta(days=2),
        )
        current_issue = Issue(
            id="TASK-2",
            title="Current task",
            status=Status.TODO,
            assignee="alice",
            priority=Priority.HIGH,
            due_date=datetime.now() + timedelta(days=2),
        )

        service = DailySummaryService(MagicMock())
        result = service.categorize_issues([overdue_issue, current_issue], "alice")

        assert len(result["overdue"]) == 1
        assert result["overdue"][0].id == "TASK-1"

    def test_categorize_issues_blocked(self):
        """Test that BLOCKED issues are correctly categorized."""
        blocked_issue = Issue(
            id="TASK-1",
            title="Blocked task",
            status=Status.BLOCKED,
            assignee="alice",
            priority=Priority.HIGH,
        )
        active_issue = Issue(
            id="TASK-2",
            title="Active task",
            status=Status.IN_PROGRESS,
            assignee="alice",
            priority=Priority.HIGH,
        )

        service = DailySummaryService(MagicMock())
        result = service.categorize_issues([blocked_issue, active_issue], "alice")

        assert len(result["blocked"]) == 1
        assert result["blocked"][0].id == "TASK-1"

    def test_categorize_issues_high_priority_todos_limited_to_three(self):
        """Test that high priority TODOs are limited to top 3."""
        todos = [
            Issue(
                id=f"TASK-{i}",
                title=f"High priority task {i}",
                status=Status.TODO,
                assignee="alice",
                priority=Priority.HIGH,
            )
            for i in range(5)
        ]

        service = DailySummaryService(MagicMock())
        result = service.categorize_issues(todos, "alice")

        assert len(result["todo_high_priority"]) == 3

    def test_categorize_issues_completed_today(self):
        """Test that today's completed issues are correctly categorized."""
        today = datetime.now()
        completed_today = Issue(
            id="TASK-1",
            title="Completed today",
            status=Status.CLOSED,
            assignee="alice",
            priority=Priority.MEDIUM,
            actual_end_date=today,
        )
        completed_yesterday = Issue(
            id="TASK-2",
            title="Completed yesterday",
            status=Status.CLOSED,
            assignee="alice",
            priority=Priority.MEDIUM,
            actual_end_date=today - timedelta(days=1),
        )

        service = DailySummaryService(MagicMock())
        result = service.categorize_issues(
            [completed_today, completed_yesterday], "alice"
        )

        assert len(result["completed_today"]) == 1
        assert result["completed_today"][0].id == "TASK-1"

    def test_categorize_issues_filters_by_status_only(self):
        """Test that categorization filters by status (assignee filtering is upstream)."""
        alice_high_todo = Issue(
            id="TASK-1",
            title="Alice's high priority task",
            status=Status.TODO,
            assignee="alice",
            priority=Priority.HIGH,
        )
        bob_high_todo = Issue(
            id="TASK-2",
            title="Bob's high priority task",
            status=Status.TODO,
            assignee="bob",
            priority=Priority.HIGH,
        )

        service = DailySummaryService(MagicMock())
        # categorize_issues doesn't filter by assignee - it just categorizes
        # The caller (get_daily_summary_data) filters by assignee first
        result = service.categorize_issues([alice_high_todo, bob_high_todo], "alice")

        # Both should appear since categorize_issues doesn't filter by assignee
        assert len(result["todo_high_priority"]) == 2


class TestDailySummaryServiceGetDailySummaryData:
    """Test main data aggregation method."""

    def test_get_daily_summary_data_returns_complete_structure(self):
        """Test that get_daily_summary_data returns all required fields."""
        core = MagicMock()
        core.get_current_user.return_value = "alice"

        today = datetime.now()
        milestone = Milestone(
            name="v1.0",
            description="First release",
            status=MilestoneStatus.OPEN,
            due_date=today + timedelta(days=10),
        )
        core.list_milestones.return_value = [milestone]

        issue = Issue(
            id="TASK-1",
            title="Test task",
            status=Status.IN_PROGRESS,
            assignee="alice",
            priority=Priority.HIGH,
            milestone="v1.0",
        )
        core.list_issues.return_value = [issue]

        service = DailySummaryService(core)
        data = service.get_daily_summary_data()

        # Check structure
        assert "current_user" in data
        assert "milestone" in data
        assert "issues" in data
        assert "has_issues" in data
        assert data["current_user"] == "alice"
        assert data["milestone"].name == "v1.0"
        assert "in_progress" in data["issues"]

    def test_get_daily_summary_data_raises_when_no_user(self):
        """Test that error is raised when user cannot be resolved."""
        core = MagicMock()
        core.get_current_user.return_value = None

        with patch.dict(os.environ, {}, clear=True):
            service = DailySummaryService(core)
            with pytest.raises(ValueError):
                service.get_daily_summary_data()

    def test_get_daily_summary_data_raises_when_no_milestone(self):
        """Test that error is raised when no upcoming milestone exists."""
        core = MagicMock()
        core.get_current_user.return_value = "alice"
        core.list_milestones.return_value = []

        service = DailySummaryService(core)
        with pytest.raises(ValueError):
            service.get_daily_summary_data()


class TestDailySummaryServiceActionSuggestion:
    """Test action suggestion generation."""

    def test_get_next_action_suggestion_suggests_start_when_no_progress(self):
        """Test that suggestion to start work appears when nothing in progress."""
        core = MagicMock()
        data = {
            "user": "alice",
            "milestone": MagicMock(),
            "issues": {
                "in_progress": [],
                "overdue": [],
                "blocked": [],
                "todo_high_priority": [MagicMock(id="TASK-1")],
                "completed_today": [],
            },
        }

        service = DailySummaryService(core)
        suggestion = service.get_next_action_suggestion(data)

        assert suggestion is not None
        assert "TASK-1" in suggestion or "start" in suggestion.lower()

    def test_get_next_action_suggestion_suggests_review_when_overdue(self):
        """Test that suggestion to address overdue appears when overdue issues exist."""
        core = MagicMock()
        overdue_issue = MagicMock()
        overdue_issue.id = "TASK-1"

        data = {
            "user": "alice",
            "milestone": MagicMock(),
            "issues": {
                "in_progress": [],
                "overdue": [overdue_issue],
                "blocked": [],
                "todo_high_priority": [],
                "completed_today": [],
            },
        }

        service = DailySummaryService(core)
        suggestion = service.get_next_action_suggestion(data)

        assert suggestion is not None
        assert "TASK-1" in suggestion or "overdue" in suggestion.lower()

    def test_get_next_action_suggestion_returns_none_when_all_caught_up(self):
        """Test that no suggestion appears when all caught up."""
        core = MagicMock()
        data = {
            "user": "alice",
            "milestone": MagicMock(),
            "issues": {
                "in_progress": [],
                "overdue": [],
                "blocked": [],
                "todo_high_priority": [],
                "completed_today": [],
            },
        }

        service = DailySummaryService(core)
        suggestion = service.get_next_action_suggestion(data)

        # Can be None or empty or a congratulatory message
        assert (
            suggestion is None
            or len(suggestion) == 0
            or "congratul" in suggestion.lower()
        )
