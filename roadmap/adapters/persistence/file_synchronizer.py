"""File synchronization manager for syncing .roadmap files to database.

This module coordinates synchronization of markdown files in the .roadmap directory
with the SQLite database. It delegates to focused managers for parsing, sync state,
and entity-specific coordination.
"""

from pathlib import Path
from typing import Any

from roadmap.adapters.persistence.file_parser import FileParser
from roadmap.adapters.persistence.sync_orchestrator import SyncOrchestrator
from roadmap.common.logging import get_logger

logger = get_logger(__name__)


class FileSynchronizer:
    """Manages synchronization of .roadmap files to the database.

    Delegates to specialized managers for parsing, sync state tracking,
    and entity-specific synchronization coordination.
    """

    def __init__(self, get_connection, transaction_context):
        """Initialize the file synchronizer.

        Args:
            get_connection: Callable that returns a database connection
            transaction_context: Context manager for transactions
        """
        self._orchestrator = SyncOrchestrator(get_connection, transaction_context)
        self._parser = FileParser()
        self._get_connection = get_connection
        self._transaction = transaction_context

    # Backward compatibility shims for existing tests
    def _calculate_file_hash(self, file_path: Path) -> str:
        """DEPRECATED: Use FileParser.calculate_file_hash instead."""
        return self._parser.calculate_file_hash(file_path)

    def _parse_yaml_frontmatter(self, file_path: Path) -> dict[str, Any]:
        """DEPRECATED: Use FileParser.parse_yaml_frontmatter instead."""
        return self._parser.parse_yaml_frontmatter(file_path)

    def get_file_sync_status(self, file_path: str) -> dict[str, Any] | None:
        """Get sync status for a file."""
        conn = self._get_connection()
        row = conn.execute(
            """
            SELECT file_path, content_hash, file_size, last_modified
            FROM file_sync_state WHERE file_path = ?
        """,
            (file_path,),
        ).fetchone()
        return dict(row) if row else None

    def update_file_sync_status(
        self, file_path: str, content_hash: str, file_size: int, last_modified: Any
    ) -> None:
        """Update sync status for a file."""
        with self._transaction() as conn:
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

            current_hash = self._parser.calculate_file_hash(file_path)
            sync_status = self.get_file_sync_status(str(file_path))

            if not sync_status:
                return True

            return current_hash != sync_status["content_hash"]

        except Exception as e:
            logger.error(f"Failed to check file changes for {file_path}", error=str(e))
            return True

    def _get_default_project_id(self) -> str | None:
        """DEPRECATED: Use entity coordinators instead."""
        try:
            with self._transaction() as conn:
                result = conn.execute("SELECT id FROM projects LIMIT 1").fetchone()
                return result[0] if result else None
        except Exception as e:
            logger.error("Failed to get default project ID", error=str(e))
            return None

    def _get_milestone_id_by_name(self, milestone_name: str) -> str | None:
        """DEPRECATED: Use entity coordinators instead."""
        try:
            with self._transaction() as conn:
                result = conn.execute(
                    "SELECT id FROM milestones WHERE title = ?", (milestone_name,)
                ).fetchone()
                return result[0] if result else None
        except Exception as e:
            logger.warning(f"Failed to find milestone '{milestone_name}'", error=str(e))
            return None

    def sync_issue_file(self, file_path: Path) -> bool:
        """DEPRECATED: Use entity coordinators instead."""
        return self._orchestrator._issue_sync.sync_issue_file(file_path)

    def sync_milestone_file(self, file_path: Path) -> bool:
        """DEPRECATED: Use entity coordinators instead."""
        return self._orchestrator._milestone_sync.sync_milestone_file(file_path)

    def sync_project_file(self, file_path: Path) -> bool:
        """DEPRECATED: Use entity coordinators instead."""
        return self._orchestrator._project_sync.sync_project_file(file_path)

    def sync_directory_incremental(self, roadmap_dir: Path) -> dict[str, Any]:
        """Incrementally sync .roadmap directory to database.

        Only syncs files that have changed since last sync.
        """
        return self._orchestrator.sync_directory_incremental(roadmap_dir)

    def full_rebuild_from_git(self, roadmap_dir: Path) -> dict[str, Any]:
        """Full rebuild of database from git files.

        Clears all data and rebuilds from scratch.
        """
        return self._orchestrator.full_rebuild_from_git(roadmap_dir)

    def should_do_full_rebuild(self, roadmap_dir: Path, threshold: int = 50) -> bool:
        """Determine if full rebuild is needed vs incremental sync.

        Args:
            roadmap_dir: Path to .roadmap directory
            threshold: Percentage of files changed before triggering rebuild (default 50%)
        """
        return self._orchestrator.should_do_full_rebuild(roadmap_dir, threshold)
