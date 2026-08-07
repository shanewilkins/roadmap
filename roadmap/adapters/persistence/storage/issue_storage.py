"""Issue storage operations."""

from typing import Any

from roadmap.common.errors import OperationType, safe_operation
from roadmap.common.logging import get_logger

from ..repositories import IssueRepository

logger = get_logger(__name__)


class IssueStorage:
    """Handles issue CRUD operations."""

    def __init__(self, issue_repo: IssueRepository):
        """Initialize issue storage.

        Args:
            issue_repo: IssueRepository instance for data access
        """
        self._issue_repo = issue_repo
        logger.debug("issue_storage_initialized")

    @safe_operation(OperationType.CREATE, "Issue", include_traceback=True)
    def create(self, issue_data: dict[str, Any]) -> str:
        """Create a new issue.

        Args:
            issue_data: Issue data dictionary

        Returns:
            str: ID of created issue
        """
        logger.debug("Creating issue", keys=list(issue_data.keys()))
        return self._issue_repo.create(issue_data)

    def get(self, issue_id: str) -> dict[str, Any] | None:
        """Get issue by ID.

        Args:
            issue_id: Issue identifier

        Returns:
            dict: Issue data or None if not found
        """
        logger.debug("Getting issue", issue_id=issue_id)
        return self._issue_repo.get(issue_id)

    @safe_operation(OperationType.UPDATE, "Issue", include_traceback=True)
    def update(self, issue_id: str, updates: dict[str, Any]) -> bool:
        """Update issue.

        Args:
            issue_id: Issue identifier
            updates: Dictionary of fields to update

        Returns:
            bool: True if update successful
        """
        logger.debug("Updating issue", issue_id=issue_id, keys=list(updates.keys()))
        return self._issue_repo.update(issue_id, updates)

    @safe_operation(OperationType.DELETE, "Issue", include_traceback=True)
    def delete(self, issue_id: str) -> bool:
        """Delete issue.

        Args:
            issue_id: Issue identifier

        Returns:
            bool: True if deletion successful
        """
        logger.debug("Deleting issue", issue_id=issue_id)
        return self._issue_repo.delete(issue_id)

    @safe_operation(OperationType.UPDATE, "Issue")
    def mark_archived(self, issue_id: str, archived: bool = True) -> bool:
        """Mark an issue as archived or unarchived.

        Args:
            issue_id: Issue identifier
            archived: Whether to archive (True) or unarchive (False)

        Returns:
            bool: True if operation successful
        """
        logger.debug("Marking issue archived", issue_id=issue_id, archived=archived)
        return self._issue_repo.mark_archived(issue_id, archived)
