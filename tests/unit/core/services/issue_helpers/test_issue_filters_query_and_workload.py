"""Tests for issue filters module."""

from datetime import UTC, datetime, timedelta
from unittest.mock import Mock

import pytest

from roadmap.common.constants import IssueType, Priority, Status
from roadmap.core.domain import Issue
from roadmap.core.services.issue_helpers.issue_filters import (
    IssueQueryService,
    WorkloadCalculator,
)
from tests.factories import IssueBuilder


class TestIssueQueryService:
    """Tests for IssueQueryService."""

    @pytest.fixture
    def mock_core(self, mock_core_simple):
        """Create mock RoadmapCore with team, issues, milestones.

        Uses centralized mock_core_simple fixture and adds services.
        """
        mock_core_simple.team = Mock()
        mock_core_simple.issues = Mock()
        mock_core_simple.milestones = Mock()
        return mock_core_simple

    @pytest.fixture
    def service(self, mock_core):
        """Create service instance."""
        return IssueQueryService(mock_core)

    @pytest.fixture
    def sample_issues(self):
        """Create sample issues."""
        issues = []
        for i in range(3):
            issue = Issue(
                id=f"issue{i}",
                title=f"Issue {i}",
                status=Status.TODO if i % 2 == 0 else Status.IN_PROGRESS,
                priority=Priority.MEDIUM,
                estimated_hours=5.0,
            )
            issues.append(issue)
        return issues

    def test_get_filtered_issues_my_issues(self, service, mock_core, sample_issues):
        """Test getting my issues."""
        mock_core.team.get_my_issues.return_value = sample_issues

        issues, description = service.get_filtered_issues(my_issues=True)

        assert issues == sample_issues
        assert description == "my"
        mock_core.team.get_my_issues.assert_called_once()

    def test_get_filtered_issues_assignee(self, service, mock_core, sample_issues):
        """Test getting issues by assignee."""
        mock_core.team.get_assigned_issues.return_value = sample_issues

        issues, description = service.get_filtered_issues(assignee="user1")

        assert issues == sample_issues
        assert "assigned to user1" in description
        mock_core.team.get_assigned_issues.assert_called_once_with("user1")

    def test_get_filtered_issues_backlog(self, service, mock_core, sample_issues):
        """Test getting backlog issues."""
        mock_core.issues.get_backlog.return_value = sample_issues

        issues, description = service.get_filtered_issues(backlog=True)

        assert issues == sample_issues
        assert description == "backlog"

    def test_get_filtered_issues_unassigned(self, service, mock_core, sample_issues):
        """Test getting unassigned issues."""
        mock_core.issues.get_backlog.return_value = sample_issues

        issues, description = service.get_filtered_issues(unassigned=True)

        assert issues == sample_issues
        assert description == "backlog"

    def test_get_filtered_issues_next_milestone(
        self, service, mock_core, sample_issues
    ):
        """Test getting issues for next milestone."""
        mock_milestone = Mock()
        mock_milestone.name = "v1.0"
        mock_core.milestones.get_next.return_value = mock_milestone
        mock_core.issues.get_by_milestone.return_value = sample_issues

        issues, description = service.get_filtered_issues(next_milestone=True)

        assert issues == sample_issues
        assert "next milestone" in description and "v1.0" in description

    def test_get_filtered_issues_next_milestone_not_found(self, service, mock_core):
        """Test handling when next milestone doesn't exist."""
        mock_core.milestones.get_next.return_value = None

        issues, description = service.get_filtered_issues(next_milestone=True)

        assert issues == []

    def test_get_filtered_issues_specific_milestone(
        self, service, mock_core, sample_issues
    ):
        """Test getting issues for specific milestone."""
        mock_core.issues.get_by_milestone.return_value = sample_issues

        issues, description = service.get_filtered_issues(milestone="v2.0")

        assert issues == sample_issues
        assert "milestone 'v2.0'" in description
        mock_core.issues.get_by_milestone.assert_called_once_with("v2.0")

    def test_get_filtered_issues_overdue(self, service, mock_core):
        """Test getting overdue issues."""
        now = datetime.now(UTC)
        overdue_issue = Issue(
            id="overdue",
            title="Overdue",
            due_date=now - timedelta(days=1),
        )
        current_issue = Issue(
            id="current",
            title="Current",
            due_date=now + timedelta(days=1),
        )

        mock_core.issues.list.return_value = [overdue_issue, current_issue]

        issues, description = service.get_filtered_issues(overdue=True)

        assert len(issues) == 1
        assert issues[0].id == "overdue"
        assert description == "overdue"

    def test_get_filtered_issues_all_when_no_filters(
        self, service, mock_core, sample_issues
    ):
        """Test getting all issues when no filters applied."""
        mock_core.issues.list.return_value = sample_issues

        issues, description = service.get_filtered_issues()

        assert issues == sample_issues
        assert description == "all"

    def test_apply_additional_filters_open_only(self, service, sample_issues):
        """Test filtering to open issues only."""
        closed_issue = Issue(
            id="closed",
            title="Closed",
            status=Status.CLOSED,
        )
        all_issues = sample_issues + [closed_issue]

        filtered, description = service.apply_additional_filters(
            all_issues, "all", open_only=True
        )

        assert len(filtered) == len(sample_issues)
        assert all(i.status != Status.CLOSED for i in filtered)
        assert "open" in description

    def test_apply_additional_filters_blocked_only(self, service):
        """Test filtering to blocked issues only."""
        blocked_issue = Issue(
            id="blocked",
            title="Blocked",
            status=Status.BLOCKED,
        )
        todo_issue = Issue(
            id="todo",
            title="TODO",
            status=Status.TODO,
        )
        all_issues = [blocked_issue, todo_issue]

        filtered, description = service.apply_additional_filters(
            all_issues, "all", blocked_only=True
        )

        assert len(filtered) == 1
        assert filtered[0].status == Status.BLOCKED
        assert "blocked" in description

    def test_apply_additional_filters_by_status(self, service, sample_issues):
        """Test filtering by specific status."""
        filtered, description = service.apply_additional_filters(
            sample_issues, "all", status=Status.TODO.value
        )

        assert all(i.status == Status.TODO for i in filtered)
        assert Status.TODO.value in description

    def test_apply_additional_filters_by_priority(self, service):
        """Test filtering by priority."""
        high_priority = Issue(
            id="high",
            title="High",
            priority=Priority.HIGH,
        )
        low_priority = Issue(
            id="low",
            title="Low",
            priority=Priority.LOW,
        )
        all_issues = [high_priority, low_priority]

        filtered, description = service.apply_additional_filters(
            all_issues, "all", priority=Priority.HIGH.value
        )

        assert len(filtered) == 1
        assert filtered[0].priority == Priority.HIGH
        assert "high" in description.lower()

    def test_apply_additional_filters_by_type(self, service):
        """Test filtering by issue type."""
        feature = Issue(
            id="feature",
            title="Feature",
            issue_type=IssueType.FEATURE,
        )
        bug = Issue(
            id="bug",
            title="Bug",
            issue_type=IssueType.BUG,
        )
        all_issues = [feature, bug]

        filtered, description = service.apply_additional_filters(
            all_issues, "all", issue_type=IssueType.FEATURE.value
        )

        assert len(filtered) == 1
        assert filtered[0].issue_type == IssueType.FEATURE

    def test_apply_additional_filters_overdue(self, service):
        """Test filtering to overdue issues."""
        now = datetime.now(UTC)
        overdue = Issue(
            id="overdue",
            title="Overdue",
            due_date=now - timedelta(days=1),
        )
        future = Issue(
            id="future",
            title="Future",
            due_date=now + timedelta(days=1),
        )
        all_issues = [overdue, future]

        filtered, description = service.apply_additional_filters(
            all_issues, "all", overdue=True
        )

        assert len(filtered) == 1
        assert filtered[0].id == "overdue"
        assert "overdue" in description

    def test_apply_multiple_additional_filters(self, service):
        """Test applying multiple filters together."""
        issues = [
            Issue(
                id="1",
                title="Issue 1",
                status=Status.IN_PROGRESS,
                priority=Priority.HIGH,
                issue_type=IssueType.FEATURE,
            ),
            Issue(
                id="2",
                title="Issue 2",
                status=Status.TODO,
                priority=Priority.LOW,
                issue_type=IssueType.BUG,
            ),
        ]

        filtered, description = service.apply_additional_filters(
            issues, "all", status=Status.IN_PROGRESS.value, priority=Priority.HIGH.value
        )

        assert len(filtered) == 1
        assert filtered[0].id == "1"


