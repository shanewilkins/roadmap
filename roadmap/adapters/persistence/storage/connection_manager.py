"""Connection management for database operations."""

import sqlite3
from contextlib import contextmanager

from roadmap.common.logging import get_logger

from ..database_manager import DatabaseManager

logger = get_logger(__name__)


class ConnectionManager:
    """Manages database connections and transactions."""

    def __init__(self, db_manager: DatabaseManager):
        """Initialize connection manager.

        Args:
            db_manager: DatabaseManager instance handling connection pooling
        """
        self._db_manager = db_manager
        logger.debug("ConnectionManager initialized")

    def get_connection(self) -> sqlite3.Connection:
        """Get thread-local database connection.

        Returns:
            sqlite3.Connection: Active database connection
        """
        return self._db_manager._get_connection()

    @contextmanager
    def transaction(self):
        """Context manager for database transactions.

        Yields:
            Connection context with automatic commit/rollback on exception
        """
        with self._db_manager.transaction() as conn:
            yield conn

    def close(self):
        """Close all database connections."""
        logger.debug("Closing database connections")
        self._db_manager.close()

    def vacuum(self):
        """Optimize database by vacuuming."""
        logger.debug("Running database vacuum")
        self._db_manager.vacuum()

    def is_initialized(self) -> bool:
        """Check if database is properly initialized.

        Returns:
            bool: True if database exists and is initialized
        """
        result = self._db_manager.is_initialized()
        logger.debug("Database initialization check", initialized=result)
        return result

    def database_exists(self) -> bool:
        """Check if database file exists and has tables.

        Returns:
            bool: True if database exists with tables
        """
        result = self._db_manager.database_exists()
        logger.debug("Database existence check", exists=result)
        return result

    def is_safe_for_writes(self) -> tuple[bool, str]:
        """Check if database is safe for write operations.

        Returns:
            tuple[bool, str]: (safe, message) indicating if writes are safe
        """
        return self._db_manager.is_safe_for_writes()
