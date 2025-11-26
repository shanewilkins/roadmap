"""SQLite-based state management for roadmap CLI application.

This module provides a persistent state management layer using SQLite,
replacing the file-based approach with a proper database backend for
better performance and data integrity.
"""

import hashlib
import json
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from ..shared.logging import get_logger

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

        -- File synchronization tracking
        CREATE TABLE IF NOT EXISTS file_sync_state (
            file_path TEXT PRIMARY KEY,
            content_hash TEXT NOT NULL,
            file_size INTEGER,
            last_modified TIMESTAMP,
            last_synced TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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

        # Execute migrations
        for migration_sql in migrations:
            try:
                conn.executescript(migration_sql)
                logger.info("Applied database migration")
            except Exception as e:
                logger.warning(f"Migration may have already been applied: {e}")

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

    def mark_project_archived(self, project_id: str, archived: bool = True) -> bool:
        """Mark a project as archived or unarchived.

        Args:
            project_id: Project identifier
            archived: True to archive, False to unarchive

        Returns:
            True if successful, False otherwise
        """
        with self.transaction() as conn:
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

    def mark_milestone_archived(self, milestone_id: str, archived: bool = True) -> bool:
        """Mark a milestone as archived or unarchived."""
        with self.transaction() as conn:
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
            logger.info(f"Milestone {action}", milestone_id=milestone_id)

        return updated

    def mark_issue_archived(self, issue_id: str, archived: bool = True) -> bool:
        """Mark an issue as archived or unarchived."""
        with self.transaction() as conn:
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
            logger.info(f"Issue {action}", issue_id=issue_id)

        return updated

    # Milestone operations
    def create_milestone(self, milestone_data: dict[str, Any]) -> str:
        """Create a new milestone."""
        with self.transaction() as conn:
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

    def get_milestone(self, milestone_id: str) -> dict[str, Any] | None:
        """Get milestone by ID."""
        conn = self._get_connection()
        row = conn.execute(
            "SELECT * FROM milestones WHERE id = ?", (milestone_id,)
        ).fetchone()

        return dict(row) if row else None

    def update_milestone(self, milestone_id: str, updates: dict[str, Any]) -> bool:
        """Update milestone."""
        if not updates:
            return False

        set_clause = ", ".join(f"{key} = ?" for key in updates.keys())
        values = list(updates.values()) + [milestone_id]

        with self.transaction() as conn:
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

    # Issue operations
    def create_issue(self, issue_data: dict[str, Any]) -> str:
        """Create a new issue."""
        with self.transaction() as conn:
            conn.execute(
                """
                INSERT INTO issues (id, project_id, milestone_id, title, description, status, priority, issue_type, assignee, estimate_hours, due_date, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    issue_data["id"],
                    issue_data.get("project_id"),
                    issue_data.get("milestone_id"),
                    issue_data.get("title"),
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

    def get_issue(self, issue_id: str) -> dict[str, Any] | None:
        """Get issue by ID."""
        conn = self._get_connection()
        row = conn.execute("SELECT * FROM issues WHERE id = ?", (issue_id,)).fetchone()

        return dict(row) if row else None

    def update_issue(self, issue_id: str, updates: dict[str, Any]) -> bool:
        """Update issue."""
        if not updates:
            return False

        set_clause = ", ".join(f"{key} = ?" for key in updates.keys())
        values = list(updates.values()) + [issue_id]

        with self.transaction() as conn:
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

    def delete_issue(self, issue_id: str) -> bool:
        """Delete issue."""
        with self.transaction() as conn:
            cursor = conn.execute("DELETE FROM issues WHERE id = ?", (issue_id,))

        deleted = cursor.rowcount > 0
        if deleted:
            logger.info("Deleted issue", issue_id=issue_id)

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

    # YAML parsing and file synchronization methods

    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA-256 hash of file content."""
        try:
            with open(file_path, "rb") as f:
                return hashlib.sha256(f.read()).hexdigest()
        except Exception as e:
            logger.warning(f"Failed to calculate hash for {file_path}", error=str(e))
            return ""

    def _parse_yaml_frontmatter(self, file_path: Path) -> dict[str, Any]:
        """Parse YAML frontmatter from markdown file."""
        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            # Check for frontmatter delimiters
            if not content.startswith("---\n"):
                return {}

            # Find the end of frontmatter
            try:
                end_marker = content.index("\n---\n", 4)
                frontmatter = content[4:end_marker]
                return yaml.safe_load(frontmatter) or {}
            except ValueError:
                # No end marker found, treat entire file as YAML
                return yaml.safe_load(content) or {}

        except Exception as e:
            logger.error(f"Failed to parse YAML from {file_path}", error=str(e))
            return {}

    def get_file_sync_status(self, file_path: str) -> dict[str, Any] | None:
        """Get sync status for a file."""
        conn = self._get_connection()
        row = conn.execute(
            """
            SELECT file_path, content_hash, file_size, last_modified, last_synced
            FROM file_sync_state WHERE file_path = ?
        """,
            (file_path,),
        ).fetchone()

        return dict(row) if row else None

    def update_file_sync_status(
        self, file_path: str, content_hash: str, file_size: int, last_modified: datetime
    ):
        """Update sync status for a file."""
        with self.transaction() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO file_sync_state
                (file_path, content_hash, file_size, last_modified)
                VALUES (?, ?, ?, ?)
            """,
                (file_path, content_hash, file_size, last_modified),
            )

    def has_file_changed(self, file_path: Path) -> bool:
        """Check if file has changed since last sync."""
        try:
            if not file_path.exists():
                return True

            current_hash = self._calculate_file_hash(file_path)
            sync_status = self.get_file_sync_status(str(file_path))

            if not sync_status:
                return True  # Never synced

            return current_hash != sync_status["content_hash"]

        except Exception as e:
            logger.error(f"Failed to check file changes for {file_path}", error=str(e))
            return True  # Assume changed on error

    def sync_issue_file(self, file_path: Path) -> bool:
        """Sync a single issue file to database."""
        try:
            if not file_path.exists():
                logger.warning(f"Issue file not found: {file_path}")
                return False

            # Parse YAML frontmatter
            issue_data = self._parse_yaml_frontmatter(file_path)
            if not issue_data:
                logger.warning(f"No YAML data found in {file_path}")
                return False

            # Extract issue ID from filename or YAML
            issue_id = issue_data.get("id")
            if not issue_id:
                # Try to extract from filename (e.g., issue-abc123.md -> abc123)
                stem = file_path.stem
                if stem.startswith("issue-"):
                    issue_id = stem[6:]  # Remove 'issue-' prefix
                else:
                    issue_id = stem
                issue_data["id"] = issue_id

            # Handle missing project_id by assigning to first available project
            project_id = issue_data.get("project_id")
            if not project_id:
                project_id = self._get_default_project_id()
                if not project_id:
                    logger.warning(f"No projects found for issue {issue_id}, skipping")
                    return False

            # Handle milestone field (could be name or ID)
            milestone_id = issue_data.get("milestone_id")
            if not milestone_id and "milestone" in issue_data:
                # Convert milestone name to ID
                milestone_name = issue_data["milestone"]
                milestone_id = self._get_milestone_id_by_name(milestone_name)
                issue_data["milestone_id"] = milestone_id

            # Ensure required fields exist
            required_fields = {
                "title": issue_data.get("title", "Untitled"),
                "status": issue_data.get("status", "open"),
                "priority": issue_data.get("priority", "medium"),
                "issue_type": issue_data.get("type", "task"),
                "project_id": project_id,
            }

            for field, default_value in required_fields.items():
                if field not in issue_data:
                    issue_data[field] = default_value

            # Convert dates
            if "due_date" in issue_data and issue_data["due_date"]:
                try:
                    if isinstance(issue_data["due_date"], str):
                        issue_data["due_date"] = datetime.fromisoformat(
                            issue_data["due_date"]
                        ).date()
                except ValueError:
                    issue_data["due_date"] = None

            # Store metadata as JSON
            metadata = {
                k: v
                for k, v in issue_data.items()
                if k
                not in [
                    "id",
                    "title",
                    "description",
                    "status",
                    "priority",
                    "issue_type",
                    "assignee",
                    "estimate_hours",
                    "due_date",
                    "project_id",
                    "milestone_id",
                ]
            }
            issue_data["metadata"] = json.dumps(metadata) if metadata else None

            # Upsert issue
            with self.transaction() as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO issues
                    (id, project_id, milestone_id, title, description, status,
                     priority, issue_type, assignee, estimate_hours, due_date, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        issue_data["id"],
                        issue_data["project_id"],
                        issue_data.get("milestone_id"),
                        issue_data["title"],
                        issue_data.get("description"),
                        issue_data["status"],
                        issue_data["priority"],
                        issue_data["issue_type"],
                        issue_data.get("assignee"),
                        issue_data.get("estimate_hours"),
                        issue_data.get("due_date"),
                        issue_data["metadata"],
                    ),
                )

            # Update sync status
            file_stat = file_path.stat()
            content_hash = self._calculate_file_hash(file_path)
            self.update_file_sync_status(
                str(file_path),
                content_hash,
                file_stat.st_size,
                datetime.fromtimestamp(file_stat.st_mtime),
            )

            logger.info(f"Synced issue file: {issue_id}", file_path=str(file_path))
            return True

        except Exception as e:
            logger.error(f"Failed to sync issue file {file_path}", error=str(e))
            return False

    def _get_default_project_id(self) -> str | None:
        """Get the first available project ID for orphaned milestones/issues."""
        try:
            with self.transaction() as conn:
                result = conn.execute("SELECT id FROM projects LIMIT 1").fetchone()
                return result[0] if result else None
        except Exception as e:
            logger.error("Failed to get default project ID", error=str(e))
            return None

    def _get_milestone_id_by_name(self, milestone_name: str) -> str | None:
        """Get milestone ID by name."""
        try:
            with self.transaction() as conn:
                result = conn.execute(
                    "SELECT id FROM milestones WHERE title = ?", (milestone_name,)
                ).fetchone()
                return result[0] if result else None
        except Exception as e:
            logger.warning(f"Failed to find milestone '{milestone_name}'", error=str(e))
            return None

    def sync_milestone_file(self, file_path: Path) -> bool:
        """Sync a single milestone file to database."""
        try:
            if not file_path.exists():
                logger.warning(f"Milestone file not found: {file_path}")
                return False

            milestone_data = self._parse_yaml_frontmatter(file_path)
            if not milestone_data:
                logger.warning(f"No YAML data found in {file_path}")
                return False

            # Extract milestone ID
            milestone_id = milestone_data.get("id", file_path.stem)
            milestone_data["id"] = milestone_id

            # Handle missing project_id by assigning to first available project
            project_id = milestone_data.get("project_id")
            if not project_id:
                project_id = self._get_default_project_id()
                if not project_id:
                    logger.warning(
                        f"No projects found for milestone {milestone_id}, skipping"
                    )
                    return False

            # Ensure required fields - use 'name' if 'title' is not present
            title = milestone_data.get("title") or milestone_data.get(
                "name", "Untitled Milestone"
            )

            required_fields = {
                "title": title,
                "status": milestone_data.get("status", "open"),
                "project_id": project_id,
                "progress_percentage": milestone_data.get("progress_percentage", 0.0),
            }

            for field, default_value in required_fields.items():
                if field not in milestone_data:
                    milestone_data[field] = default_value

            # Convert dates
            if "due_date" in milestone_data and milestone_data["due_date"]:
                try:
                    if isinstance(milestone_data["due_date"], str):
                        milestone_data["due_date"] = datetime.fromisoformat(
                            milestone_data["due_date"]
                        ).date()
                except ValueError:
                    milestone_data["due_date"] = None

            # Store metadata
            metadata = {
                k: v
                for k, v in milestone_data.items()
                if k
                not in [
                    "id",
                    "title",
                    "description",
                    "status",
                    "due_date",
                    "progress_percentage",
                    "project_id",
                ]
            }
            milestone_data["metadata"] = json.dumps(metadata) if metadata else None

            # Upsert milestone
            with self.transaction() as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO milestones
                    (id, project_id, title, description, status, due_date, progress_percentage, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        milestone_data["id"],
                        milestone_data["project_id"],
                        milestone_data["title"],
                        milestone_data.get("description"),
                        milestone_data["status"],
                        milestone_data.get("due_date"),
                        milestone_data["progress_percentage"],
                        milestone_data["metadata"],
                    ),
                )

            # Update sync status
            file_stat = file_path.stat()
            content_hash = self._calculate_file_hash(file_path)
            self.update_file_sync_status(
                str(file_path),
                content_hash,
                file_stat.st_size,
                datetime.fromtimestamp(file_stat.st_mtime),
            )

            logger.info(
                f"Synced milestone file: {milestone_id}", file_path=str(file_path)
            )
            return True

        except Exception as e:
            logger.error(f"Failed to sync milestone file {file_path}", error=str(e))
            return False

    def sync_project_file(self, file_path: Path) -> bool:
        """Sync a single project file to database."""
        try:
            if not file_path.exists():
                logger.warning(f"Project file not found: {file_path}")
                return False

            project_data = self._parse_yaml_frontmatter(file_path)
            if not project_data:
                logger.warning(f"No YAML data found in {file_path}")
                return False

            # Extract project ID
            project_id = project_data.get("id", file_path.stem)
            project_data["id"] = project_id

            # Ensure required fields
            required_fields = {
                "name": project_data.get(
                    "name", project_data.get("title", "Untitled Project")
                ),
                "status": project_data.get("status", "active"),
            }

            for field, default_value in required_fields.items():
                if field not in project_data:
                    project_data[field] = default_value

            # Store metadata
            metadata = {
                k: v
                for k, v in project_data.items()
                if k not in ["id", "name", "description", "status"]
            }
            project_data["metadata"] = json.dumps(metadata) if metadata else None

            # Upsert project
            with self.transaction() as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO projects
                    (id, name, description, status, metadata)
                    VALUES (?, ?, ?, ?, ?)
                """,
                    (
                        project_data["id"],
                        project_data["name"],
                        project_data.get("description"),
                        project_data["status"],
                        project_data["metadata"],
                    ),
                )

            # Update sync status
            file_stat = file_path.stat()
            content_hash = self._calculate_file_hash(file_path)
            self.update_file_sync_status(
                str(file_path),
                content_hash,
                file_stat.st_size,
                datetime.fromtimestamp(file_stat.st_mtime),
            )

            logger.info(f"Synced project file: {project_id}", file_path=str(file_path))
            return True

        except Exception as e:
            logger.error(f"Failed to sync project file {file_path}", error=str(e))
            return False

    def sync_directory_incremental(self, roadmap_dir: Path) -> dict[str, Any]:
        """Incrementally sync .roadmap directory to database."""
        stats = {
            "files_checked": 0,
            "files_changed": 0,
            "files_synced": 0,
            "files_failed": 0,
            "sync_time": datetime.now(),
        }

        try:
            if not roadmap_dir.exists():
                logger.warning(f"Roadmap directory not found: {roadmap_dir}")
                return stats

            # Process in dependency order: projects first, then milestones, then issues
            for directory, pattern in [
                ("projects", "projects/*.md"),
                ("milestones", "milestones/*.md"),
                ("issues", "issues/*.md"),
            ]:
                dir_path = roadmap_dir / directory
                if dir_path.exists():
                    for file_path in roadmap_dir.glob(pattern):
                        stats["files_checked"] += 1
                        if self.has_file_changed(file_path):
                            stats["files_changed"] += 1

                            if "issues/" in str(file_path):
                                success = self.sync_issue_file(file_path)
                            elif "milestones/" in str(file_path):
                                success = self.sync_milestone_file(file_path)
                            elif "projects/" in str(file_path):
                                success = self.sync_project_file(file_path)
                            else:
                                continue

                            if success:
                                stats["files_synced"] += 1
                            else:
                                stats["files_failed"] += 1

            # Update last sync time
            self.set_sync_state("last_incremental_sync", str(stats["sync_time"]))

            logger.info(
                "Incremental sync completed",
                **{k: v for k, v in stats.items() if k != "sync_time"},
            )
            return stats

        except Exception as e:
            logger.error("Incremental sync failed", error=str(e))
            stats["files_failed"] += 1
            return stats

    def full_rebuild_from_git(self, roadmap_dir: Path) -> dict[str, Any]:
        """Full rebuild of database from git files."""
        stats = {
            "files_processed": 0,
            "files_changed": 0,  # All files are "changed" in a full rebuild
            "files_synced": 0,
            "files_failed": 0,
            "rebuild_time": datetime.now(),
        }

        try:
            if not roadmap_dir.exists():
                logger.warning(f"Roadmap directory not found: {roadmap_dir}")
                return stats

            # Clear existing sync state
            with self.transaction() as conn:
                conn.execute("DELETE FROM file_sync_state")
                conn.execute("DELETE FROM issues")
                conn.execute("DELETE FROM milestones")
                conn.execute("DELETE FROM projects")

            logger.info("Starting full rebuild from git files")

            # Rebuild from all files in dependency order (projects first, then milestones, then issues)
            for pattern in ["projects/*.md", "milestones/*.md", "issues/*.md"]:
                for file_path in roadmap_dir.glob(pattern):
                    stats["files_processed"] += 1
                    stats["files_changed"] += (
                        1  # All files are "changed" in full rebuild
                    )

                    if "issues/" in str(file_path):
                        success = self.sync_issue_file(file_path)
                    elif "milestones/" in str(file_path):
                        success = self.sync_milestone_file(file_path)
                    elif "projects/" in str(file_path):
                        success = self.sync_project_file(file_path)
                    else:
                        continue

                    if success:
                        stats["files_synced"] += 1
                    else:
                        stats["files_failed"] += 1

            # Update sync state
            self.set_sync_state("last_full_rebuild", str(stats["rebuild_time"]))
            self.set_sync_state("rebuild_reason", "manual_full_rebuild")

            logger.info(
                "Full rebuild completed",
                **{k: v for k, v in stats.items() if k != "rebuild_time"},
            )
            return stats

        except Exception as e:
            logger.error("Full rebuild failed", error=str(e))
            return stats

    def should_do_full_rebuild(self, roadmap_dir: Path, threshold: int = 50) -> bool:
        """Determine if full rebuild is needed vs incremental sync."""
        try:
            # Count total files
            total_files = 0
            for pattern in ["issues/*.md", "milestones/*.md", "projects/*.md"]:
                total_files += len(list(roadmap_dir.glob(pattern)))

            # Count changed files
            changed_files = 0
            for pattern in ["issues/*.md", "milestones/*.md", "projects/*.md"]:
                for file_path in roadmap_dir.glob(pattern):
                    if self.has_file_changed(file_path):
                        changed_files += 1

            # Check for missing sync state
            last_sync = self.get_sync_state("last_incremental_sync")
            if not last_sync:
                logger.info("No previous sync found, triggering full rebuild")
                return True

            # Threshold-based decision
            if total_files > 0 and (changed_files / total_files) >= threshold / 100:
                logger.info(
                    f"Many files changed ({changed_files}/{total_files}), triggering full rebuild"
                )
                return True

            return False

        except Exception as e:
            logger.error("Failed to determine rebuild strategy", error=str(e))
            return True  # Default to full rebuild on error

    def smart_sync(self, roadmap_dir: Path | None = None) -> dict[str, Any]:
        """Smart sync that chooses between incremental and full rebuild."""
        if roadmap_dir is None:
            roadmap_dir = Path.cwd() / ".roadmap"

        try:
            if self.should_do_full_rebuild(roadmap_dir):
                return self.full_rebuild_from_git(roadmap_dir)
            else:
                return self.sync_directory_incremental(roadmap_dir)

        except Exception as e:
            logger.error("Smart sync failed", error=str(e))
            return {"error": str(e), "files_failed": 1}

    def check_git_conflicts(self, roadmap_dir: Path | None = None) -> list[str]:
        """Check for git conflicts in .roadmap directory."""
        if roadmap_dir is None:
            roadmap_dir = Path.cwd() / ".roadmap"

        conflict_files = []

        try:
            if not roadmap_dir.exists():
                return conflict_files

            # Check for conflict markers in .roadmap files
            for pattern in ["**/*.md", "**/*.yaml", "**/*.yml"]:
                for file_path in roadmap_dir.glob(pattern):
                    try:
                        with open(file_path, encoding="utf-8") as f:
                            content = f.read()

                        # Look for git conflict markers
                        conflict_markers = ["<<<<<<<", "=======", ">>>>>>>"]
                        if any(marker in content for marker in conflict_markers):
                            conflict_files.append(
                                str(file_path.relative_to(Path.cwd()))
                            )

                    except Exception as e:
                        logger.warning(
                            f"Failed to check conflicts in {file_path}", error=str(e)
                        )

            if conflict_files:
                logger.warning(
                    f"Git conflicts detected in {len(conflict_files)} files",
                    conflicts=conflict_files,
                )
                self.set_sync_state("git_conflicts_detected", "true")
                self.set_sync_state("conflict_files", json.dumps(conflict_files))
            else:
                self.set_sync_state("git_conflicts_detected", "false")
                self.set_sync_state("conflict_files", "[]")

            return conflict_files

        except Exception as e:
            logger.error("Failed to check git conflicts", error=str(e))
            return conflict_files

    def has_git_conflicts(self) -> bool:
        """Check if there are unresolved git conflicts."""
        try:
            conflicts_detected = self.get_sync_state("git_conflicts_detected")
            return conflicts_detected == "true"
        except Exception:
            # If we can't check, assume no conflicts to avoid blocking operations
            return False

    def get_conflict_files(self) -> list[str]:
        """Get list of files with git conflicts."""
        try:
            conflict_files_json = self.get_sync_state("conflict_files")
            if conflict_files_json:
                return json.loads(conflict_files_json)
            return []
        except Exception:
            return []

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
            logger.warning("Error checking database existence", error=str(e))
            return False

    def has_file_changes(self) -> bool:
        """Check if .roadmap/ files have changes since last sync."""
        try:
            # Get roadmap directory from database path
            roadmap_dir = self.db_path.parent

            # Check for Markdown files with YAML frontmatter in relevant directories
            md_files = []
            for subdir in ["issues", "milestones", "projects"]:
                subdir_path = roadmap_dir / subdir
                if subdir_path.exists():
                    md_files.extend(subdir_path.glob("*.md"))

            if not md_files:
                return False

            # Check each file against stored hash
            with self.transaction() as conn:
                for file_path in md_files:
                    if not file_path.exists():
                        continue

                    # Calculate current hash
                    current_hash = hashlib.sha256(file_path.read_bytes()).hexdigest()

                    # Get stored hash
                    result = conn.execute(
                        "SELECT content_hash FROM file_sync_state WHERE file_path = ?",
                        (str(file_path.relative_to(roadmap_dir)),),
                    ).fetchone()

                    if not result or result[0] != current_hash:
                        # File is new or changed
                        return True

            return False

        except Exception as e:
            logger.warning("Error checking file changes", error=str(e))
            # If we can't check, assume changes exist to be safe
            return True

    def get_all_issues(self) -> list[dict[str, Any]]:
        """Get all issues from database."""
        try:
            with self.transaction() as conn:
                results = conn.execute("""
                    SELECT i.id, i.title, i.status, i.priority, i.issue_type,
                           i.assignee, i.estimate_hours, i.due_date,
                           i.project_id, i.milestone_id, i.metadata,
                           m.title as milestone_name, p.name as project_name
                    FROM issues i
                    LEFT JOIN milestones m ON i.milestone_id = m.id
                    LEFT JOIN projects p ON i.project_id = p.id
                    ORDER BY i.title
                """).fetchall()

                issues = []
                for row in results:
                    issue = {
                        "id": row[0],
                        "title": row[1],
                        "status": row[2],
                        "priority": row[3],
                        "type": row[4],
                        "assignee": row[5],
                        "estimate_hours": row[6],
                        "due_date": row[7],
                        "project_id": row[8],
                        "milestone_id": row[9],
                        "milestone_name": row[11],
                        "project_name": row[12],
                    }

                    # Parse metadata
                    if row[10]:
                        try:
                            metadata = json.loads(row[10])
                            issue.update(metadata)
                        except json.JSONDecodeError:
                            pass

                    issues.append(issue)

                return issues

        except Exception as e:
            logger.error("Failed to get issues", error=str(e))
            return []

    def get_all_milestones(self) -> list[dict[str, Any]]:
        """Get all milestones from database."""
        try:
            with self.transaction() as conn:
                results = conn.execute("""
                    SELECT m.id, m.title, m.description, m.status, m.due_date,
                           m.progress_percentage, m.project_id, m.metadata,
                           p.name as project_name
                    FROM milestones m
                    LEFT JOIN projects p ON m.project_id = p.id
                    ORDER BY m.title
                """).fetchall()

                milestones = []
                for row in results:
                    milestone = {
                        "id": row[0],
                        "name": row[1],  # Use 'name' for compatibility
                        "title": row[1],
                        "description": row[2],
                        "status": row[3],
                        "due_date": row[4],
                        "progress_percentage": row[5],
                        "project_id": row[6],
                        "project_name": row[8],
                    }

                    # Parse metadata
                    if row[7]:
                        try:
                            metadata = json.loads(row[7])
                            milestone.update(metadata)
                        except json.JSONDecodeError:
                            pass

                    milestones.append(milestone)

                return milestones

        except Exception as e:
            logger.error("Failed to get milestones", error=str(e))
            return []

    def get_milestone_progress(self, milestone_name: str) -> dict[str, int]:
        """Get progress stats for a milestone."""
        try:
            with self.transaction() as conn:
                # Get milestone ID first
                milestone_result = conn.execute(
                    "SELECT id FROM milestones WHERE title = ?", (milestone_name,)
                ).fetchone()

                if not milestone_result:
                    return {"total": 0, "completed": 0}

                milestone_id = milestone_result[0]

                # Count total and done issues for this milestone
                total_result = conn.execute(
                    "SELECT COUNT(*) FROM issues WHERE milestone_id = ?",
                    (milestone_id,),
                ).fetchone()

                completed_result = conn.execute(
                    "SELECT COUNT(*) FROM issues WHERE milestone_id = ? AND status = 'closed'",
                    (milestone_id,),
                ).fetchone()

                return {
                    "total": total_result[0] if total_result else 0,
                    "completed": completed_result[0] if completed_result else 0,
                }

        except Exception as e:
            logger.error(
                f"Failed to get milestone progress for {milestone_name}", error=str(e)
            )
            return {"total": 0, "completed": 0}

    def get_issues_by_status(self) -> dict[str, int]:
        """Get issue counts by status."""
        try:
            with self.transaction() as conn:
                results = conn.execute("""
                    SELECT status, COUNT(*)
                    FROM issues
                    GROUP BY status
                    ORDER BY status
                """).fetchall()

                return {row[0]: row[1] for row in results}

        except Exception as e:
            logger.error("Failed to get issues by status", error=str(e))
            return {}

    def is_safe_for_writes(self) -> tuple[bool, str]:
        """Check if database is safe for write operations."""
        try:
            # Check for git conflicts
            if self.has_git_conflicts():
                conflict_files = self.get_conflict_files()
                return (
                    False,
                    f"Git conflicts detected in {len(conflict_files)} files. Resolve conflicts first.",
                )

            # Check database integrity
            conn = self._get_connection()
            try:
                conn.execute("PRAGMA integrity_check").fetchone()
            except sqlite3.DatabaseError as e:
                return False, f"Database corruption detected: {e}"

            return True, "Database ready for operations"

        except Exception as e:
            return False, f"Safety check failed: {e}"


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
