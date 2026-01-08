"""State manager and database errors for persistence layer."""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from roadmap.common.logging import get_logger

from ..conflict_resolver import ConflictResolver
from ..database_manager import DatabaseManager
from ..file_synchronizer import FileSynchronizer
from ..repositories import (
    IssueRepository,
    MilestoneRepository,
    ProjectRepository,
    RemoteLinkRepository,
    SyncStateRepository,
)
from ..sync_state_tracker import SyncStateTracker
from .connection_manager import ConnectionManager
from .issue_storage import IssueStorage
from .milestone_storage import MilestoneStorage
from .project_storage import ProjectStorage
from .sync_state_storage import SyncStateStorage

if TYPE_CHECKING:
    from roadmap.adapters.git.sync_monitor import GitSyncMonitor  # noqa: F401

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

    def __init__(
        self,
        db_path: str | Path | None = None,
        git_sync_monitor: "GitSyncMonitor | None" = None,
    ):
        """Initialize the state manager.

        Args:
            db_path: Path to SQLite database file. Defaults to ~/.roadmap/roadmap.db
            git_sync_monitor: Optional GitSyncMonitor for cache invalidation via git diff.
                            If provided, database will sync on access.
        """
        if db_path is None:
            db_path = Path.home() / ".roadmap" / "roadmap.db"

        self.db_path = Path(db_path)
        self._git_sync_monitor = git_sync_monitor
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
        self._remote_link_repo = RemoteLinkRepository(
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

        logger.info(
            "Initializing state manager",
            db_path=str(self.db_path),
            has_git_monitor=git_sync_monitor is not None,
        )

        # Note: Remote links initialization moved to RoadmapCore.initialize_remote_links()
        # because StateManager doesn't have access to roadmap_dir

    # Connection management - delegate to ConnectionManager
    def _get_connection(self) -> sqlite3.Connection:
        """Get thread-local database connection."""
        return self._connection_manager.get_connection()

    def transaction(self):
        """Context manager for database transactions."""
        return self._connection_manager.transaction()

    def _sync_git_state(self) -> None:
        """Sync git state to database if GitSyncMonitor is configured.

        This ensures the database cache is up-to-date with git before
        any repository access. Called transparently before repo operations.
        """
        if self._git_sync_monitor is None:
            return

        try:
            changes = self._git_sync_monitor.detect_changes()
            if changes:
                self._git_sync_monitor.sync_to_database(changes)
        except Exception as e:
            logger.warning(
                "Git sync failed, proceeding with potentially stale cache",
                error=str(e),
                error_type=type(e).__name__,
            )

    def _initialize_remote_links_from_yaml(self) -> None:
        """Initialize database remote_links from YAML files on startup.

        This is a one-time initialization that loads all remote_ids found in
        YAML frontmatter into the database cache for fast O(1) lookups during
        sync operations.

        Only loads links if database is empty (first initialization or reset).

        Note: This method is deprecated. Use initialize_remote_links(roadmap_dir) instead.
        """
        # This is kept for backward compatibility but does nothing
        # The actual initialization is now done by initialize_remote_links()

    def initialize_remote_links(self, roadmap_dir: Path | str) -> None:
        """Initialize remote_links from YAML files in the given roadmap directory.

        Args:
            roadmap_dir: Path to the roadmap directory
        """
        self._initialize_remote_links_impl(roadmap_dir)

    def _initialize_remote_links_impl(self, roadmap_dir: Path | str) -> None:
        """Implementation of remote links initialization.

        Args:
            roadmap_dir: Path to the roadmap directory
        """
        try:
            # Check if remote_links table already has data (skip if so)
            existing_github_links = self._remote_link_repo.get_all_links_for_backend(
                "github"
            )
            if existing_github_links:
                logger.debug(
                    "remote_links_already_initialized",
                    existing_count=len(existing_github_links),
                )
                return

            # Load all issue files from roadmap_dir/.roadmap/issues directory
            from roadmap.adapters.persistence.parser.issue import IssueParser

            issues_dir = Path(roadmap_dir) / ".roadmap" / "issues"

            if not issues_dir.exists():
                logger.debug("issues_directory_not_found", path=str(issues_dir))
                return

            # Collect all issue files from all subdirectories
            issue_files = list(issues_dir.glob("**/*.md"))
            if not issue_files:
                logger.debug("no_issue_files_found", path=str(issues_dir))
                return

            # Build dict of issue_uuid -> dict[backend_name -> remote_id]
            issues_with_remote_ids = {}
            for file_path in issue_files:
                try:
                    issue = IssueParser.parse_issue_file(file_path)
                    if issue.remote_ids:
                        issues_with_remote_ids[issue.id] = issue.remote_ids
                except Exception as e:
                    logger.warning(
                        "failed_to_parse_issue_file",
                        file_path=str(file_path),
                        error=str(e),
                    )
                    continue

            if not issues_with_remote_ids:
                logger.debug("no_remote_ids_found_in_yaml_files")
                return

            # Bulk import into database
            count = self._remote_link_repo.bulk_import_from_yaml(issues_with_remote_ids)
            logger.info(
                "initialized_remote_links_from_yaml",
                total_files=len(issue_files),
                issues_with_links=len(issues_with_remote_ids),
                links_imported=count,
            )

        except Exception as e:
            logger.error(
                "failed_to_initialize_remote_links",
                error=str(e),
                error_type=type(e).__name__,
            )
            # Don't raise - allow startup to proceed even if initialization fails

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

    # Repository access - with automatic git sync
    def get_issue_repository(self) -> IssueRepository:
        """Get issue repository after syncing git state.

        Returns:
            IssueRepository with database synced to latest git state
        """
        self._sync_git_state()
        return self._issue_repo

    def get_milestone_repository(self) -> MilestoneRepository:
        """Get milestone repository after syncing git state.

        Returns:
            MilestoneRepository with database synced to latest git state
        """
        self._sync_git_state()
        return self._milestone_repo

    def get_project_repository(self) -> ProjectRepository:
        """Get project repository after syncing git state.

        Returns:
            ProjectRepository with database synced to latest git state
        """
        self._sync_git_state()
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

    # Sync state operations - delegate to SyncStateStorage
    def get_sync_state(self, key: str) -> str | None:
        """Get sync state value."""
        return self._sync_state_storage.get_sync_state(key)

    def set_sync_state(self, key: str, value: str):
        """Set sync state value."""
        self._sync_state_storage.set_sync_state(key, value)

    # Remote link operations - delegate to RemoteLinkRepository
    @property
    def remote_links(self) -> RemoteLinkRepository:
        """Get remote link repository for sync backend operations."""
        return self._remote_link_repo

    # Sync baseline operations - store/retrieve baseline for three-way merge
    def get_sync_baseline(self) -> dict[str, Any] | None:
        """Get the sync baseline from database.

        The baseline represents the state of issues as they were during the last
        successful sync. Used for three-way merge to detect conflicts.

        Returns:
            Dictionary mapping issue_id to baseline state, or None if no baseline exists
        """
        try:
            import json

            self._sync_git_state()

            conn = self._get_connection()
            rows = conn.execute(
                """
                SELECT issue_id, status, assignee, milestone, description, labels, synced_at
                FROM sync_base_state
                ORDER BY synced_at DESC
            """
            ).fetchall()

            if not rows:
                logger.debug("no_sync_baseline_found")
                return None

            baseline = {}
            for row in rows:
                baseline[row["issue_id"]] = {
                    "status": row["status"],
                    "assignee": row["assignee"],
                    "milestone": row["milestone"],
                    "headline": row["description"],
                    "labels": json.loads(row["labels"]) if row["labels"] else [],
                    "synced_at": row["synced_at"],
                }

            logger.debug(
                "loaded_sync_baseline",
                issue_count=len(baseline),
                synced_at=rows[0]["synced_at"],
            )
            return baseline

        except Exception as e:
            logger.error(
                "error_loading_sync_baseline",
                error=str(e),
                error_type=type(e).__name__,
            )
            return None

    def save_sync_baseline(self, baseline: dict[str, Any]) -> bool:
        """Save the current sync baseline to database.

        Called after a successful sync to establish the new baseline for the
        next sync's three-way merge.

        Args:
            baseline: Dictionary mapping issue_id to state dict with keys:
                     status, assignee, milestone, headline, labels

        Returns:
            True if saved successfully, False otherwise
        """
        try:
            import json

            now = datetime.utcnow().isoformat()

            with self.transaction() as conn:
                # Clear old baseline
                conn.execute("DELETE FROM sync_base_state")

                # Insert new baseline
                for issue_id, state in baseline.items():
                    conn.execute(
                        """
                        INSERT INTO sync_base_state
                        (issue_id, status, assignee, milestone, description, labels, synced_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                        (
                            issue_id,
                            state.get("status"),
                            state.get("assignee"),
                            state.get("milestone"),
                            state.get("headline"),
                            json.dumps(state.get("labels", [])),
                            now,
                        ),
                    )

            logger.debug(
                "saved_sync_baseline", issue_count=len(baseline), synced_at=now
            )
            return True

        except Exception as e:
            logger.error(
                "error_saving_sync_baseline",
                error=str(e),
                error_type=type(e).__name__,
            )
            return False

    def clear_sync_baseline(self) -> bool:
        """Clear the sync baseline (used before first sync).

        Returns:
            True if cleared successfully
        """
        try:
            with self.transaction() as conn:
                conn.execute("DELETE FROM sync_base_state")
            logger.debug("cleared_sync_baseline")
            return True
        except Exception as e:
            logger.error(
                "error_clearing_sync_baseline",
                error=str(e),
                error_type=type(e).__name__,
            )
            return False

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
