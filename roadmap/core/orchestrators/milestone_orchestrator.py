"""Milestone management orchestrator.

Handles milestone planning, tracking, and progress calculation.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from ...domain import Milestone

if TYPE_CHECKING:
    from ...application.services import IssueService, MilestoneService


class MilestoneOrchestrator:
    """Orchestrates milestone management operations."""

    def __init__(
        self, milestone_service: MilestoneService, issue_service: IssueService
    ):
        """Initialize with required services.

        Args:
            milestone_service: MilestoneService instance
            issue_service: IssueService instance for progress calculation
        """
        self.milestone_service = milestone_service
        self.issue_service = issue_service

    def create(
        self,
        name: str,
        description: str = "",
        due_date: datetime | None = None,
    ) -> Milestone:
        """Create a new milestone.

        Args:
            name: Milestone name
            description: Milestone description
            due_date: Target completion date

        Returns:
            Created Milestone object
        """
        return self.milestone_service.create_milestone(
            name=name, description=description, due_date=due_date
        )

    def list(self) -> list[Milestone]:
        """List all milestones.

        Returns:
            List of Milestone objects sorted by due date
        """
        return self.milestone_service.list_milestones()

    def get(self, name: str) -> Milestone | None:
        """Get a specific milestone by name.

        Args:
            name: Milestone name

        Returns:
            Milestone object if found, None otherwise
        """
        return self.milestone_service.get_milestone(name)

    def update(
        self,
        name: str,
        description: str | None = None,
        due_date: datetime | None = None,
        clear_due_date: bool = False,
        status: str | None = None,
    ) -> bool:
        """Update a milestone.

        Args:
            name: Milestone name
            description: New description
            due_date: New due date
            clear_due_date: Clear the due date if True
            status: New status

        Returns:
            True if update succeeded, False if milestone not found
        """
        return self.milestone_service.update_milestone(
            name=name,
            description=description,
            due_date=due_date,
            clear_due_date=clear_due_date,
            status=status,
        )

    def delete(self, name: str) -> bool:
        """Delete a milestone and unassign all issues from it.

        Args:
            name: Milestone name

        Returns:
            True if deleted, False if not found
        """
        return self.milestone_service.delete_milestone(name)

    def get_progress(self, name: str) -> dict[str, Any]:
        """Get progress statistics for a milestone.

        Args:
            name: Milestone name

        Returns:
            Dictionary with progress metrics (completed, total, percentage, etc.)
        """
        return self.milestone_service.get_milestone_progress(name)

    def get_issues(self, name: str) -> list:
        """Get all issues assigned to a milestone.

        Args:
            name: Milestone name

        Returns:
            List of issues in milestone
        """
        all_issues = self.issue_service.list_issues()
        return [issue for issue in all_issues if issue.milestone == name]

    def get_issues_by_status(self) -> dict[str, list]:
        """Get all issues grouped by milestone and status.

        Returns:
            Dictionary mapping milestone names to lists of issues
        """
        all_issues = self.issue_service.list_issues()
        grouped = {}

        for issue in all_issues:
            milestone_name = issue.milestone or "Backlog"
            if milestone_name not in grouped:
                grouped[milestone_name] = []
            grouped[milestone_name].append(issue)

        return grouped
