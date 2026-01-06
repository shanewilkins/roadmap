"""Abstract MilestoneRepository interface."""

import builtins
from abc import ABC, abstractmethod

from roadmap.core.domain import Milestone


class MilestoneRepository(ABC):
    """Abstract repository for milestone persistence and retrieval.

    Implementations handle:
    - Milestone data storage
    - Progress tracking
    - Status management
    - Synchronization

    Core services use this interface and don't care about implementation.
    """

    @abstractmethod
    def get(self, milestone_id: str) -> Milestone | None:
        """Retrieve a single milestone by ID."""
        pass

    @abstractmethod
    def list(self, project_id: str | None = None) -> list[Milestone]:
        """List milestones, optionally filtered by project."""
        pass

    @abstractmethod
    def create(self, milestone: Milestone) -> Milestone:
        """Create a new milestone."""
        pass

    @abstractmethod
    def update(self, milestone: Milestone) -> Milestone:
        """Update an existing milestone."""
        pass

    @abstractmethod
    def delete(self, milestone_id: str) -> bool:
        """Delete a milestone by ID."""
        pass

    @abstractmethod
    def get_progress(self, milestone_id: str) -> dict:
        """Get progress metrics for a milestone."""
        pass

    @abstractmethod
    def find_by_status(self, status: str) -> builtins.list[Milestone]:
        """Find milestones by status."""
        pass

    @abstractmethod
    def close(self, milestone_id: str) -> Milestone:
        """Close/complete a milestone."""
        pass
