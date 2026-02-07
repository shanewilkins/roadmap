"""Repository for issue persistence operations."""

from typing import Any

from roadmap.common.errors import OperationType, safe_operation
from roadmap.common.logging import get_logger

logger = get_logger(__name__)


class IssueRepository:
    """Handles all issue-related database operations."""

    def __init__(self, get_connection, transaction):
        """Initialize repository with database connection methods.

        Args:
            get_connection: Callable that returns sqlite3 Connection
            transaction: Context manager for database transactions
        """
        self._get_connection = get_connection
        self._transaction = transaction

    @safe_operation(OperationType.CREATE, "Issue", include_traceback=True)
    @safe_operation(OperationType.CREATE, "Issue", include_traceback=True)
    def create(self, issue_data: dict[str, Any]) -> str:
        """Create a new issue.

        Args:
            issue_data: Dictionary with issue fields

        Returns:
            Issue ID
        """
        with self._transaction() as conn:
            conn.execute(
                """
                INSERT INTO issues (id, project_id, milestone_id, title, headline, description, status, priority, issue_type, assignee, estimate_hours, due_date, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    issue_data["id"],
                    issue_data.get("project_id"),
                    issue_data.get("milestone_id"),
                    issue_data.get("title"),
                    issue_data.get("headline", ""),
                    issue_data.get("description"),
                    issue_data.get("status", "open"),
                    issue_data.get("priority", "medium"),
                    issue_data.get("issue_type", "task"),
                    issue_data.get("assignee"),
                    issue_data.get("estimate_hours"),
                    issue_data.get("due_date"),
                    issue_data.get("metadata"),
                ),
            )

        logger.info("Created issue", issue_id=issue_data["id"])
        return issue_data["id"]

    def get(self, issue_id: str) -> dict[str, Any] | None:
        """Get issue by ID.

        Args:
            issue_id: Issue identifier

        Returns:
            Issue data or None if not found
        """
        conn = self._get_connection()
        row = conn.execute("SELECT * FROM issues WHERE id = ?", (issue_id,)).fetchone()

        return dict(row) if row else None

    @safe_operation(OperationType.UPDATE, "Issue")
    @safe_operation(OperationType.UPDATE, "Issue")
    def update(self, issue_id: str, updates: dict[str, Any]) -> bool:
        """Update issue.

        Args:
            issue_id: Issue identifier
            updates: Dictionary of fields to update

        Returns:
            True if successful, False otherwise
        """
        if not updates:
            return False

        set_clause = ", ".join(f"{key} = ?" for key in updates.keys())
        values = list(updates.values()) + [issue_id]

        with self._transaction() as conn:
            cursor = conn.execute(
                f"""
                UPDATE issues SET {set_clause} WHERE id = ?
            """,
                values,
            )

        updated = cursor.rowcount > 0
        if updated:
            logger.info(
                "Updated issue", issue_id=issue_id, updates=list(updates.keys())
            )

        return updated

    @safe_operation(OperationType.DELETE, "Issue", include_traceback=True)
    @safe_operation(OperationType.DELETE, "Issue", include_traceback=True)
    def delete(self, issue_id: str) -> bool:
        """Delete issue.

        Args:
            issue_id: Issue identifier

        Returns:
            True if successful, False otherwise
        """
        with self._transaction() as conn:
            cursor = conn.execute("DELETE FROM issues WHERE id = ?", (issue_id,))

        deleted = cursor.rowcount > 0
        if deleted:
            logger.info("Deleted issue", issue_id=issue_id)

        return deleted

    @safe_operation(OperationType.DELETE, "Issue", include_traceback=True)
    def delete_many(self, issue_ids: list[str]) -> int:
        """Delete multiple issues in a single transaction.

        Batch delete is much more efficient than deleting one-by-one
        as it avoids repeated cache invalidations and enumeration.

        Args:
            issue_ids: List of issue identifiers to delete

        Returns:
            Number of issues successfully deleted
        """
        if not issue_ids:
            return 0

        with self._transaction() as conn:
            placeholders = ",".join("?" * len(issue_ids))
            cursor = conn.execute(
                f"DELETE FROM issues WHERE id IN ({placeholders})",
                issue_ids,
            )

        deleted_count = cursor.rowcount
        if deleted_count > 0:
            logger.info(
                "Deleted multiple issues",
                count=deleted_count,
                issue_count=len(issue_ids),
            )

        return deleted_count

    @safe_operation(OperationType.UPDATE, "Issue")
    @safe_operation(OperationType.UPDATE, "Issue")
    def mark_archived(self, issue_id: str, archived: bool = True) -> bool:
        """Mark an issue as archived or unarchived.

        Args:
            issue_id: Issue identifier
            archived: True to archive, False to unarchive

        Returns:
            True if successful, False otherwise
        """
        with self._transaction() as conn:
            if archived:
                cursor = conn.execute(
                    "UPDATE issues SET archived = 1, archived_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (issue_id,),
                )
            else:
                cursor = conn.execute(
                    "UPDATE issues SET archived = 0, archived_at = NULL WHERE id = ?",
                    (issue_id,),
                )

        updated = cursor.rowcount > 0
        if updated:
            action = "archived" if archived else "unarchived"
            logger.info(
                "issue_status_changed",
                issue_id=issue_id,
                action=action,
            )

        return updated
