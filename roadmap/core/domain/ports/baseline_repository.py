"""Port for managing baseline state (canonical sync point)."""

from abc import ABC, abstractmethod

from roadmap.core.services.sync.sync_state import SyncState


class IBaselineRepository(ABC):
    """Port for managing baseline state (canonical sync point)."""

    @abstractmethod
    def load(self) -> SyncState | None:
        """Load current baseline. Returns None if not set."""
        pass

    @abstractmethod
    def save(self, baseline: SyncState) -> None:
        """Save baseline state."""
        pass

    @abstractmethod
    def clear(self) -> None:
        """Clear baseline (reset sync state)."""
        pass
