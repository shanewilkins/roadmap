"""Abstract ProjectRepository interface."""

from abc import ABC, abstractmethod

from roadmap.core.domain import Project


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
    def create(self, project: Project) -> Project:
        """Create a new project."""
        pass

    @abstractmethod
    def update(self, project: Project) -> Project:
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
