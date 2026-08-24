"""State manager and database errors for persistence layer."""

import sqlite3
from pathlib import Path
from typing import Any

from roadmap.common.logging import get_logger

from ..database_manager import DatabaseManager
from ..repositories import (
    IssueRepository,
    MilestoneRepository,
    ProjectRepository,
)
from .connection_manager import ConnectionManager
from .issue_storage import IssueStorage
from .milestone_storage import MilestoneStorage
from .project_storage import ProjectStorage

logger = get_logger(__name__)


class DatabaseError(Exception):
    """Base exception for database operations."""


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

        # Initialize storage layers
        self._connection_manager = ConnectionManager(self._db_manager)
        self._project_storage = ProjectStorage(self._project_repo)
        self._milestone_storage = MilestoneStorage(self._milestone_repo)
        self._issue_storage = IssueStorage(self._issue_repo)

        # Expose database manager's _local for backward compatibility with tests
        self._local = self._db_manager._local

        logger.info(
            "Initializing state manager",
            db_path=str(self.db_path),
        )

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

    # Repository access
    def get_issue_repository(self) -> IssueRepository:
        """Get the issue repository."""
        return self._issue_repo

    def get_milestone_repository(self) -> MilestoneRepository:
        """Get the milestone repository."""
        return self._milestone_repo

    def get_project_repository(self) -> ProjectRepository:
        """Get the project repository."""
        return self._project_repo

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

    # Query operations - these delegate complex queries to query service
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

        return ConflictService().check_git_conflicts(roadmap_dir)

    def has_git_conflicts(self) -> bool:
        """Check if there are unresolved git conflicts."""
        from .conflicts import ConflictService

        return ConflictService().has_git_conflicts()

    def get_conflict_files(self) -> list[str]:
        """Get list of files with git conflicts."""
        from .conflicts import ConflictService

        return ConflictService().get_conflict_files()

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
