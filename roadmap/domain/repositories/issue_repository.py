"""Abstract IssueRepository interface."""

import builtins
from abc import ABC, abstractmethod

from roadmap.core.domain import Issue


class IssueRepository(ABC):
    """Abstract repository for issue persistence and retrieval.

    Implementations handle:
    - File-based storage
    - Database operations
    - Git integration
    - Synchronization

    Core services use this interface and don't care about implementation.
    """

    @abstractmethod
    def get(self, issue_id: str) -> Issue | None:
        """Retrieve a single issue by ID."""
        pass

    @abstractmethod
    def list(self, _filters: dict | None = None) -> list[Issue]:
        """List issues with optional filtering."""
        pass

    @abstractmethod
    def create(self, issue: Issue) -> Issue:
        """Create a new issue."""
        pass

    @abstractmethod
    def update(self, issue: Issue) -> Issue:
        """Update an existing issue."""
        pass

    @abstractmethod
    def delete(self, issue_id: str) -> bool:
        """Delete an issue by ID."""
        pass

    @abstractmethod
    def bulk_update(self, issues: builtins.list[Issue]) -> builtins.list[Issue]:
        """Update multiple issues at once."""
        pass

    @abstractmethod
    def find_by_milestone(self, milestone_id: str) -> builtins.list[Issue]:
        """Find all issues for a milestone."""
        pass

    @abstractmethod
    def find_by_status(self, status: str) -> builtins.list[Issue]:
        """Find issues by status."""
        pass
