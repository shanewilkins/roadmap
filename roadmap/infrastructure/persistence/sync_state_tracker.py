"""Sync state tracking for file synchronization operations.

This module manages sync state metadata for tracking which files have been
synced, when they were last synced, and detecting git conflicts.
"""

import json

from ...shared.logging import get_logger

logger = get_logger(__name__)


class SyncStateTracker:
    """Tracks synchronization state and metadata."""

    def __init__(self, get_connection):
        """Initialize the sync state tracker.

        Args:
            get_connection: Callable that returns a database connection
        """
        self._get_connection = get_connection

    def get_sync_state(self, key: str) -> str | None:
        """Get sync state value by key."""
        conn = self._get_connection()
        row = conn.execute(
            "SELECT value FROM sync_state WHERE key = ?", (key,)
        ).fetchone()
        return row["value"] if row else None

    def set_sync_state(self, key: str, value: str):
        """Set sync state value by key."""
        conn = self._get_connection()
        conn.execute(
            "INSERT OR REPLACE INTO sync_state (key, value) VALUES (?, ?)",
            (key, value),
        )

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

    def update_last_incremental_sync(self, sync_time: str):
        """Update timestamp of last incremental sync."""
        self.set_sync_state("last_incremental_sync", sync_time)

    def update_last_full_rebuild(self, rebuild_time: str):
        """Update timestamp of last full rebuild."""
        self.set_sync_state("last_full_rebuild", rebuild_time)

    def get_last_incremental_sync(self) -> str | None:
        """Get timestamp of last incremental sync."""
        return self.get_sync_state("last_incremental_sync")

    def get_last_full_rebuild(self) -> str | None:
        """Get timestamp of last full rebuild."""
        return self.get_sync_state("last_full_rebuild")

    def mark_conflicts_detected(self, conflict_files: list[str]):
        """Mark that git conflicts have been detected."""
        self.set_sync_state("git_conflicts_detected", "true")
        self.set_sync_state("conflict_files", json.dumps(conflict_files))

    def clear_conflicts(self):
        """Clear conflict markers after resolution."""
        self.set_sync_state("git_conflicts_detected", "false")
        self.set_sync_state("conflict_files", "[]")
