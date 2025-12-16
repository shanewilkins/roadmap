"""State manager and database errors for persistence layer."""

import sqlite3
from pathlib import Path
from typing import Any

from roadmap.common.logging import get_logger

from ..conflict_resolver import ConflictResolver
from ..database_manager import DatabaseManager
from ..file_synchronizer import FileSynchronizer
from ..repositories import (
    IssueRepository,
    MilestoneRepository,
    ProjectRepository,
    SyncStateRepository,
)
from ..sync_state_tracker import SyncStateTracker
from .connection_manager import ConnectionManager
from .issue_storage import IssueStorage
from .milestone_storage import MilestoneStorage
from .project_storage import ProjectStorage
from .sync_state_storage import SyncStateStorage

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

        # Initialize storage layers
        self._connection_manager = ConnectionManager(self._db_manager)
        self._project_storage = ProjectStorage(self._project_repo)
        self._milestone_storage = MilestoneStorage(self._milestone_repo)
        self._issue_storage = IssueStorage(self._issue_repo)
        self._sync_state_storage = SyncStateStorage(
            self._sync_state_repo, self._file_synchronizer
        )

        # Expose database manager's _local for backward compatibility with tests
        self._local = self._db_manager._local

        logger.info("Initializing state manager", db_path=str(self.db_path))

    # Connection management - delegate to ConnectionManager
    def _get_connection(self) -> sqlite3.Connection:
        """Get thread-local database connection."""
        return self._connection_manager.get_connection()

    def transaction(self):
        """Context manager for database transactions."""
        return self._connection_manager.transaction()

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
        return self._connection_manager.is_initialized()

    def close(self):
        """Close database connections."""
        self._connection_manager.close()

    def vacuum(self):
        """Optimize database."""
        self._connection_manager.vacuum()

    def database_exists(self) -> bool:
        """Check if database file exists and has tables."""
        return self._connection_manager.database_exists()

    # Project operations - delegate to ProjectStorage
    def create_project(self, project_data: dict[str, Any]) -> str:
        """Create a new project."""
        return self._project_storage.create(project_data)

    def get_project(self, project_id: str) -> dict[str, Any] | None:
        """Get project by ID."""
        return self._project_storage.get(project_id)

    def list_projects(self) -> list[dict[str, Any]]:
        """List all projects."""
        return self._project_storage.list_all()

    def update_project(self, project_id: str, updates: dict[str, Any]) -> bool:
        """Update project."""
        return self._project_storage.update(project_id, updates)

    def delete_project(self, project_id: str) -> bool:
        """Delete project and all related data."""
        return self._project_storage.delete(project_id)

    def mark_project_archived(self, project_id: str, archived: bool = True) -> bool:
        """Mark a project as archived or unarchived."""
        return self._project_storage.mark_archived(project_id, archived)

    # Milestone operations - delegate to MilestoneStorage
    def create_milestone(self, milestone_data: dict[str, Any]) -> str:
        """Create a new milestone."""
        return self._milestone_storage.create(milestone_data)

    def get_milestone(self, milestone_id: str) -> dict[str, Any] | None:
        """Get milestone by ID."""
        return self._milestone_storage.get(milestone_id)

    def update_milestone(self, milestone_id: str, updates: dict[str, Any]) -> bool:
        """Update milestone."""
        return self._milestone_storage.update(milestone_id, updates)

    def mark_milestone_archived(self, milestone_id: str, archived: bool = True) -> bool:
        """Mark a milestone as archived or unarchived."""
        return self._milestone_storage.mark_archived(milestone_id, archived)

    # Issue operations - delegate to IssueStorage
    def create_issue(self, issue_data: dict[str, Any]) -> str:
        """Create a new issue."""
        return self._issue_storage.create(issue_data)

    def get_issue(self, issue_id: str) -> dict[str, Any] | None:
        """Get issue by ID."""
        return self._issue_storage.get(issue_id)

    def update_issue(self, issue_id: str, updates: dict[str, Any]) -> bool:
        """Update issue."""
        return self._issue_storage.update(issue_id, updates)

    def delete_issue(self, issue_id: str) -> bool:
        """Delete issue."""
        return self._issue_storage.delete(issue_id)

    def mark_issue_archived(self, issue_id: str, archived: bool = True) -> bool:
        """Mark an issue as archived or unarchived."""
        return self._issue_storage.mark_archived(issue_id, archived)

    # Sync state operations - delegate to SyncStateStorage
    def get_sync_state(self, key: str) -> str | None:
        """Get sync state value."""
        return self._sync_state_storage.get_sync_state(key)

    def set_sync_state(self, key: str, value: str):
        """Set sync state value."""
        self._sync_state_storage.set_sync_state(key, value)

    # File sync delegation - delegate to SyncStateStorage
    def get_file_sync_status(self, file_path: str) -> dict[str, Any] | None:
        """Get sync status for a file."""
        return self._sync_state_storage.get_file_sync_status(file_path)

    def update_file_sync_status(
        self, file_path: str, content_hash: str, file_size: int, last_modified: Any
    ):
        """Update sync status for a file."""
        self._sync_state_storage.update_file_sync_status(
            file_path, content_hash, file_size, last_modified
        )

    def has_file_changed(self, file_path: Path) -> bool:
        """Check if file has changed since last sync."""
        return self._sync_state_storage.has_file_changed(file_path)

    def sync_directory_incremental(self, roadmap_dir: Path) -> dict[str, Any]:
        """Incrementally sync .roadmap directory to database."""
        return self._sync_state_storage.sync_directory_incremental(roadmap_dir)

    def full_rebuild_from_git(self, roadmap_dir: Path) -> dict[str, Any]:
        """Full rebuild of database from git files."""
        return self._sync_state_storage.full_rebuild_from_git(roadmap_dir)

    def should_do_full_rebuild(self, roadmap_dir: Path, threshold: int = 50) -> bool:
        """Determine if full rebuild is needed vs incremental sync."""
        return self._sync_state_storage.should_do_full_rebuild(roadmap_dir, threshold)

    def smart_sync(self, roadmap_dir: Path | None = None) -> dict[str, Any]:
        """Smart sync that chooses between incremental and full rebuild."""
        return self._sync_state_storage.smart_sync(roadmap_dir)

    # Query operations - these delegate complex queries to query service
    def has_file_changes(self) -> bool:
        """Check if .roadmap/ files have changes since last sync."""
        return self._sync_state_storage.has_file_changes(self)

    def get_all_issues(self) -> list[dict[str, Any]]:
        """Get all issues from database."""
        from .queries import QueryService

        logger.debug("getting_all_issues")
        issues = QueryService(self).get_all_issues()
        logger.debug("get_all_issues_completed", issue_count=len(issues))
        return issues

    def get_all_milestones(self) -> list[dict[str, Any]]:
        """Get all milestones from database."""
        from .queries import QueryService

        return QueryService(self).get_all_milestones()

    def get_milestone_progress(self, milestone_name: str) -> dict[str, int]:
        """Get progress stats for a milestone."""
        from .queries import QueryService

        return QueryService(self).get_milestone_progress(milestone_name)

    def get_issues_by_status(self) -> dict[str, int]:
        """Get issue counts by status."""
        from .queries import QueryService

        return QueryService(self).get_issues_by_status()

    # Conflict operations - delegate to conflict service
    def check_git_conflicts(self, roadmap_dir: Path | None = None) -> list[str]:
        """Check for git conflicts in .roadmap directory."""
        from .conflicts import ConflictService

        return ConflictService(self).check_git_conflicts(roadmap_dir)

    def has_git_conflicts(self) -> bool:
        """Check if there are unresolved git conflicts."""
        from .conflicts import ConflictService

        return ConflictService(self).has_git_conflicts()

    def get_conflict_files(self) -> list[str]:
        """Get list of files with git conflicts."""
        from .conflicts import ConflictService

        return ConflictService(self).get_conflict_files()

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

            # Delegate to connection manager for safety check
            return self._connection_manager.is_safe_for_writes()

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
