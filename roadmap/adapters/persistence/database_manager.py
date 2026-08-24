"""Database infrastructure manager for SQLite persistence layer.

This module handles database connection, initialization, and migrations.
It separates database infrastructure concerns from the state management layer.
"""

import sqlite3
import threading
import weakref
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

from roadmap.common.logging import get_logger

logger = get_logger(__name__)


def _close_connections(
    connections: set[sqlite3.Connection], lock: threading.RLock
) -> None:
    """Close a manager-owned connection registry without retaining its manager."""
    with lock:
        while connections:
            connections.pop().close()


class DatabaseError(Exception):
    """Base exception for database operations."""


class DatabaseManager:
    """Manages SQLite database connections, initialization, and migrations."""

    def __init__(self, db_path: str | Path | None = None):
        """Initialize the database manager.

        Args:
            db_path: Path to SQLite database file. Defaults to ~/.roadmap/roadmap.db
        """
        if db_path is None:
            db_path = Path.home() / ".roadmap" / "roadmap.db"

        self.db_path = Path(db_path)
        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            logger.error(
                "database_directory_create_failed",
                db_path=str(self.db_path),
                error=str(e),
                error_type=type(e).__name__,
                severity="system_error",
            )
            raise DatabaseError(
                f"Failed to create database directory for {self.db_path}: {e}"
            ) from e

        # Thread-local storage for connections
        self._local = threading.local()
        self._connections: set[sqlite3.Connection] = set()
        self._connections_lock = threading.RLock()
        self._connection_finalizer = weakref.finalize(
            self,
            _close_connections,
            self._connections,
            self._connections_lock,
        )

        logger.info("Initializing database manager", db_path=str(self.db_path))
        try:
            self._init_database()
        except sqlite3.Error as e:
            logger.error(
                "database_schema_init_failed",
                db_path=str(self.db_path),
                error=str(e),
                error_type=type(e).__name__,
                severity="system_error",
            )
            raise DatabaseError(
                f"Failed to initialize database schema at {self.db_path}: {e}"
            ) from e

    def validate_read_write(self) -> None:
        """Validate that the database is readable and writable."""
        conn = self._get_connection()
        try:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS db_health_check (
                    id INTEGER PRIMARY KEY,
                    checked_at TIMESTAMP
                )
                """
            )
            conn.execute(
                "INSERT INTO db_health_check (checked_at) VALUES (?)",
                (datetime.now(UTC).isoformat(),),
            )
            row_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            conn.execute("DELETE FROM db_health_check WHERE id = ?", (row_id,))
        except sqlite3.Error as e:
            logger.error(
                "database_read_write_failed",
                db_path=str(self.db_path),
                error=str(e),
                error_type=type(e).__name__,
                severity="system_error",
            )
            raise DatabaseError(
                f"Database read/write check failed for {self.db_path}: {e}"
            ) from e

    def _get_connection(self) -> sqlite3.Connection:
        """Get thread-local database connection."""
        connection = getattr(self._local, "connection", None)
        with self._connections_lock:
            if connection in self._connections or (
                connection is not None
                and not isinstance(connection, sqlite3.Connection)
            ):
                return connection

            connection = sqlite3.connect(
                str(self.db_path),
                check_same_thread=False,
                timeout=30.0,
                isolation_level=None,  # Autocommit mode
            )
            try:
                sqlite3.register_adapter(datetime, lambda dt: dt.isoformat())
                sqlite3.register_converter(
                    "TIMESTAMP", lambda val: datetime.fromisoformat(val.decode())
                )
                connection.execute("PRAGMA foreign_keys = ON")
                connection.execute("PRAGMA journal_mode = WAL")
                connection.execute("PRAGMA synchronous = NORMAL")
                connection.row_factory = sqlite3.Row
            except Exception:
                connection.close()
                raise
            self._connections.add(connection)
            self._local.connection = connection

        return connection

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
                logger.debug(
                    "rollback_failed_transaction_not_active", severity="operational"
                )
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
            archived BOOLEAN DEFAULT 0,
            archived_at TIMESTAMP NULL,
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
            archived BOOLEAN DEFAULT 0,
            archived_at TIMESTAMP NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            metadata TEXT,  -- JSON for additional data
            FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE
        );

        -- Issues table
        CREATE TABLE IF NOT EXISTS issues (
            id TEXT PRIMARY KEY,
            project_id TEXT,
            milestone_id TEXT,
            title TEXT NOT NULL,
            headline TEXT DEFAULT '',  -- Short summary for list views
            description TEXT,  -- Full markdown content
            status TEXT NOT NULL DEFAULT 'open',
            priority TEXT NOT NULL DEFAULT 'medium',
            issue_type TEXT NOT NULL DEFAULT 'task',
            assignee TEXT,
            estimate_hours REAL,
            archived BOOLEAN DEFAULT 0,
            archived_at TIMESTAMP NULL,
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

        # Run migrations
        self._run_migrations()

    def _migration_archive_columns(self, cursor) -> list[str]:
        """Migration 1: add archived/archived_at to projects, milestones, issues."""
        result = []
        for table in ("projects", "milestones", "issues"):
            cursor.execute(f"PRAGMA table_info({table})")  # noqa: S608
            columns = {col[1] for col in cursor.fetchall()}
            if "archived" not in columns:
                result.append(
                    f"ALTER TABLE {table} ADD COLUMN archived INTEGER DEFAULT 0;"
                )
            if "archived_at" not in columns:
                result.append(
                    f"ALTER TABLE {table} ADD COLUMN archived_at TIMESTAMP NULL;"
                )
        return result

    def _migration_headline_column(self, cursor) -> list[str]:
        """Migration 4: add headline column to issues table."""
        cursor.execute("PRAGMA table_info(issues)")
        issue_columns = (
            [row[1] for row in cursor.fetchall()] if cursor.fetchone() else []
        )
        if "headline" in issue_columns:
            return []
        return ["ALTER TABLE issues ADD COLUMN headline TEXT DEFAULT '';"]

    @staticmethod
    def _migration_remove_provider_state() -> list[str]:
        """Delete obsolete provider and cache protocol tables from legacy databases."""
        return [
            "DROP TABLE IF EXISTS issue_remote_links;",
            "DROP TABLE IF EXISTS sync_metrics;",
            "DROP TABLE IF EXISTS sync_base_state;",
            "DROP TABLE IF EXISTS sync_metadata;",
            "DROP TABLE IF EXISTS file_sync_state;",
        ]

    def _run_migrations(self):
        """Run database migrations for schema updates."""
        conn = self._get_connection()
        cursor = conn.cursor()

        migrations = (
            self._migration_archive_columns(cursor)
            + self._migration_headline_column(cursor)
            + self._migration_remove_provider_state()
        )

        for migration_sql in migrations:
            try:
                conn.executescript(migration_sql)
                logger.info("applied_database_migration")
            except Exception as e:
                logger.warning(
                    "migration_may_have_been_applied",
                    error=str(e),
                    severity="operational",
                )

        conn.commit()

    def is_initialized(self) -> bool:
        """Check if database is properly initialized."""
        try:
            conn = self._get_connection()
            result = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='projects'"
            ).fetchone()
            return result is not None
        except Exception as e:
            logger.error(
                "Failed to check database initialization",
                error=str(e),
                severity="infrastructure",
            )
            return False

    def close(self):
        """Close every connection created by this manager, from any thread."""
        connections = getattr(self, "_connections", None)
        lock = getattr(self, "_connections_lock", None)
        if connections is not None and lock is not None:
            _close_connections(connections, lock)
        local = getattr(self, "_local", None)
        if local is not None and hasattr(local, "connection"):
            delattr(local, "connection")

    def vacuum(self):
        """Optimize database."""
        conn = self._get_connection()
        conn.execute("VACUUM")
        logger.info("Database vacuumed")

    def database_exists(self) -> bool:
        """Check if database file exists and has tables."""
        if not self.db_path.exists():
            return False

        try:
            conn = self._get_connection()
            # Check if our main tables exist
            tables = conn.execute("""
                SELECT name FROM sqlite_master
                WHERE type='table' AND name IN ('issues', 'milestones', 'projects')
            """).fetchall()

            # We should have at least our core tables
            return len(tables) >= 3

        except Exception as e:
            logger.warning(
                "Error checking database existence",
                error=str(e),
                severity="infrastructure",
            )
            return False

    def is_safe_for_writes(self) -> tuple[bool, str]:
        """Check if database is safe for write operations."""
        try:
            # Check database integrity
            conn = self._get_connection()
            try:
                conn.execute("PRAGMA integrity_check").fetchone()
            except sqlite3.DatabaseError as e:
                return False, f"Database corruption detected: {e}"

            return True, "Database ready for operations"

        except Exception as e:
            return False, f"Safety check failed: {e}"
