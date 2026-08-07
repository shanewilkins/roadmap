"""Repository for milestone persistence operations."""

from typing import Any

from roadmap.common.errors import OperationType, safe_operation
from roadmap.common.logging import get_logger

logger = get_logger(__name__)


class MilestoneRepository:
    """Handles all milestone-related database operations."""

    def __init__(self, get_connection, transaction):
        """Initialize repository with database connection methods.

        Args:
            get_connection: Callable that returns sqlite3 Connection
            transaction: Context manager for database transactions
        """
        self._get_connection = get_connection
        self._transaction = transaction

    @safe_operation(OperationType.CREATE, "Milestone", include_traceback=True)
    @safe_operation(OperationType.CREATE, "Milestone", include_traceback=True)
    def create(self, milestone_data: dict[str, Any]) -> str:
        """Create a new milestone.

        Args:
            milestone_data: Dictionary with milestone fields

        Returns:
            Milestone ID
        """
        with self._transaction() as conn:
            conn.execute(
                """
                INSERT INTO milestones (id, project_id, title, description, status, due_date, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    milestone_data["id"],
                    milestone_data.get("project_id"),
                    milestone_data.get("title"),
                    milestone_data.get("description"),
                    milestone_data.get("status", "open"),
                    milestone_data.get("due_date"),
                    milestone_data.get("metadata"),
                ),
            )

        logger.info("Created milestone", milestone_id=milestone_data["id"])
        return milestone_data["id"]

    def get(self, milestone_id: str) -> dict[str, Any] | None:
        """Get milestone by ID.

        Args:
            milestone_id: Milestone identifier

        Returns:
            Milestone data or None if not found
        """
        conn = self._get_connection()
        row = conn.execute(
            "SELECT * FROM milestones WHERE id = ?", (milestone_id,)
        ).fetchone()

        return dict(row) if row else None

    @safe_operation(OperationType.UPDATE, "Milestone")
    @safe_operation(OperationType.UPDATE, "Milestone")
    def update(self, milestone_id: str, updates: dict[str, Any]) -> bool:
        """Update milestone.

        Args:
            milestone_id: Milestone identifier
            updates: Dictionary of fields to update

        Returns:
            True if successful, False otherwise
        """
        if not updates:
            return False

        set_clause = ", ".join(f"{key} = ?" for key in updates.keys())
        values = list(updates.values()) + [milestone_id]

        with self._transaction() as conn:
            cursor = conn.execute(
                f"""
                UPDATE milestones SET {set_clause} WHERE id = ?
            """,
                values,
            )

        updated = cursor.rowcount > 0
        if updated:
            logger.info(
                "Updated milestone",
                milestone_id=milestone_id,
                updates=list(updates.keys()),
            )

        return updated

    @safe_operation(OperationType.UPDATE, "Milestone")
    @safe_operation(OperationType.UPDATE, "Milestone")
    def mark_archived(self, milestone_id: str, archived: bool = True) -> bool:
        """Mark a milestone as archived or unarchived.

        Args:
            milestone_id: Milestone identifier
            archived: True to archive, False to unarchive

        Returns:
            True if successful, False otherwise
        """
        with self._transaction() as conn:
            if archived:
                cursor = conn.execute(
                    "UPDATE milestones SET archived = 1, archived_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (milestone_id,),
                )
            else:
                cursor = conn.execute(
                    "UPDATE milestones SET archived = 0, archived_at = NULL WHERE id = ?",
                    (milestone_id,),
                )

        updated = cursor.rowcount > 0
        if updated:
            action = "archived" if archived else "unarchived"
            logger.info(
                "milestone_status_changed",
                milestone_id=milestone_id,
                action=action,
            )

        return updated
