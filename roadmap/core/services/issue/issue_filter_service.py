"""
Issue filtering service for issue queries and filtering.

Provides utilities for filtering issues based on various criteria and calculating workload.
"""

from datetime import UTC
from typing import TYPE_CHECKING

from roadmap.core.domain import Issue, Priority, Status

if TYPE_CHECKING:
    from roadmap.infrastructure.coordination.core import RoadmapCore  # noqa: F401


class IssueFilterValidator:
    """Validates filter combinations for issue queries."""

    @staticmethod
    def validate_filters(
        assignee: str | None,
        my_issues: bool,
        backlog: bool,
        unassigned: bool,
        next_milestone: bool,
        milestone: str | None,
    ) -> tuple[bool, str | None]:
        """
        Validate that filter combinations are valid.

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check for conflicting assignee filters
        assignee_filters = [assignee is not None, my_issues]
        if sum(bool(f) for f in assignee_filters) > 1:
            return False, "Cannot combine --assignee and --my-issues filters"

        # Check for conflicting milestone filters
        exclusive_filters = [backlog, unassigned, next_milestone, milestone is not None]
        if sum(bool(f) for f in exclusive_filters) > 1:
            return (
                False,
                "Cannot combine --backlog, --unassigned, --next-milestone, and --milestone filters",
            )

        return True, None


class IssueQueryService:
    """Service for querying issues with different filter criteria."""

    def __init__(self, core: "RoadmapCore"):  # noqa: F821
        self.core = core

    def _get_issues_for_assignee_filters(
        self, my_issues: bool, assignee: str | None
    ) -> tuple[list[Issue], str] | None:
        """Get issues for assignee-based filters. Returns None if no match."""
        if my_issues:
            return self.core.team.get_my_issues(), "my"
        if assignee:
            return self.core.team.get_assigned_issues(
                assignee
            ), f"assigned to {assignee}"
        return None

    def _get_issues_for_collection_filters(
        self,
        backlog: bool,
        unassigned: bool,
        next_milestone: bool,
        milestone: str | None,
    ) -> tuple[list[Issue], str] | None:
        """Get issues for collection-based filters. Returns None if no match."""
        if backlog or unassigned:
            return self.core.issues.get_backlog(), "backlog"

        if next_milestone:
            next_ms = self.core.milestones.get_next()
            if not next_ms:
                return [], ""  # Handled by caller
            return (
                self.core.issues.get_by_milestone(next_ms.name),
                f"next milestone ({next_ms.name})",
            )

        if milestone:
            return (
                self.core.issues.get_by_milestone(milestone),
                f"milestone '{milestone}'",
            )
        return None

    def _get_overdue_issues(self) -> tuple[list[Issue], str]:
        """Get overdue issues."""
        from datetime import datetime

        all_issues = self.core.issues.list()
        now = datetime.now(UTC)
        overdue_issues: list[Issue] = []
        for issue in all_issues:
            if not issue.due_date:
                continue

            due = issue.due_date
            if isinstance(due, datetime):
                if due.tzinfo:
                    due_aware = due.astimezone(UTC)
                else:
                    due_aware = due.replace(tzinfo=UTC)
            else:
                due_aware = datetime.fromisoformat(str(due)).replace(tzinfo=UTC)

            if due_aware < now:
                overdue_issues.append(issue)

        return overdue_issues, "overdue"

    def get_filtered_issues(
        self,
        milestone: str | None = None,
        backlog: bool = False,
        unassigned: bool = False,
        next_milestone: bool = False,
        assignee: str | None = None,
        my_issues: bool = False,
        overdue: bool = False,
    ) -> tuple[list[Issue], str]:
        """
        Get issues based on primary filter criteria.

        Returns:
            Tuple of (issues, filter_description)
        """
        # Try assignee filters first
        result = self._get_issues_for_assignee_filters(my_issues, assignee)
        if result is not None:
            return result

        # Try collection filters
        result = self._get_issues_for_collection_filters(
            backlog, unassigned, next_milestone, milestone
        )
        if result is not None:
            return result

        # Handle overdue filter
        if overdue:
            return self._get_overdue_issues()

        # Show all issues
        return self.core.issues.list(), "all"

    def apply_additional_filters(
        self,
        issues: list[Issue],
        filter_description: str,
        open_only: bool = False,
        blocked_only: bool = False,
        status: str | None = None,
        priority: str | None = None,
        issue_type: str | None = None,
        overdue: bool = False,
    ) -> tuple[list[Issue], str]:
        """
        Apply additional filters to issue list.

        Returns:
            Tuple of (filtered_issues, updated_description)
        """
        result = issues
        description = filter_description

        # Apply each filter in sequence
        if open_only:
            result, description = self._filter_by_open_status(result, description)

        if blocked_only:
            result, description = self._filter_by_blocked_status(result, description)

        if status:
            result, description = self._filter_by_status(result, description, status)

        if priority:
            result, description = self._filter_by_priority(
                result, description, priority
            )

        if issue_type:
            result, description = self._filter_by_type(result, description, issue_type)

        if overdue:
            result, description = self._filter_by_overdue(result, description)

        return result, description

    @staticmethod
    def _filter_by_open_status(
        issues: list[Issue], description: str
    ) -> tuple[list[Issue], str]:
        """Filter to only open issues (not closed)."""
        filtered = [i for i in issues if i.status != Status.CLOSED]
        return filtered, description + " open"

    @staticmethod
    def _filter_by_blocked_status(
        issues: list[Issue], description: str
    ) -> tuple[list[Issue], str]:
        """Filter to only blocked issues."""
        filtered = [i for i in issues if i.status == Status.BLOCKED]
        return filtered, description + " blocked"

    @staticmethod
    def _filter_by_status(
        issues: list[Issue], description: str, status: str
    ) -> tuple[list[Issue], str]:
        """Filter by specific status."""
        filtered = [i for i in issues if i.status == Status(status)]
        return filtered, description + f" {status}"

    @staticmethod
    def _filter_by_priority(
        issues: list[Issue], description: str, priority: str
    ) -> tuple[list[Issue], str]:
        """Filter by priority level."""
        filtered = [i for i in issues if i.priority == Priority(priority)]
        return filtered, description + f" {priority} priority"

    @staticmethod
    def _filter_by_type(
        issues: list[Issue], description: str, issue_type: str
    ) -> tuple[list[Issue], str]:
        """Filter by issue type."""
        from roadmap.core.domain import IssueType

        filtered = [i for i in issues if i.issue_type == IssueType(issue_type)]
        return filtered, description + f" {issue_type}"

    @staticmethod
    def _filter_by_overdue(
        issues: list[Issue], description: str
    ) -> tuple[list[Issue], str]:
        """Filter to only overdue issues."""
        from datetime import datetime

        now = datetime.now(UTC)
        filtered: list[Issue] = []
        for i in issues:
            if not i.due_date:
                continue

            due = i.due_date
            if isinstance(due, datetime):
                if due.tzinfo:
                    due_aware = due.astimezone(UTC)
                else:
                    due_aware = due.replace(tzinfo=UTC)
            else:
                due_aware = datetime.fromisoformat(str(due)).replace(tzinfo=UTC)

            if due_aware < now:
                filtered.append(i)

        return filtered, description + " overdue"


class WorkloadCalculator:
    """Calculates time estimates and workload breakdowns."""

    @staticmethod
    def calculate_workload(issues: list[Issue]) -> dict:
        """
        Calculate workload statistics for a list of issues.

        Returns:
            Dictionary with total_hours, status_breakdown
        """
        total_hours = sum(issue.estimated_hours or 0 for issue in issues)

        status_counts = {}
        for issue in issues:
            status = issue.status.value
            if status not in status_counts:
                status_counts[status] = {"count": 0, "hours": 0}
            status_counts[status]["count"] += 1
            status_counts[status]["hours"] += issue.estimated_hours or 0

        return {
            "total_hours": total_hours,
            "status_breakdown": status_counts,
        }

    @staticmethod
    def format_time_display(hours: float) -> str:
        """Format time in hours to human-readable display."""
        if hours < 1:
            return f"{hours * 60:.0f}m"
        elif hours <= 24:
            return f"{hours:.1f}h"
        else:
            return f"{hours / 8:.1f}d"
