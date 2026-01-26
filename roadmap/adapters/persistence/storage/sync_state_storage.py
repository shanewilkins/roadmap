"""Sync state and file synchronization operations."""

from pathlib import Path
from typing import Any

from roadmap.common.errors import OperationType, safe_operation
from roadmap.common.logging import get_logger

from ..file_synchronizer import FileSynchronizer
from ..repositories import SyncStateRepository

logger = get_logger(__name__)


class SyncStateStorage:
    """Handles sync state tracking and file synchronization operations."""

    def __init__(
        self,
        sync_state_repo: SyncStateRepository,
        file_synchronizer: FileSynchronizer,
    ):
        """Initialize sync state storage.

        Args:
            sync_state_repo: SyncStateRepository instance for sync state persistence
            file_synchronizer: FileSynchronizer instance for file operations
        """
        self._sync_state_repo = sync_state_repo
        self._file_synchronizer = file_synchronizer
        logger.debug("sync_state_storage_initialized")

    # Sync state operations
    def get_sync_state(self, key: str) -> str | None:
        """Get sync state value.

        Args:
            key: State key identifier

        Returns:
            str: State value or None if not found
        """
        logger.debug("Getting sync state", key=key)
        return self._sync_state_repo.get(key)

    def set_sync_state(self, key: str, value: str):
        """Set sync state value.

        Args:
            key: State key identifier
            value: State value to store
        """
        logger.debug("Setting sync state", key=key, value_length=len(value))
        self._sync_state_repo.set(key, value)

    # File sync operations
    def get_file_sync_status(self, file_path: str) -> dict[str, Any] | None:
        """Get sync status for a file.

        Args:
            file_path: Path to file

        Returns:
            dict: Sync status data or None if not found
        """
        logger.debug("Getting file sync status", file_path=file_path)
        return self._file_synchronizer.get_file_sync_status(file_path)

    @safe_operation(OperationType.UPDATE, "FileSync")
    def update_file_sync_status(
        self, file_path: str, content_hash: str, file_size: int, last_modified: Any
    ):
        """Update sync status for a file.

        Args:
            file_path: Path to file
            content_hash: Hash of file content
            file_size: Size of file in bytes
            last_modified: Last modification timestamp
        """
        logger.debug(
            "Updating file sync status", file_path=file_path, file_size=file_size
        )
        self._file_synchronizer.update_file_sync_status(
            file_path, content_hash, file_size, last_modified
        )

    def has_file_changed(self, file_path: Path) -> bool:
        """Check if file has changed since last sync.

        Args:
            file_path: Path to file

        Returns:
            bool: True if file has changed
        """
        result = self._file_synchronizer.has_file_changed(file_path)
        logger.debug("File change check", file_path=str(file_path), changed=result)
        return result

    @safe_operation(OperationType.SYNC, "Directory", retryable=True, max_retries=2)
    def sync_directory_incremental(self, roadmap_dir: Path) -> dict[str, Any]:
        """Incrementally sync .roadmap directory to database.

        Args:
            roadmap_dir: Path to .roadmap directory

        Returns:
            dict: Sync results with files_synced count
        """
        logger.info("Incremental sync started", roadmap_dir=str(roadmap_dir))
        result = self._file_synchronizer.sync_directory_incremental(roadmap_dir)
        logger.info(
            "Incremental sync completed",
            roadmap_dir=str(roadmap_dir),
            files_synced=result.get("files_synced", 0),
        )
        return result

    @safe_operation(OperationType.SYNC, "Directory", retryable=True, max_retries=2)
    def full_rebuild_from_git(self, roadmap_dir: Path) -> dict[str, Any]:
        """Full rebuild of database from git files.

        Args:
            roadmap_dir: Path to .roadmap directory

        Returns:
            dict: Rebuild results with files_processed count
        """
        logger.info("Full rebuild from git started", roadmap_dir=str(roadmap_dir))
        result = self._file_synchronizer.full_rebuild_from_git(roadmap_dir)
        logger.info(
            "Full rebuild completed",
            roadmap_dir=str(roadmap_dir),
            files_processed=result.get("files_processed", 0),
        )
        return result

    def should_do_full_rebuild(self, roadmap_dir: Path, threshold: int = 50) -> bool:
        """Determine if full rebuild is needed vs incremental sync.

        Args:
            roadmap_dir: Path to .roadmap directory
            threshold: Number of changed files before full rebuild recommended

        Returns:
            bool: True if full rebuild is recommended
        """
        result = self._file_synchronizer.should_do_full_rebuild(roadmap_dir, threshold)
        logger.debug("Full rebuild check", roadmap_dir=str(roadmap_dir), result=result)
        return result

    @safe_operation(OperationType.SYNC, "Directory")
    def smart_sync(self, roadmap_dir: Path | None = None) -> dict[str, Any]:
        """Smart sync that chooses between incremental and full rebuild.

        Args:
            roadmap_dir: Path to .roadmap directory. Defaults to .roadmap in cwd

        Returns:
            dict: Sync results
        """
        if roadmap_dir is None:
            roadmap_dir = Path.cwd() / ".roadmap"

        logger.info("Smart sync started", roadmap_dir=str(roadmap_dir))

        try:
            if self.should_do_full_rebuild(roadmap_dir):
                logger.info("Choosing full rebuild", roadmap_dir=str(roadmap_dir))
                result = self.full_rebuild_from_git(roadmap_dir)
            else:
                logger.info("Choosing incremental sync", roadmap_dir=str(roadmap_dir))
                result = self.sync_directory_incremental(roadmap_dir)

            logger.info(
                "Smart sync completed",
                roadmap_dir=str(roadmap_dir),
                result_keys=list(result.keys()),
            )
            return result

        except Exception as e:
            logger.error(
                "Smart sync failed",
                roadmap_dir=str(roadmap_dir),
                error=str(e),
                error_type=type(e).__name__,
            )
            return {"error": str(e), "files_failed": 1}

    # File changes checking - needs state manager context
    def has_file_changes(self, state_manager) -> bool:
        """Check if .roadmap/ files have changes since last sync.

        Args:
            state_manager: StateManager instance for database access

        Returns:
            bool: True if changes detected
        """
        from .queries import QueryService

        logger.debug("Checking file changes")
        result = QueryService(state_manager).has_file_changes()
        logger.debug("File changes check completed", has_changes=result)
        return result
