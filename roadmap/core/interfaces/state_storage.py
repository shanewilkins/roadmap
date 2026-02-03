"""State manager interface for sync state operations.

Defines contract for managing sync state without importing storage implementations.
Breaks circular dependencies between core services and persistence layer.
"""

from abc import ABC, abstractmethod

from roadmap.core.services.sync.sync_state import SyncState


class SyncStateStorageInterface(ABC):
    """Contract for sync state persistence operations."""

    @abstractmethod
    def load_sync_state(self) -> SyncState | None:
        """Load the current sync state.

        Returns:
            SyncState object or None if not found
        """
        pass

    @abstractmethod
    def save_sync_state(self, state: SyncState) -> bool:
        """Save sync state to storage.

        Args:
            state: SyncState object to save

        Returns:
            True if successful, False otherwise
        """
        pass

    @abstractmethod
    def clear_sync_state(self) -> bool:
        """Clear the sync state.

        Returns:
            True if successful, False otherwise
        """
        pass

    @abstractmethod
    def get_last_sync_time(self) -> str | None:
        """Get the last sync timestamp.

        Returns:
            ISO format datetime string or None if never synced
        """
        pass

    @abstractmethod
    def update_last_sync_time(self, timestamp: str) -> bool:
        """Update the last sync timestamp.

        Args:
            timestamp: ISO format datetime string

        Returns:
            True if successful, False otherwise
        """
        pass
