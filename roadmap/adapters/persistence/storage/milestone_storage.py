"""Milestone storage operations."""

from typing import Any

from roadmap.common.errors import OperationType, safe_operation
from roadmap.common.logging import get_logger

from ..repositories import MilestoneRepository

logger = get_logger(__name__)


class MilestoneStorage:
    """Handles milestone CRUD operations."""

    def __init__(self, milestone_repo: MilestoneRepository):
        """Initialize milestone storage.

        Args:
            milestone_repo: MilestoneRepository instance for data access
        """
        self._milestone_repo = milestone_repo
        logger.debug("milestone_storage_initialized")

    @safe_operation(OperationType.CREATE, "Milestone", include_traceback=True)
    def create(self, milestone_data: dict[str, Any]) -> str:
        """Create a new milestone.

        Args:
            milestone_data: Milestone data dictionary

        Returns:
            str: ID of created milestone
        """
        logger.debug("Creating milestone", keys=list(milestone_data.keys()))
        return self._milestone_repo.create(milestone_data)

    def get(self, milestone_id: str) -> dict[str, Any] | None:
        """Get milestone by ID.

        Args:
            milestone_id: Milestone identifier

        Returns:
            dict: Milestone data or None if not found
        """
        logger.debug("Getting milestone", milestone_id=milestone_id)
        return self._milestone_repo.get(milestone_id)

    @safe_operation(OperationType.UPDATE, "Milestone", include_traceback=True)
    def update(self, milestone_id: str, updates: dict[str, Any]) -> bool:
        """Update milestone.

        Args:
            milestone_id: Milestone identifier
            updates: Dictionary of fields to update

        Returns:
            bool: True if update successful
        """
        logger.debug(
            "Updating milestone", milestone_id=milestone_id, keys=list(updates.keys())
        )
        return self._milestone_repo.update(milestone_id, updates)

    @safe_operation(OperationType.UPDATE, "Milestone")
    def mark_archived(self, milestone_id: str, archived: bool = True) -> bool:
        """Mark a milestone as archived or unarchived.

        Args:
            milestone_id: Milestone identifier
            archived: Whether to archive (True) or unarchive (False)

        Returns:
            bool: True if operation successful
        """
        logger.debug(
            "Marking milestone archived", milestone_id=milestone_id, archived=archived
        )
        return self._milestone_repo.mark_archived(milestone_id, archived)
