"""Issue management orchestrator.

Handles all issue-related operations including creation, querying,
updating, and deletion of issues.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ...domain import Issue, IssueType, Priority, Status

if TYPE_CHECKING:
    from ...application.services import IssueService


class IssueOrchestrator:
    """Orchestrates issue management operations."""

    def __init__(self, issue_service: IssueService):
        """Initialize with issue service.

        Args:
            issue_service: IssueService instance
        """
        self.issue_service = issue_service

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
    ) -> Issue:
        """Create a new issue.

        Args:
            title: Issue title
            priority: Issue priority level
            issue_type: Type of issue (bug, feature, etc.)
            milestone: Associated milestone name
            labels: List of labels
            assignee: Assigned team member
            estimated_hours: Estimated time to complete
            depends_on: List of issue IDs this depends on
            blocks: List of issue IDs this blocks

        Returns:
            Created Issue object
        """
        return self.issue_service.create_issue(
            title=title,
            priority=priority,
            issue_type=issue_type,
            milestone=milestone,
            labels=labels,
            assignee=assignee,
            estimated_hours=estimated_hours,
            depends_on=depends_on,
            blocks=blocks,
        )

    def list(
        self,
        milestone: str | None = None,
        status: Status | None = None,
        priority: Priority | None = None,
        issue_type: IssueType | None = None,
        assignee: str | None = None,
    ) -> list[Issue]:
        """List issues with optional filtering.

        All filters are combined with AND logic (all must match).

        Args:
            milestone: Filter by milestone name
            status: Filter by status
            priority: Filter by priority level
            issue_type: Filter by issue type
            assignee: Filter by assignee

        Returns:
            List of matching Issue objects
        """
        return self.issue_service.list_issues(
            milestone=milestone,
            status=status,
            priority=priority,
            issue_type=issue_type,
            assignee=assignee,
        )

    def get(self, issue_id: str) -> Issue | None:
        """Get a specific issue by ID.

        Args:
            issue_id: Issue identifier

        Returns:
            Issue object if found, None otherwise
        """
        return self.issue_service.get_issue(issue_id)

    def update(self, issue_id: str, **updates) -> Issue | None:
        """Update an existing issue.

        Args:
            issue_id: Issue identifier
            **updates: Fields to update

        Returns:
            Updated Issue object if found, None otherwise
        """
        return self.issue_service.update_issue(issue_id, **updates)

    def delete(self, issue_id: str) -> bool:
        """Delete an issue.

        Args:
            issue_id: Issue identifier

        Returns:
            True if deleted, False if not found
        """
        return self.issue_service.delete_issue(issue_id)

    def assign_to_milestone(self, issue_id: str, milestone_name: str | None) -> bool:
        """Assign an issue to a milestone.

        Args:
            issue_id: Issue identifier
            milestone_name: Target milestone name (or None to remove from milestone)

        Returns:
            True if assignment succeeded, False otherwise
        """
        issue = self.get(issue_id)
        if not issue:
            return False

        if milestone_name is None:
            return self.update(issue_id, milestone=None) is not None
        return self.update(issue_id, milestone=milestone_name) is not None

    def remove_from_milestone(self, issue_id: str) -> bool:
        """Remove an issue from its milestone.

        Args:
            issue_id: Issue identifier

        Returns:
            True if removal succeeded, False otherwise
        """
        return self.assign_to_milestone(issue_id, None)

    def get_backlog(self) -> list[Issue]:
        """Get all issues not assigned to any milestone.

        Returns:
            List of backlog issues
        """
        all_issues = self.list()
        return [issue for issue in all_issues if issue.is_backlog]

    def get_by_milestone(self, milestone_name: str) -> list[Issue]:
        """Get all issues assigned to a specific milestone.

        Args:
            milestone_name: Milestone name

        Returns:
            List of issues in milestone
        """
        all_issues = self.list()
        return [issue for issue in all_issues if issue.milestone == milestone_name]
