"""Project management orchestrator.

Handles project creation, tracking, and resource coordination.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ...domain import Project

if TYPE_CHECKING:
    from ...application.services import ProjectService


class ProjectOrchestrator:
    """Orchestrates project management operations."""

    def __init__(self, project_service: ProjectService):
        """Initialize with project service.

        Args:
            project_service: ProjectService instance
        """
        self.project_service = project_service

    def create(
        self,
        name: str,
        description: str = "",
        milestones: list[str] | None = None,
    ) -> Project:
        """Create a new project.

        Args:
            name: Project name
            description: Project description
            milestones: Associated milestone names

        Returns:
            Created Project object
        """
        return self.project_service.create_project(
            name=name,
            description=description,
            milestones=milestones or [],
        )

    def list(self) -> list[Project]:
        """List all projects.

        Returns:
            List of Project objects
        """
        return self.project_service.list_projects()

    def get(self, project_id: str) -> Project | None:
        """Get a specific project by ID.

        Args:
            project_id: Project identifier

        Returns:
            Project object if found, None otherwise
        """
        return self.project_service.get_project(project_id)

    def update(self, project_id: str, **updates) -> Project | None:
        """Update a project with the given fields.

        Args:
            project_id: Project identifier
            **updates: Fields to update (name, description, status, etc.)

        Returns:
            Updated Project object if found, None otherwise
        """
        return self.project_service.update_project(project_id, **updates)

    def save(self, project: Project) -> bool:
        """Save an updated project to disk.

        Args:
            project: Project object to save

        Returns:
            True if save succeeded, False otherwise
        """
        return self.project_service.save_project(project)

    def delete(self, project_id: str) -> bool:
        """Delete a project.

        Args:
            project_id: Project identifier

        Returns:
            True if deleted, False if not found
        """
        return self.project_service.delete_project(project_id)
