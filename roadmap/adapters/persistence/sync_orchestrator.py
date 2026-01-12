"""Orchestrates file synchronization across the .roadmap directory."""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from roadmap.adapters.persistence.entity_sync_coordinators import (
    IssueSyncCoordinator,
    MilestoneSyncCoordinator,
    ProjectSyncCoordinator,
)
from roadmap.adapters.persistence.file_parser import FileParser
from roadmap.adapters.persistence.sync_state_tracker import SyncStateTracker
from roadmap.common.logging import get_logger

logger = get_logger(__name__)


class SyncOrchestrator:
    """Orchestrates synchronization of .roadmap directory to database."""

    def __init__(self, get_connection, transaction_context):
        """Initialize the orchestrator.

        Args:
            get_connection: Callable that returns a database connection
            transaction_context: Context manager for transactions
        """
        self._get_connection = get_connection
        self._transaction = transaction_context
        self._parser = FileParser()
        self._state_tracker = SyncStateTracker(get_connection)
        self._issue_sync = IssueSyncCoordinator(get_connection, transaction_context)
        self._milestone_sync = MilestoneSyncCoordinator(
            get_connection, transaction_context
        )
        self._project_sync = ProjectSyncCoordinator(get_connection, transaction_context)

    def _has_file_changed(self, file_path: Path) -> bool:
        """Check if file has changed since last sync."""
        try:
            if not file_path.exists():
                return True

            current_hash = self._parser.calculate_file_hash(file_path)
            conn = self._get_connection()
            row = conn.execute(
                "SELECT content_hash FROM file_sync_state WHERE file_path = ?",
                (str(file_path),),
            ).fetchone()

            if not row:
                return True  # Never synced
            return current_hash != row[0]

        except Exception as e:
            logger.error(f"Failed to check file changes for {file_path}", error=str(e))
            return True

    def _sync_file_by_type(self, file_path: Path, stats: dict) -> bool:
        """Sync file based on its type.

        Args:
            file_path: Path to file to sync
            stats: Stats dict to update

        Returns:
            True if sync was successful
        """
        if "issues/" in str(file_path):
            success = self._issue_sync.sync_issue_file(file_path)
        elif "milestones/" in str(file_path):
            success = self._milestone_sync.sync_milestone_file(file_path)
        elif "projects/" in str(file_path):
            success = self._project_sync.sync_project_file(file_path)
        else:
            return False

        if success:
            stats["files_synced"] += 1
        else:
            stats["files_failed"] += 1
        return success

    def sync_directory_incremental(self, roadmap_dir: Path) -> dict[str, Any]:
        """Incrementally sync .roadmap directory to database."""
        stats = {
            "files_checked": 0,
            "files_changed": 0,
            "files_synced": 0,
            "files_failed": 0,
            "sync_time": datetime.now(UTC),
        }

        try:
            if not roadmap_dir.exists():
                logger.warning(f"Roadmap directory not found: {roadmap_dir}")
                return stats

            # Process in dependency order: projects first, then milestones, then issues
            for pattern in ["projects/**/*.md", "milestones/**/*.md", "issues/**/*.md"]:
                for file_path in roadmap_dir.glob(pattern):
                    stats["files_checked"] += 1
                    if self._has_file_changed(file_path):
                        stats["files_changed"] += 1
                        self._sync_file_by_type(file_path, stats)

            # Update checkpoint
            self._state_tracker.update_last_incremental_sync(str(stats["sync_time"]))

            logger.info(
                "Incremental sync completed",
                **{k: v for k, v in stats.items() if k != "sync_time"},
            )
            return stats

        except Exception as e:
            logger.error("Incremental sync failed", error=str(e))
            stats["files_failed"] += 1
            return stats

    def _clear_database_for_rebuild(self) -> None:
        """Clear database state for full rebuild."""
        with self._transaction() as conn:
            conn.execute("DELETE FROM file_sync_state")
            conn.execute("DELETE FROM issues")

    def _sync_file_in_rebuild(self, file_path: Path, stats: dict) -> None:
        """Sync a single file during rebuild and update stats.

        Args:
            file_path: Path to file to sync
            stats: Statistics dict to update
        """
        stats["files_processed"] += 1
        stats["files_changed"] += 1

        if "issues/" in str(file_path):
            success = self._issue_sync.sync_issue_file(file_path)
        elif "milestones/" in str(file_path):
            success = self._milestone_sync.sync_milestone_file(file_path)
        elif "projects/" in str(file_path):
            success = self._project_sync.sync_project_file(file_path)
        else:
            return

        if success:
            stats["files_synced"] += 1
        else:
            stats["files_failed"] += 1

    def _rebuild_from_file_patterns(self, roadmap_dir: Path, stats: dict) -> None:
        """Rebuild database by processing files in dependency order.

        Args:
            roadmap_dir: Root roadmap directory
            stats: Statistics dict to update
        """
        for pattern in ["projects/**/*.md", "milestones/**/*.md", "issues/**/*.md"]:
            for file_path in roadmap_dir.glob(pattern):
                self._sync_file_in_rebuild(file_path, stats)

    def full_rebuild_from_git(self, roadmap_dir: Path) -> dict[str, Any]:
        """Full rebuild of database from git files."""
        stats = {
            "files_processed": 0,
            "files_changed": 0,
            "files_synced": 0,
            "files_failed": 0,
            "rebuild_time": datetime.now(UTC),
        }

        try:
            if not roadmap_dir.exists():
                logger.warning(f"Roadmap directory not found: {roadmap_dir}")
                return stats

            # Clear existing data
            self._clear_database_for_rebuild()

            logger.info("Starting full rebuild from git files")

            # Rebuild from all files in dependency order
            self._rebuild_from_file_patterns(roadmap_dir, stats)

            # Update checkpoints
            self._state_tracker.update_last_full_rebuild(str(stats["rebuild_time"]))

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
            for pattern in ["issues/**/*.md", "milestones/**/*.md", "projects/**/*.md"]:
                total_files += len(list(roadmap_dir.glob(pattern)))

            # Count changed files
            changed_files = 0
            for pattern in ["issues/**/*.md", "milestones/**/*.md", "projects/**/*.md"]:
                for file_path in roadmap_dir.glob(pattern):
                    if self._has_file_changed(file_path):
                        changed_files += 1

            # Check for missing sync checkpoint
            if not self._state_tracker.get_last_incremental_sync():
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
            return True
