"""Milestone Operations Module - Handles all milestone-related CRUD operations.

This module encapsulates milestone management responsibilities extracted from RoadmapCore,
including creating, reading, updating, and deleting milestones, as well as milestone-related
queries and progress tracking.

Responsibilities:
- Milestone CRUD operations (create, list, get, update, delete)
- Milestone progress tracking
- Next milestone calculation
"""

from datetime import datetime
from typing import Any

from roadmap.common.errors.error_standards import OperationType, safe_operation
from roadmap.common.logging import get_logger
from roadmap.core.domain import Milestone, MilestoneStatus
from roadmap.core.services import MilestoneService

logger = get_logger(__name__)


class MilestoneOperations:
    """Manager for milestone-related operations."""

    def __init__(self, milestone_service: MilestoneService):
        """Initialize milestone operations manager.

        Args:
            milestone_service: The MilestoneService instance for database operations
        """
        self.milestone_service = milestone_service

    @safe_operation(OperationType.CREATE, "Milestone", include_traceback=True)
    def create_milestone(
        self,
        name: str,
        headline: str = "",
        due_date: datetime | None = None,
        status: str | None = None,
    ) -> Milestone:
        """Create a new milestone.

        Args:
            name: Milestone name
            headline: Milestone headline (short summary)
            due_date: Due date for the milestone (optional)
            status: Milestone status (optional, defaults to OPEN)

        Returns:
            Created Milestone object
        """
        logger.info(
            "creating_milestone",
            milestone_name=name,
            has_headline=headline is not None,
            has_due_date=due_date is not None,
            status=status,
        )
        return self.milestone_service.create_milestone(
            name=name, headline=headline, due_date=due_date, status=status
        )

    @safe_operation(OperationType.READ, "Milestone")
    def list_milestones(self) -> list[Milestone]:
        """List all milestones.

        Returns:
            List of Milestone objects
        """
        logger.info("listing_milestones")
        return self.milestone_service.list_milestones()

    @safe_operation(OperationType.READ, "Milestone")
    def get_milestone(self, name: str) -> Milestone | None:
        """Get a specific milestone by name.

        Args:
            name: Name of the milestone (searches by YAML name field, not filename)

        Returns:
            Milestone object if found, None otherwise
        """
        logger.info("getting_milestone", milestone_name=name)
        return self.milestone_service.get_milestone(name)

    @safe_operation(OperationType.DELETE, "Milestone", include_traceback=True)
    def delete_milestone(self, name: str) -> bool:
        """Delete a milestone and unassign all issues from it.

        Args:
            name: Name of the milestone to delete

        Returns:
            True if milestone was deleted, False if not found
        """
        logger.info("deleting_milestone", milestone_name=name)
        return self.milestone_service.delete_milestone(name)

    @safe_operation(OperationType.UPDATE, "Milestone")
    def update_milestone(
        self,
        name: str,
        headline: str | None = None,
        due_date: datetime | None = None,
        clear_due_date: bool = False,
        status: str | None = None,
    ) -> bool:
        """Update a milestone's properties.

        Args:
            name: Name of the milestone to update
            headline: New headline (None to keep current)
            due_date: New due date (None to keep current)
            clear_due_date: If True, remove the due date
            status: New status (None to keep current)

        Returns:
            True if milestone was updated, False if not found or error occurred
        """
        from roadmap.common.errors.exceptions import UpdateError

        logger.info(
            "updating_milestone",
            milestone_name=name,
            has_headline=headline is not None,
            has_due_date=due_date is not None,
            clear_due_date=clear_due_date,
            has_status=status is not None,
        )
        try:
            return (
                self.milestone_service.update_milestone(
                    name=name,
                    headline=headline,
                    due_date=due_date,
                    clear_due_date=clear_due_date,
                    status=status,
                )
                is not None
            )
        except UpdateError as e:
            logger.error("milestone_update_failed", name=name, error=str(e))
            return False

    @safe_operation(OperationType.READ, "Milestone")
    def get_milestone_progress(self, milestone_name: str) -> dict[str, Any]:
        """Get progress statistics for a milestone.

        Args:
            milestone_name: Name of the milestone

        Returns:
            Dictionary containing progress metrics (completed, total, percentage, etc.)
        """
        logger.info("getting_milestone_progress", milestone_name=milestone_name)
        return self.milestone_service.get_milestone_progress(milestone_name)

    def get_next_milestone(self) -> Milestone | None:
        """Get the next upcoming milestone based on due date.

        Returns:
            The upcoming milestone with the earliest due date, or None if no upcoming milestones
        """
        milestones = self.list_milestones()

        # Filter for open milestones with due dates
        upcoming_milestones = [
            m
            for m in milestones
            if m.status == MilestoneStatus.OPEN and m.due_date is not None
        ]

        if not upcoming_milestones:
            return None

        # Sort by due date and return the earliest
        # Handle timezone-aware vs timezone-naive datetime comparison
        def get_sortable_date(milestone: Milestone) -> datetime:
            """Extract sortable date from milestone."""
            due_date = milestone.due_date
            # due_date should not be None since we filtered above, but be safe
            if due_date is None:
                return datetime.max  # Put None dates at the end
            # Convert timezone-aware dates to naive for comparison
            if due_date.tzinfo is not None:
                return due_date.replace(tzinfo=None)
            return due_date

        upcoming_milestones.sort(key=get_sortable_date)
        return upcoming_milestones[0]
