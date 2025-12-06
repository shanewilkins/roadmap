"""Project Operations Module - Handles all project-related CRUD operations.

This module encapsulates project management responsibilities extracted from RoadmapCore,
including creating, reading, updating, and managing projects.

Responsibilities:
- Project CRUD operations (list, get, save, update)
"""

from roadmap.core.domain import Project
from roadmap.core.services import ProjectService


class ProjectOperations:
    """Manager for project-related operations."""

    def __init__(self, project_service: ProjectService):
        """Initialize project operations manager.

        Args:
            project_service: The ProjectService instance for database operations
        """
        self.project_service = project_service

    def list_projects(self) -> list[Project]:
        """List all projects.

        Returns:
            List of Project objects
        """
        return self.project_service.list_projects()

    def get_project(self, project_id: str) -> Project | None:
        """Get a specific project by ID.

        Args:
            project_id: The project ID to retrieve

        Returns:
            Project object if found, None otherwise
        """
        return self.project_service.get_project(project_id)

    def save_project(self, project: Project) -> bool:
        """Save an updated project to disk.

        Args:
            project: The Project object to save

        Returns:
            True if save successful, False otherwise
        """
        return self.project_service.save_project(project)

    def update_project(self, project_id: str, **updates) -> Project | None:
        """Update a project with the given fields.

        Args:
            project_id: Project identifier
            **updates: Fields to update (name, description, status, priority, etc.)

        Returns:
            Updated Project object if successful, None if not found
        """
        return self.project_service.update_project(project_id, **updates)
