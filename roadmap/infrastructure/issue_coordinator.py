"""Issue Coordinator - Coordinates issue-related operations

Extracted from RoadmapCore to reduce god object complexity.
Provides a focused API for all issue-related concerns.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from roadmap.core.domain import IssueType, Priority, Status
from roadmap.infrastructure.issue_operations import IssueOperations

if TYPE_CHECKING:
    from roadmap.core.domain import Issue
    from roadmap.infrastructure.core import RoadmapCore


class IssueCoordinator:
    """Coordinates all issue-related operations."""

    def __init__(self, issue_ops: IssueOperations, core: RoadmapCore | None = None):
        """Initialize coordinator with issue operations manager.

        Args:
            issue_ops: IssueOperations instance
            core: RoadmapCore instance for initialization checks
        """
        self._ops = issue_ops
        self._core = core

    # CRUD Operations
    def create(
        self,
        title: str,
        priority: Priority = Priority.MEDIUM,
        issue_type: IssueType = IssueType.OTHER,
        milestone: str | None = None,
        labels: list[str] | None = None,
        assignee: str | None = None,
        estimated_hours: float | None = None,
        depends_on: list[str] | None = None,
        blocks: list[str] | None = None,
        status: str | None = None,
    ) -> Issue:
        """Create a new issue."""
        return self._ops.create_issue(
            title=title,
            priority=priority,
            issue_type=issue_type,
            milestone=milestone,
            labels=labels,
            assignee=assignee,
            estimated_hours=estimated_hours,
            depends_on=depends_on,
            blocks=blocks,
            status=status,
        )

    def list(
        self,
        milestone: str | None = None,
        status: Status | None = None,
        priority: Priority | None = None,
        issue_type: IssueType | None = None,
        assignee: str | None = None,
    ) -> list[Issue]:
        """List issues with optional filtering."""
        return self._ops.list_issues(
            milestone=milestone,
            status=status,
            priority=priority,
            issue_type=issue_type,
            assignee=assignee,
        )

    def get(self, issue_id: str) -> Issue | None:
        """Get a specific issue by ID."""
        return self._ops.get_issue(issue_id)

    def update(self, issue_id: str, **updates) -> Issue | None:
        """Update an existing issue."""
        return self._ops.update_issue(issue_id, **updates)

    def delete(self, issue_id: str) -> bool:
        """Delete an issue."""
        return self._ops.delete_issue(issue_id)

    # Milestone-related queries
    def get_backlog(self) -> list[Issue]:
        """Get all issues not assigned to any milestone (backlog)."""
        return self._ops.get_backlog_issues()

    def get_by_milestone(self, milestone_name: str) -> list[Issue]:
        """Get all issues assigned to a specific milestone."""
        return self._ops.get_milestone_issues(milestone_name)

    def get_grouped_by_milestone(self) -> dict[str, list[Issue]]:
        """Get all issues grouped by milestone, including backlog."""
        return self._ops.get_issues_by_milestone()

    def move_to_milestone(self, issue_id: str, milestone_name: str | None) -> bool:
        """Move an issue to a milestone or to backlog if milestone_name is None."""
        return self._ops.move_issue_to_milestone(issue_id, milestone_name)

    def assign_to_milestone(self, issue_id: str, milestone_name: str) -> bool:
        """Assign an issue to a milestone."""
        return self._ops.assign_issue_to_milestone(issue_id, milestone_name)

    def batch_assign_to_milestone(
        self,
        issue_ids: list[str],
        milestone_name: str,
        preloaded_issues: list | None = None,
    ) -> tuple[int, int]:
        """Batch assign multiple issues to a milestone in a single pass.

        Args:
            issue_ids: List of issue IDs to assign
            milestone_name: The milestone name to assign to
            preloaded_issues: Optional pre-loaded list of issues (avoids filesystem scan)

        Returns:
            Tuple of (successful_count, failed_count)
        """
        return self._ops.batch_assign_to_milestone(
            issue_ids, milestone_name, preloaded_issues
        )

    def get_similar_milestone_names(
        self, milestone_name: str, max_results: int = 3
    ) -> list[str]:
        """Find milestone names similar to the given name.

        Args:
            milestone_name: The milestone name to find similar matches for
            max_results: Maximum number of suggestions to return

        Returns:
            List of similar milestone names found
        """
        return self._ops.get_similar_milestone_names(milestone_name, max_results)
