"""
Issue filtering logic extracted from complex CLI command.
"""

from roadmap.application.core import RoadmapCore
from roadmap.domain import Issue, Priority, Status


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

    def __init__(self, core: RoadmapCore):
        self.core = core

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
        # Handle special assignee filters first
        if my_issues:
            return self.core.get_my_issues(), "my"

        if assignee:
            return self.core.get_assigned_issues(assignee), f"assigned to {assignee}"

        # Get base set of issues
        if backlog or unassigned:
            return self.core.get_backlog_issues(), "backlog"

        if next_milestone:
            next_ms = self.core.get_next_milestone()
            if not next_ms:
                return [], ""  # Handled by caller
            return (
                self.core.get_milestone_issues(next_ms.name),
                f"next milestone ({next_ms.name})",
            )

        if milestone:
            return self.core.get_milestone_issues(milestone), f"milestone '{milestone}'"

        # Handle overdue filter
        if overdue:
            from datetime import datetime

            all_issues = self.core.list_issues()
            overdue_issues = [
                issue
                for issue in all_issues
                if issue.due_date
                and issue.due_date.replace(tzinfo=None) < datetime.now()
            ]
            return overdue_issues, "overdue"

        # Show all issues
        return self.core.list_issues(), "all"

    def apply_additional_filters(
        self,
        issues: list[Issue],
        filter_description: str,
        open_only: bool = False,
        blocked_only: bool = False,
        status: str | None = None,
        priority: str | None = None,
        overdue: bool = False,
    ) -> tuple[list[Issue], str]:
        """
        Apply additional filters to issue list.

        Returns:
            Tuple of (filtered_issues, updated_description)
        """
        result = issues
        description = filter_description

        if open_only:
            result = [i for i in result if i.status != Status.DONE]
            description += " open"

        if blocked_only:
            result = [i for i in result if i.status == Status.BLOCKED]
            description += " blocked"

        if status:
            result = [i for i in result if i.status == Status(status)]
            description += f" {status}"

        if priority:
            result = [i for i in result if i.priority == Priority(priority)]
            description += f" {priority} priority"

        if overdue:
            from datetime import datetime

            result = [
                i
                for i in result
                if i.due_date and i.due_date.replace(tzinfo=None) < datetime.now()
            ]
            description += " overdue"

        return result, description


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
