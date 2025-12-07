"""Issue Operations Module - Handles all issue-related CRUD operations.

This module encapsulates issue management responsibilities extracted from RoadmapCore,
including creating, reading, updating, and deleting issues, as well as issue assignment
and milestone-related queries.

Responsibilities:
- Issue CRUD operations (create, list, get, update, delete)
- Issue assignment to milestones
- Issue queries (backlog, by milestone, grouped by milestone)
- Issue movement between milestones
"""

from pathlib import Path

from roadmap.adapters.persistence.parser import IssueParser
from roadmap.common.timezone_utils import now_utc
from roadmap.core.domain import (
    Issue,
    IssueType,
    Priority,
    Status,
)
from roadmap.core.services import IssueService


class IssueOperations:
    """Manager for issue-related operations."""

    def __init__(self, issue_service: IssueService, issues_dir: Path):
        """Initialize issue operations manager.

        Args:
            issue_service: The IssueService instance for database operations
            issues_dir: Path to the issues directory
        """
        self.issue_service = issue_service
        self.issues_dir = issues_dir

    def create_issue(
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
            priority: Issue priority (default: MEDIUM)
            issue_type: Type of issue (default: OTHER)
            milestone: Milestone name (optional)
            labels: List of labels (optional)
            assignee: Assigned user (optional)
            estimated_hours: Estimated hours to complete (optional)
            depends_on: List of issue IDs this depends on (optional)
            blocks: List of issue IDs this blocks (optional)

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

    def list_issues(
        self,
        milestone: str | None = None,
        status: Status | None = None,
        priority: Priority | None = None,
        issue_type: IssueType | None = None,
        assignee: str | None = None,
    ) -> list[Issue]:
        """List issues with optional filtering.

        Args:
            milestone: Filter by milestone name (optional)
            status: Filter by issue status (optional)
            priority: Filter by priority (optional)
            issue_type: Filter by issue type (optional)
            assignee: Filter by assignee (optional)

        Returns:
            List of Issue objects matching the filters
        """
        return self.issue_service.list_issues(
            milestone=milestone,
            status=status,
            priority=priority,
            issue_type=issue_type,
            assignee=assignee,
        )

    def get_issue(self, issue_id: str) -> Issue | None:
        """Get a specific issue by ID.

        Args:
            issue_id: The issue ID to retrieve

        Returns:
            Issue object if found, None otherwise
        """
        return self.issue_service.get_issue(issue_id)

    def update_issue(self, issue_id: str, **updates) -> Issue | None:
        """Update an existing issue.

        Args:
            issue_id: The issue ID to update
            **updates: Fields to update

        Returns:
            Updated Issue object if found, None otherwise
        """
        return self.issue_service.update_issue(issue_id, **updates)

    def delete_issue(self, issue_id: str) -> bool:
        """Delete an issue.

        Args:
            issue_id: The issue ID to delete

        Returns:
            True if issue was deleted, False if not found
        """
        return self.issue_service.delete_issue(issue_id)

    def assign_issue_to_milestone(self, issue_id: str, milestone_name: str) -> bool:
        """Assign an issue to a milestone.

        Args:
            issue_id: The issue ID to assign
            milestone_name: The milestone name to assign to

        Returns:
            True if assignment successful, False if issue or milestone not found
        """
        issue = self.get_issue(issue_id)
        if not issue:
            return False

        # Validate milestone exists by checking file using same logic as Milestone.filename
        safe_name = "".join(
            c for c in milestone_name if c.isalnum() or c in (" ", "-", "_")
        ).strip()
        safe_name = safe_name.replace(" ", "-").lower()
        milestone_file = self.issues_dir.parent / "milestones" / f"{safe_name}.md"
        if not milestone_file.exists():
            return False

        # Set the milestone
        issue.milestone = milestone_name
        issue.updated = now_utc()

        # Use the file_path if available (preserves original location)
        if hasattr(issue, "file_path") and issue.file_path:
            issue_path = Path(issue.file_path)
        else:
            issue_path = self.issues_dir / issue.filename

        IssueParser.save_issue_file(issue, issue_path)

        return True

    def get_backlog_issues(self) -> list[Issue]:
        """Get all issues not assigned to any milestone (backlog).

        Returns:
            List of Issue objects in the backlog
        """
        all_issues = self.list_issues()
        return [issue for issue in all_issues if issue.is_backlog]

    def get_milestone_issues(self, milestone_name: str) -> list[Issue]:
        """Get all issues assigned to a specific milestone.

        Args:
            milestone_name: The milestone name to filter by

        Returns:
            List of Issue objects assigned to the milestone
        """
        all_issues = self.list_issues()
        return [issue for issue in all_issues if issue.milestone == milestone_name]

    def get_issues_by_milestone(self) -> dict[str, list[Issue]]:
        """Get all issues grouped by milestone, including backlog.

        Returns:
            Dictionary mapping milestone names to lists of Issue objects,
            with a "Backlog" key for unassigned issues
        """
        all_issues = self.list_issues()
        grouped: dict[str, list[Issue]] = {"Backlog": []}

        # Add backlog issues
        for issue in all_issues:
            if issue.is_backlog:
                grouped["Backlog"].append(issue)
            else:
                milestone_name = issue.milestone
                if milestone_name is None:
                    # Issues without milestone go to Backlog
                    grouped["Backlog"].append(issue)
                else:
                    if milestone_name not in grouped:
                        grouped[milestone_name] = []
                    grouped[milestone_name].append(issue)

        return grouped

    def move_issue_to_milestone(
        self, issue_id: str, milestone_name: str | None
    ) -> bool:
        """Move an issue to a milestone or to backlog if milestone_name is None.

        Args:
            issue_id: The issue ID to move
            milestone_name: The target milestone name, or None for backlog

        Returns:
            True if move successful, False if issue not found or milestone invalid
        """
        issue = self.get_issue(issue_id)
        if not issue:
            return False

        # Validate milestone exists if milestone_name is provided (None is valid for backlog)
        if milestone_name is not None:
            # Check if milestone file exists
            safe_name = "".join(
                c for c in milestone_name if c.isalnum() or c in (" ", "-", "_")
            ).strip()
            safe_name = safe_name.replace(" ", "-").lower()
            milestone_file = self.issues_dir.parent / "milestones" / f"{safe_name}.md"
            if not milestone_file.exists():
                return False

        # Update issue milestone
        issue.milestone = milestone_name
        issue.updated = now_utc()

        # Save updated issue
        issue_path = self.issues_dir / issue.filename
        IssueParser.save_issue_file(issue, issue_path)

        return True
