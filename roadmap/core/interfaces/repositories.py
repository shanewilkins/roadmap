"""Abstract repository interfaces for persistence.

These interfaces define contracts for data access and external integrations.
Implementations are in the infrastructure layer.

This follows the Dependency Inversion Principle:
- Core services depend on these abstractions
- Infrastructure implements these abstractions
- Services are decoupled from implementation details
"""

import builtins
from abc import ABC, abstractmethod

from roadmap.core.domain import Issue, Milestone, Project


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


class ProjectRepository(ABC):
    """Abstract repository for project persistence and retrieval.

    Implementations handle:
    - Project data storage
    - Configuration management
    - File system operations
    - Synchronization

    Core services use this interface and don't care about implementation.
    """

    @abstractmethod
    def get(self, project_id: str) -> Project | None:
        """Retrieve a single project by ID."""
        pass

    @abstractmethod
    def list(self) -> list[Project]:
        """List all projects."""
        pass

    @abstractmethod
    def get_current(self) -> Project | None:
        """Get the currently active project."""
        pass

    @abstractmethod
    def create(self, project: Project) -> Project:  # noqa: F841
        """Create a new project."""
        pass

    @abstractmethod
    def update(self, project: Project) -> Project:  # noqa: F841
        """Update an existing project."""
        pass

    @abstractmethod
    def delete(self, project_id: str) -> bool:
        """Delete a project by ID."""
        pass

    @abstractmethod
    def get_status(self, project_id: str) -> dict:
        """Get project status/health information."""
        pass

    @abstractmethod
    def validate(self, project_id: str) -> bool:
        """Validate project structure and integrity."""
        pass
