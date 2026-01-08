"""Milestone Coordinator - Coordinates milestone-related operations

Extracted from RoadmapCore to reduce god object complexity.
Provides a focused API for all milestone-related concerns.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from roadmap.core.domain import Milestone
from roadmap.infrastructure.milestone_consistency_validator import (
    MilestoneConsistencyValidator,
)
from roadmap.infrastructure.milestone_operations import MilestoneOperations

if TYPE_CHECKING:
    from roadmap.infrastructure.core import RoadmapCore


class MilestoneCoordinator:
    """Coordinates all milestone-related operations."""

    def __init__(
        self,
        milestone_ops: MilestoneOperations,
        milestones_dir,
        core: RoadmapCore | None = None,
    ):
        """Initialize coordinator with milestone operations manager.

        Args:
            milestone_ops: MilestoneOperations instance
            milestones_dir: Path to milestones directory
            core: RoadmapCore instance for initialization checks
        """
        self._ops = milestone_ops
        self._consistency_validator = MilestoneConsistencyValidator(milestones_dir)
        self._core = core

    # CRUD Operations
    def create(
        self,
        name: str,
        headline: str = "",
        due_date: datetime | None = None,
        status: str | None = None,
        project_id: str | None = None,
    ) -> Milestone:
        """Create a new milestone."""
        milestone = self._ops.create_milestone(
            name=name, headline=headline, due_date=due_date, status=status
        )

        # Assign to project if provided
        if project_id:
            milestone.project_id = project_id

        return milestone

    def list(self) -> list[Milestone]:
        """List all milestones."""
        return self._ops.list_milestones()

    def get(self, name: str) -> Milestone | None:
        """Get a specific milestone by name (searches by YAML name field, not filename)."""
        return self._ops.get_milestone(name)

    def update(
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
            True if milestone was updated, False if not found
        """
        return self._ops.update_milestone(
            name=name,
            headline=headline,
            due_date=due_date,
            clear_due_date=clear_due_date,
            status=status,
        )

    def delete(self, name: str) -> bool:
        """Delete a milestone and unassign all issues from it.

        Args:
            name: Name of the milestone to delete

        Returns:
            True if milestone was deleted, False if not found
        """
        return self._ops.delete_milestone(name)

    def get_progress(self, milestone_name: str) -> dict[str, Any]:
        """Get progress statistics for a milestone."""
        return self._ops.get_milestone_progress(milestone_name)

    def get_next(self) -> Milestone | None:
        """Get the next upcoming milestone based on due date."""
        return self._ops.get_next_milestone()

    # Consistency and Validation
    def validate_naming_consistency(self) -> list[dict[str, str]]:
        """Check for inconsistencies between milestone filenames and name fields.

        Returns:
            List of dictionaries with inconsistency details
        """
        return self._consistency_validator.validate()

    def fix_naming_consistency(self) -> dict[str, list[str]]:
        """Fix milestone filename inconsistencies by renaming files to match name fields.

        Returns:
            Dictionary with 'renamed' and 'errors' lists
        """
        return self._consistency_validator.fix()
