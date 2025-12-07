"""SQLite-based state management for roadmap CLI application.

This module provides a persistent state management layer using SQLite,
replacing the file-based approach with a proper database backend for
better performance and data integrity.
"""

import hashlib
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from roadmap.common.logging import get_logger

from .conflict_resolver import ConflictResolver
from .database_manager import DatabaseManager
from .file_synchronizer import FileSynchronizer
from .repositories import (
    IssueRepository,
    MilestoneRepository,
    ProjectRepository,
    SyncStateRepository,
)
from .sync_state_tracker import SyncStateTracker

logger = get_logger(__name__)


class DatabaseError(Exception):
    """Base exception for database operations."""

    pass


class StateManager:
    """SQLite-based state manager for roadmap data.

    This class serves as a facade, delegating entity-specific operations
    to specialized repository classes while maintaining connection management
    and transaction handling.
    """

    def __init__(self, db_path: str | Path | None = None):
        """Initialize the state manager.

        Args:
            db_path: Path to SQLite database file. Defaults to ~/.roadmap/roadmap.db
        """
        if db_path is None:
            db_path = Path.home() / ".roadmap" / "roadmap.db"

        self.db_path = Path(db_path)
        self._db_manager = DatabaseManager(db_path)
        self._file_synchronizer = FileSynchronizer(
            self._db_manager._get_connection, self._db_manager.transaction
        )
        self._sync_state_tracker = SyncStateTracker(self._db_manager._get_connection)
        self._conflict_resolver = ConflictResolver(
            self.db_path.parent
        )  # data_dir is parent of db file

        # Initialize repositories
        self._project_repo = ProjectRepository(
            self._db_manager._get_connection, self._db_manager.transaction
        )
        self._milestone_repo = MilestoneRepository(
            self._db_manager._get_connection, self._db_manager.transaction
        )
        self._issue_repo = IssueRepository(
            self._db_manager._get_connection, self._db_manager.transaction
        )
        self._sync_state_repo = SyncStateRepository(
            self._db_manager._get_connection, self._db_manager.transaction
        )

        # Expose database manager's _local for backward compatibility with tests
        self._local = self._db_manager._local

        logger.info("Initializing state manager", db_path=str(self.db_path))

    def _get_connection(self) -> sqlite3.Connection:
        """Get thread-local database connection."""
        return self._db_manager._get_connection()

    def transaction(self):
        """Context manager for database transactions."""
        return self._db_manager.transaction()

    def _init_database(self):
        """Initialize database schema."""
        # Delegated to DatabaseManager during initialization
        pass

    def _run_migrations(self):
        """Run database migrations for schema updates."""
        # Delegated to DatabaseManager during initialization
        pass

    def is_initialized(self) -> bool:
        """Check if database is properly initialized."""
        return self._db_manager.is_initialized()

    # ========== Project operations (delegated to ProjectRepository) ==========
    def create_project(self, project_data: dict[str, Any]) -> str:
        """Create a new project."""
        return self._project_repo.create(project_data)

    def get_project(self, project_id: str) -> dict[str, Any] | None:
        """Get project by ID."""
        return self._project_repo.get(project_id)

    def list_projects(self) -> list[dict[str, Any]]:
        """List all projects."""
        return self._project_repo.list_all()

    def update_project(self, project_id: str, updates: dict[str, Any]) -> bool:
        """Update project."""
        return self._project_repo.update(project_id, updates)

    def delete_project(self, project_id: str) -> bool:
        """Delete project and all related data."""
        return self._project_repo.delete(project_id)

    def mark_project_archived(self, project_id: str, archived: bool = True) -> bool:
        """Mark a project as archived or unarchived."""
        return self._project_repo.mark_archived(project_id, archived)

    # ========== Milestone operations (delegated to MilestoneRepository) ==========
    def create_milestone(self, milestone_data: dict[str, Any]) -> str:
        """Create a new milestone."""
        return self._milestone_repo.create(milestone_data)

    def get_milestone(self, milestone_id: str) -> dict[str, Any] | None:
        """Get milestone by ID."""
        return self._milestone_repo.get(milestone_id)

    def update_milestone(self, milestone_id: str, updates: dict[str, Any]) -> bool:
        """Update milestone."""
        return self._milestone_repo.update(milestone_id, updates)

    def mark_milestone_archived(self, milestone_id: str, archived: bool = True) -> bool:
        """Mark a milestone as archived or unarchived."""
        return self._milestone_repo.mark_archived(milestone_id, archived)

    # ========== Issue operations (delegated to IssueRepository) ==========
    def create_issue(self, issue_data: dict[str, Any]) -> str:
        """Create a new issue."""
        return self._issue_repo.create(issue_data)

    def get_issue(self, issue_id: str) -> dict[str, Any] | None:
        """Get issue by ID."""
        return self._issue_repo.get(issue_id)

    def update_issue(self, issue_id: str, updates: dict[str, Any]) -> bool:
        """Update issue."""
        return self._issue_repo.update(issue_id, updates)

    def delete_issue(self, issue_id: str) -> bool:
        """Delete issue."""
        return self._issue_repo.delete(issue_id)

    def mark_issue_archived(self, issue_id: str, archived: bool = True) -> bool:
        """Mark an issue as archived or unarchived."""
        return self._issue_repo.mark_archived(issue_id, archived)

    # ========== Sync state operations (delegated to SyncStateRepository) ==========
    def get_sync_state(self, key: str) -> str | None:
        """Get sync state value."""
        return self._sync_state_repo.get(key)

    def set_sync_state(self, key: str, value: str):
        """Set sync state value."""
        self._sync_state_repo.set(key, value)

    def close(self):
        """Close database connections."""
        self._db_manager.close()

    def vacuum(self):
        """Optimize database."""
        self._db_manager.vacuum()

    # YAML parsing and file synchronization methods

    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA-256 hash of file content."""
        return self._file_synchronizer._calculate_file_hash(file_path)

    def _parse_yaml_frontmatter(self, file_path: Path) -> dict[str, Any]:
        """Parse YAML frontmatter from markdown file."""
        return self._file_synchronizer._parse_yaml_frontmatter(file_path)

    def get_file_sync_status(self, file_path: str) -> dict[str, Any] | None:
        """Get sync status for a file."""
        return self._file_synchronizer.get_file_sync_status(file_path)

    def update_file_sync_status(
        self, file_path: str, content_hash: str, file_size: int, last_modified: datetime
    ):
        """Update sync status for a file."""
        self._file_synchronizer.update_file_sync_status(
            file_path, content_hash, file_size, last_modified
        )

    def has_file_changed(self, file_path: Path) -> bool:
        """Check if file has changed since last sync."""
        return self._file_synchronizer.has_file_changed(file_path)

    def sync_issue_file(self, file_path: Path) -> bool:
        """Sync a single issue file to database."""
        return self._file_synchronizer.sync_issue_file(file_path)

    def _get_default_project_id(self) -> str | None:
        """Get the first available project ID for orphaned milestones/issues."""
        return self._file_synchronizer._get_default_project_id()

    def _get_milestone_id_by_name(self, milestone_name: str) -> str | None:
        """Get milestone ID by name."""
        return self._file_synchronizer._get_milestone_id_by_name(milestone_name)

    def sync_milestone_file(self, file_path: Path) -> bool:
        """Sync a single milestone file to database."""
        return self._file_synchronizer.sync_milestone_file(file_path)

    def sync_project_file(self, file_path: Path) -> bool:
        """Sync a single project file to database."""
        return self._file_synchronizer.sync_project_file(file_path)

    def sync_directory_incremental(self, roadmap_dir: Path) -> dict[str, Any]:
        """Incrementally sync .roadmap directory to database."""
        return self._file_synchronizer.sync_directory_incremental(roadmap_dir)

    def full_rebuild_from_git(self, roadmap_dir: Path) -> dict[str, Any]:
        """Full rebuild of database from git files."""
        return self._file_synchronizer.full_rebuild_from_git(roadmap_dir)

    def should_do_full_rebuild(self, roadmap_dir: Path, threshold: int = 50) -> bool:
        """Determine if full rebuild is needed vs incremental sync."""
        return self._file_synchronizer.should_do_full_rebuild(roadmap_dir, threshold)

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
        return self._db_manager.database_exists()

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
                    md_files.extend(subdir_path.rglob("*.md"))

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

            # Delegate to database manager for safety check
            return self._db_manager.is_safe_for_writes()

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
