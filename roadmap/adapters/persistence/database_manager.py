"""Database infrastructure manager for SQLite persistence layer.

This module handles database connection, initialization, and migrations.
It separates database infrastructure concerns from the state management layer.
"""

import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from roadmap.common.logging import get_logger

logger = get_logger(__name__)


class DatabaseError(Exception):
    """Base exception for database operations."""

    pass


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
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Thread-local storage for connections
        self._local = threading.local()

        logger.info("Initializing database manager", db_path=str(self.db_path))
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
            # Register datetime adapter for Python 3.12+
            sqlite3.register_adapter(datetime, lambda dt: dt.isoformat())
            sqlite3.register_converter(
                "TIMESTAMP", lambda val: datetime.fromisoformat(val.decode())
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

        -- Sync base state (three-way merge baseline from last successful sync)
        -- Note: issue_id does NOT have a foreign key constraint because sync baseline
        -- can be saved before issues are persisted to the database (during sync operations)
        CREATE TABLE IF NOT EXISTS sync_base_state (
            issue_id TEXT PRIMARY KEY,
            status TEXT NOT NULL,
            assignee TEXT,
            milestone TEXT,
            description TEXT,
            labels TEXT,  -- JSON array of label strings
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Sync metadata (overall sync state)
        CREATE TABLE IF NOT EXISTS sync_metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- File synchronization tracking
        CREATE TABLE IF NOT EXISTS file_sync_state (
            file_path TEXT PRIMARY KEY,
            content_hash TEXT NOT NULL,
            file_size INTEGER,
            last_modified TIMESTAMP,
            last_synced TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Indexes for performance
        CREATE INDEX IF NOT EXISTS idx_sync_base_state_synced_at ON sync_base_state (synced_at);
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

    def _run_migrations(self):
        """Run database migrations for schema updates."""
        conn = self._get_connection()
        cursor = conn.cursor()

        # Get current schema version (use pragma to check if columns exist)
        migrations = []

        # Migration 1: Add archive columns
        cursor.execute("PRAGMA table_info(projects)")
        project_columns = [col[1] for col in cursor.fetchall()]
        if "archived" not in project_columns:
            migrations.append("""
                ALTER TABLE projects ADD COLUMN archived INTEGER DEFAULT 0;
                ALTER TABLE projects ADD COLUMN archived_at TIMESTAMP NULL;
            """)

        cursor.execute("PRAGMA table_info(milestones)")
        milestone_columns = [col[1] for col in cursor.fetchall()]
        if "archived" not in milestone_columns:
            migrations.append("""
                ALTER TABLE milestones ADD COLUMN archived INTEGER DEFAULT 0;
                ALTER TABLE milestones ADD COLUMN archived_at TIMESTAMP NULL;
            """)

        cursor.execute("PRAGMA table_info(issues)")
        issue_columns = [col[1] for col in cursor.fetchall()]
        if "archived" not in issue_columns:
            migrations.append("""
                ALTER TABLE issues ADD COLUMN archived INTEGER DEFAULT 0;
                ALTER TABLE issues ADD COLUMN archived_at TIMESTAMP NULL;
            """)

        # Migration 2: Create sync_base_state table if it doesn't exist
        # Note: issue_id does NOT have a foreign key constraint because sync baseline
        # can be saved before issues are persisted to the database (during sync operations)
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='sync_base_state'"
        )
        if not cursor.fetchone():
            migrations.append("""
                CREATE TABLE sync_base_state (
                    issue_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    assignee TEXT,
                    milestone TEXT,
                    description TEXT,
                    labels TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX idx_sync_base_state_synced_at ON sync_base_state (synced_at);
            """)

        # Migration 3: Create issue_remote_links table for tracking remote backend IDs
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='issue_remote_links'"
        )
        if not cursor.fetchone():
            migrations.append("""
                CREATE TABLE issue_remote_links (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    issue_uuid TEXT NOT NULL,
                    backend_name TEXT NOT NULL,
                    remote_id TEXT NOT NULL,
                    linked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(issue_uuid, backend_name),
                    FOREIGN KEY (issue_uuid) REFERENCES issues (id) ON DELETE CASCADE
                );
                CREATE INDEX idx_issue_remote_links_backend ON issue_remote_links (backend_name);
                CREATE INDEX idx_issue_remote_links_issue_uuid ON issue_remote_links (issue_uuid);
            """)

        # Migration 4: Add headline column to issues table
        cursor.execute("PRAGMA table_info(issues)")
        issue_columns = (
            [row[1] for row in cursor.fetchall()] if cursor.fetchone() else []
        )
        if "headline" not in issue_columns:
            migrations.append("""
                ALTER TABLE issues ADD COLUMN headline TEXT DEFAULT '';
            """)

        # Migration 5: Add headline and content columns to sync_base_state
        cursor.execute("PRAGMA table_info(sync_base_state)")
        columns = [row[1] for row in cursor.fetchall()] if cursor.fetchone() else []
        if "headline" not in columns and "content" not in columns:
            migrations.append("""
                ALTER TABLE sync_base_state ADD COLUMN headline TEXT DEFAULT '';
                ALTER TABLE sync_base_state ADD COLUMN content TEXT DEFAULT '';
            """)

        # Migration 6: Create sync_metrics table for storing sync operation metrics
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='sync_metrics'"
        )
        if not cursor.fetchone():
            migrations.append("""
                CREATE TABLE sync_metrics (
                    id TEXT PRIMARY KEY,
                    operation_id TEXT NOT NULL UNIQUE,
                    backend_type TEXT NOT NULL,
                    duration_seconds REAL NOT NULL DEFAULT 0.0,
                    metrics_json TEXT NOT NULL,  -- Full SyncMetrics.to_dict() as JSON
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS idx_sync_metrics_backend_type ON sync_metrics (backend_type);
                CREATE INDEX IF NOT EXISTS idx_sync_metrics_created_at ON sync_metrics (created_at);
                CREATE INDEX IF NOT EXISTS idx_sync_metrics_operation_id ON sync_metrics (operation_id);
            """)

        # Execute migrations
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
        """Close database connections."""
        if hasattr(self._local, "connection"):
            self._local.connection.close()
            delattr(self._local, "connection")

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
