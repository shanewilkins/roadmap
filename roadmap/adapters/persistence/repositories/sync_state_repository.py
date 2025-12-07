"""Repository for sync state persistence operations."""

from roadmap.common.logging import get_logger

logger = get_logger(__name__)


class SyncStateRepository:
    """Handles all sync state database operations."""

    def __init__(self, get_connection, transaction):
        """Initialize repository with database connection methods.

        Args:
            get_connection: Callable that returns sqlite3 Connection
            transaction: Context manager for database transactions
        """
        self._get_connection = get_connection
        self._transaction = transaction

    def get(self, key: str) -> str | None:
        """Get sync state value by key.

        Args:
            key: State key

        Returns:
            State value or None if not found
        """
        conn = self._get_connection()
        row = conn.execute(
            "SELECT value FROM sync_state WHERE key = ?", (key,)
        ).fetchone()
        return row["value"] if row else None

    def set(self, key: str, value: str) -> None:
        """Set sync state value.

        Args:
            key: State key
            value: State value
        """
        with self._transaction() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO sync_state (key, value) VALUES (?, ?)
            """,
                (key, value),
            )
        logger.debug("Set sync state", key=key)

    def delete(self, key: str) -> None:
        """Delete sync state value.

        Args:
            key: State key
        """
        with self._transaction() as conn:
            conn.execute("DELETE FROM sync_state WHERE key = ?", (key,))
        logger.debug("Deleted sync state", key=key)

    def clear_all(self) -> None:
        """Clear all sync state values."""
        with self._transaction() as conn:
            conn.execute("DELETE FROM sync_state")
        logger.info("Cleared all sync state")
