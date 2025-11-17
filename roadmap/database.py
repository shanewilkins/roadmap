"""SQLite-based state management for roadmap CLI application.

This module provides a persistent state management layer using SQLite,
replacing the file-based approach with a proper database backend for
better performance and data integrity.
"""

import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from .logging import get_logger

logger = get_logger(__name__)


class DatabaseError(Exception):
    """Base exception for database operations."""

    pass


class StateManager:
    """SQLite-based state manager for roadmap data."""

    def __init__(self, db_path: str | Path | None = None):
        """Initialize the state manager.

        Args:
            db_path: Path to SQLite database file. Defaults to ~/.roadmap/roadmap.db
        """
        if db_path is None:
            db_path = Path.home() / ".roadmap" / "roadmap.db"

        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Thread-local storage for connections
        self._local = threading.local()

        logger.info("Initializing state manager", db_path=str(self.db_path))
        self._init_database()

    def _get_connection(self) -> sqlite3.Connection:
        """Get thread-local database connection."""
        if not hasattr(self._local, "connection"):
            self._local.connection = sqlite3.connect(
                str(self.db_path),
                check_same_thread=False,
                timeout=30.0,
                isolation_level=None,  # Autocommit mode
            )
            # Enable foreign keys and WAL mode for better performance
            self._local.connection.execute("PRAGMA foreign_keys = ON")
            self._local.connection.execute("PRAGMA journal_mode = WAL")
            self._local.connection.execute("PRAGMA synchronous = NORMAL")
            self._local.connection.row_factory = sqlite3.Row

        return self._local.connection

    @contextmanager
    def transaction(self):
        """Context manager for database transactions."""
        conn = self._get_connection()
        try:
            conn.execute("BEGIN IMMEDIATE")
            yield conn
            conn.execute("COMMIT")
        except Exception:
            try:
                conn.execute("ROLLBACK")
            except sqlite3.OperationalError:
                # Transaction might not be active
                pass
            raise

    def _init_database(self):
        """Initialize database schema."""
        schema_sql = """
        -- Projects table
        CREATE TABLE IF NOT EXISTS projects (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            status TEXT NOT NULL DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            metadata TEXT  -- JSON for additional data
        );

        -- Milestones table
        CREATE TABLE IF NOT EXISTS milestones (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            status TEXT NOT NULL DEFAULT 'open',
            due_date DATE,
            progress_percentage REAL DEFAULT 0.0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            metadata TEXT,  -- JSON for additional data
            FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE
        );

        -- Issues table
        CREATE TABLE IF NOT EXISTS issues (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            milestone_id TEXT,
            title TEXT NOT NULL,
            description TEXT,
            status TEXT NOT NULL DEFAULT 'open',
            priority TEXT NOT NULL DEFAULT 'medium',
            issue_type TEXT NOT NULL DEFAULT 'task',
            assignee TEXT,
            estimate_hours REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            due_date DATE,
            metadata TEXT,  -- JSON for additional data
            FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE,
            FOREIGN KEY (milestone_id) REFERENCES milestones (id) ON DELETE SET NULL
        );

        -- Issue dependencies table
        CREATE TABLE IF NOT EXISTS issue_dependencies (
            issue_id TEXT NOT NULL,
            depends_on_id TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (issue_id, depends_on_id),
            FOREIGN KEY (issue_id) REFERENCES issues (id) ON DELETE CASCADE,
            FOREIGN KEY (depends_on_id) REFERENCES issues (id) ON DELETE CASCADE
        );

        -- Issue labels table (many-to-many)
        CREATE TABLE IF NOT EXISTS issue_labels (
            issue_id TEXT NOT NULL,
            label TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (issue_id, label),
            FOREIGN KEY (issue_id) REFERENCES issues (id) ON DELETE CASCADE
        );

        -- Comments table
        CREATE TABLE IF NOT EXISTS comments (
            id TEXT PRIMARY KEY,
            issue_id TEXT NOT NULL,
            author TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            metadata TEXT,  -- JSON for additional data
            FOREIGN KEY (issue_id) REFERENCES issues (id) ON DELETE CASCADE
        );

        -- Git sync state table
        CREATE TABLE IF NOT EXISTS sync_state (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Indexes for performance
        CREATE INDEX IF NOT EXISTS idx_milestones_project_id ON milestones (project_id);
        CREATE INDEX IF NOT EXISTS idx_issues_project_id ON issues (project_id);
        CREATE INDEX IF NOT EXISTS idx_issues_milestone_id ON issues (milestone_id);
        CREATE INDEX IF NOT EXISTS idx_issues_assignee ON issues (assignee);
        CREATE INDEX IF NOT EXISTS idx_issues_status ON issues (status);
        CREATE INDEX IF NOT EXISTS idx_comments_issue_id ON comments (issue_id);

        -- Triggers for updated_at timestamps
        CREATE TRIGGER IF NOT EXISTS update_projects_timestamp
        AFTER UPDATE ON projects
        BEGIN
            UPDATE projects SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
        END;

        CREATE TRIGGER IF NOT EXISTS update_milestones_timestamp
        AFTER UPDATE ON milestones
        BEGIN
            UPDATE milestones SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
        END;

        CREATE TRIGGER IF NOT EXISTS update_issues_timestamp
        AFTER UPDATE ON issues
        BEGIN
            UPDATE issues SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
        END;

        CREATE TRIGGER IF NOT EXISTS update_comments_timestamp
        AFTER UPDATE ON comments
        BEGIN
            UPDATE comments SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
        END;
        """

        conn = self._get_connection()
        conn.executescript(schema_sql)

        logger.info("Database schema initialized")

    def is_initialized(self) -> bool:
        """Check if database is properly initialized."""
        try:
            conn = self._get_connection()
            result = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='projects'"
            ).fetchone()
            return result is not None
        except Exception as e:
            logger.error("Failed to check database initialization", error=str(e))
            return False

    # Project operations
    def create_project(self, project_data: dict[str, Any]) -> str:
        """Create a new project."""
        with self.transaction() as conn:
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

    def get_project(self, project_id: str) -> dict[str, Any] | None:
        """Get project by ID."""
        conn = self._get_connection()
        row = conn.execute(
            "SELECT * FROM projects WHERE id = ?", (project_id,)
        ).fetchone()

        return dict(row) if row else None

    def list_projects(self) -> list[dict[str, Any]]:
        """List all projects."""
        conn = self._get_connection()
        rows = conn.execute(
            "SELECT * FROM projects ORDER BY created_at DESC"
        ).fetchall()
        return [dict(row) for row in rows]

    def update_project(self, project_id: str, updates: dict[str, Any]) -> bool:
        """Update project."""
        if not updates:
            return False

        set_clause = ", ".join(f"{key} = ?" for key in updates.keys())
        values = list(updates.values()) + [project_id]

        with self.transaction() as conn:
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

    def delete_project(self, project_id: str) -> bool:
        """Delete project and all related data."""
        with self.transaction() as conn:
            cursor = conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))

        deleted = cursor.rowcount > 0
        if deleted:
            logger.info("Deleted project", project_id=project_id)

        return deleted

    # Similar methods would be implemented for milestones, issues, etc.
    # For brevity, I'll add the key ones:

    def get_sync_state(self, key: str) -> str | None:
        """Get sync state value."""
        conn = self._get_connection()
        row = conn.execute(
            "SELECT value FROM sync_state WHERE key = ?", (key,)
        ).fetchone()
        return row["value"] if row else None

    def set_sync_state(self, key: str, value: str):
        """Set sync state value."""
        with self.transaction() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO sync_state (key, value) VALUES (?, ?)
            """,
                (key, value),
            )

    def close(self):
        """Close database connections."""
        if hasattr(self._local, "connection"):
            self._local.connection.close()
            delattr(self._local, "connection")

    def vacuum(self):
        """Optimize database."""
        conn = self._get_connection()
        conn.execute("VACUUM")
        logger.info("Database vacuumed")


# Global state manager instance
_state_manager: StateManager | None = None


def get_state_manager(db_path: str | Path | None = None) -> StateManager:
    """Get the global state manager instance."""
    global _state_manager

    if _state_manager is None:
        _state_manager = StateManager(db_path)

    return _state_manager


def initialize_state_manager(db_path: str | Path | None = None) -> StateManager:
    """Initialize the global state manager."""
    global _state_manager
    _state_manager = StateManager(db_path)
    return _state_manager
