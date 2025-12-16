"""Repository for project persistence operations."""

from typing import Any

from roadmap.common.errors import OperationType, safe_operation
from roadmap.common.logging import get_logger

logger = get_logger(__name__)


class ProjectRepository:
    """Handles all project-related database operations."""

    def __init__(self, get_connection, transaction):
        """Initialize repository with database connection methods.

        Args:
            get_connection: Callable that returns sqlite3 Connection
            transaction: Context manager for database transactions
        """
        self._get_connection = get_connection
        self._transaction = transaction

    @safe_operation(OperationType.CREATE, "Project", include_traceback=True)
    @safe_operation(OperationType.CREATE, "Project", include_traceback=True)
    def create(self, project_data: dict[str, Any]) -> str:
        """Create a new project.

        Args:
            project_data: Dictionary with project fields

        Returns:
            Project ID
        """
        with self._transaction() as conn:
            conn.execute(
                """
                INSERT INTO projects (id, name, description, status, metadata)
                VALUES (?, ?, ?, ?, ?)
            """,
                (
                    project_data["id"],
                    project_data["name"],
                    project_data.get("description"),
                    project_data.get("status", "active"),
                    project_data.get("metadata"),
                ),
            )

        logger.info("Created project", project_id=project_data["id"])
        return project_data["id"]

    def get(self, project_id: str) -> dict[str, Any] | None:
        """Get project by ID.

        Args:
            project_id: Project identifier

        Returns:
            Project data or None if not found
        """
        conn = self._get_connection()
        row = conn.execute(
            "SELECT * FROM projects WHERE id = ?", (project_id,)
        ).fetchone()

        return dict(row) if row else None

    def list_all(self) -> list[dict[str, Any]]:
        """List all projects.

        Returns:
            List of project data dictionaries
        """
        conn = self._get_connection()
        rows = conn.execute(
            "SELECT * FROM projects ORDER BY created_at DESC"
        ).fetchall()
        return [dict(row) for row in rows]

    @safe_operation(OperationType.UPDATE, "Project")
    @safe_operation(OperationType.UPDATE, "Project")
    def update(self, project_id: str, updates: dict[str, Any]) -> bool:
        """Update project.

        Args:
            project_id: Project identifier
            updates: Dictionary of fields to update

        Returns:
            True if successful, False otherwise
        """
        if not updates:
            return False

        set_clause = ", ".join(f"{key} = ?" for key in updates.keys())
        values = list(updates.values()) + [project_id]

        with self._transaction() as conn:
            cursor = conn.execute(
                f"""
                UPDATE projects SET {set_clause} WHERE id = ?
            """,
                values,
            )

        updated = cursor.rowcount > 0
        if updated:
            logger.info(
                "Updated project", project_id=project_id, updates=list(updates.keys())
            )

        return updated

    @safe_operation(OperationType.DELETE, "Project", include_traceback=True)
    @safe_operation(OperationType.DELETE, "Project", include_traceback=True)
    def delete(self, project_id: str) -> bool:
        """Delete project and all related data.

        Args:
            project_id: Project identifier

        Returns:
            True if successful, False otherwise
        """
        with self._transaction() as conn:
            cursor = conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))

        deleted = cursor.rowcount > 0
        if deleted:
            logger.info("Deleted project", project_id=project_id)

        return deleted

    @safe_operation(OperationType.UPDATE, "Project")
    @safe_operation(OperationType.UPDATE, "Project")
    def mark_archived(self, project_id: str, archived: bool = True) -> bool:
        """Mark a project as archived or unarchived.

        Args:
            project_id: Project identifier
            archived: True to archive, False to unarchive

        Returns:
            True if successful, False otherwise
        """
        with self._transaction() as conn:
            if archived:
                cursor = conn.execute(
                    "UPDATE projects SET archived = 1, archived_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (project_id,),
                )
            else:
                cursor = conn.execute(
                    "UPDATE projects SET archived = 0, archived_at = NULL WHERE id = ?",
                    (project_id,),
                )

        updated = cursor.rowcount > 0
        if updated:
            action = "archived" if archived else "unarchived"
            logger.info(f"Project {action}", project_id=project_id)

        return updated