class TestWorkloadCalculator:
    """Tests for WorkloadCalculator."""

    def test_calculate_workload_empty_list(self):
        """Test calculating workload for empty list."""
        result = WorkloadCalculator.calculate_workload([])

        assert result["total_hours"] == 0
        assert result["status_breakdown"] == {}

    def test_calculate_workload_single_issue(self):
        """Test calculating workload for single issue."""
        issue = Issue(
            id="1",
            title="Issue",
            status=Status.TODO,
            estimated_hours=5.0,
        )

        result = WorkloadCalculator.calculate_workload([issue])

        assert result["total_hours"] == 5.0
        assert Status.TODO.value in result["status_breakdown"]
        assert result["status_breakdown"][Status.TODO.value]["count"] == 1
        assert result["status_breakdown"][Status.TODO.value]["hours"] == 5.0

    def test_calculate_workload_multiple_issues(self):
        """Test calculating workload for multiple issues."""
        issues = [
            IssueBuilder()
            .with_id("1")
            .with_title("Issue 1")
            .with_status(Status.TODO)
            .with_estimated_hours(5.0)
            .build(),
            IssueBuilder()
            .with_id("2")
            .with_title("Issue 2")
            .with_status(Status.IN_PROGRESS)
            .with_estimated_hours(10.0)
            .build(),
            IssueBuilder()
            .with_id("3")
            .with_title("Issue 3")
            .with_status(Status.TODO)
            .with_estimated_hours(3.0)
            .build(),
        ]

        result = WorkloadCalculator.calculate_workload(issues)

        assert result["total_hours"] == 18.0
        assert result["status_breakdown"][Status.TODO.value]["count"] == 2
        assert result["status_breakdown"][Status.TODO.value]["hours"] == 8.0
        assert result["status_breakdown"][Status.IN_PROGRESS.value]["count"] == 1
        assert result["status_breakdown"][Status.IN_PROGRESS.value]["hours"] == 10.0

    def test_calculate_workload_missing_estimated_hours(self):
        """Test calculating workload when some issues lack estimates."""
        issues = [
            IssueBuilder()
            .with_id("1")
            .with_title("Issue 1")
            .with_status(Status.TODO)
            .with_estimated_hours(5.0)
            .build(),
            IssueBuilder()
            .with_id("2")
            .with_title("Issue 2")
            .with_status(Status.TODO)
            .with_estimated_hours(None)
            .build(),
            IssueBuilder()
            .with_id("3")
            .with_title("Issue 3")
            .with_status(Status.TODO)
            .with_estimated_hours(3.0)
            .build(),
        ]

        result = WorkloadCalculator.calculate_workload(issues)

        assert result["total_hours"] == 8.0
        assert result["status_breakdown"][Status.TODO.value]["count"] == 3
        assert result["status_breakdown"][Status.TODO.value]["hours"] == 8.0

    def test_format_time_display_minutes(self):
        """Test formatting time in minutes."""
        result = WorkloadCalculator.format_time_display(0.5)
        assert "m" in result

    def test_format_time_display_hours(self):
        """Test formatting time in hours."""
        result = WorkloadCalculator.format_time_display(5.0)
        assert "h" in result

    def test_format_time_display_hours_24(self):
        """Test formatting exactly 24 hours."""
        result = WorkloadCalculator.format_time_display(24.0)
        assert "h" in result

    def test_format_time_display_days(self):
        """Test formatting time in days."""
        result = WorkloadCalculator.format_time_display(25.0)
        assert "d" in result

    @pytest.mark.parametrize(
        "hours,expected_unit",
        [
            (0.5, "m"),
            (0.9, "m"),
            (1.0, "h"),
            (8.0, "h"),
            (24.0, "h"),
            (25.0, "d"),
            (40.0, "d"),
            (80.0, "d"),
        ],
    )
    def test_format_time_display_parametrized(self, hours, expected_unit):
        """Test formatting various time values."""
        result = WorkloadCalculator.format_time_display(hours)
        assert expected_unit in result
