"""Project Operations Module - Handles all project-related CRUD operations.

This module encapsulates project management responsibilities extracted from RoadmapCore,
including creating, reading, updating, and managing projects.

Responsibilities:
- Project CRUD operations (list, get, save, update)
"""

from roadmap.common.errors.error_standards import OperationType, safe_operation
from roadmap.common.logging import get_logger
from roadmap.core.domain import Project
from roadmap.core.services import ProjectService

logger = get_logger(__name__)


class ProjectOperations:
    """Manager for project-related operations."""

    def __init__(self, project_service: ProjectService):
        """Initialize project operations manager.

        Args:
            project_service: The ProjectService instance for database operations
        """
        self.project_service = project_service

    @safe_operation(OperationType.READ, "Project")
    def list_projects(self) -> list[Project]:
        """List all projects.

        Returns:
            List of Project objects
        """
        logger.info("listing_projects")
        return self.project_service.list_projects()

    @safe_operation(OperationType.READ, "Project")
    def get_project(self, project_id: str) -> Project | None:
        """Get a specific project by ID.

        Args:
            project_id: The project ID to retrieve

        Returns:
            Project object if found, None otherwise
        """
        logger.info("getting_project", project_id=project_id)
        return self.project_service.get_project(project_id)

    @safe_operation(OperationType.CREATE, "Project", include_traceback=True)
    def create_project(
        self,
        name: str,
        description: str = "",
        milestones: list[str] | None = None,
        status: str | None = None,
    ) -> Project:
        """Create a new project.

        Args:
            name: Project name
            description: Project description
            milestones: List of milestone names (optional)
            status: Project status (optional)

        Returns:
            Created Project object
        """
        logger.info(
            "creating_project",
            project_name=name,
            has_description=description is not None,
            milestone_count=len(milestones or []),
            status=status,
        )
        return self.project_service.create_project(
            name=name,
            description=description,
            milestones=milestones or [],
            status=status,
        )

    @safe_operation(OperationType.UPDATE, "Project")
    def save_project(self, project: Project) -> bool:
        """Save an updated project to disk.

        Args:
            project: The Project object to save

        Returns:
            True if save successful, False otherwise
        """
        logger.info(
            "saving_project",
            project_id=project.id,
            project_name=project.name,
        )
        return self.project_service.save_project(project)

    @safe_operation(OperationType.UPDATE, "Project")
    def update_project(self, project_id: str, **updates) -> Project | None:
        """Update a project with the given fields.

        Args:
            project_id: Project identifier
            **updates: Fields to update (name, description, status, priority, etc.)

        Returns:
            Updated Project object if successful, None if not found
        """
        logger.info(
            "updating_project",
            project_id=project_id,
            update_fields=list(updates.keys()),
        )
        return self.project_service.update_project(project_id, **updates)

    @safe_operation(OperationType.DELETE, "Project", include_traceback=True)
    def delete_project(self, project_id: str) -> bool:
        """Delete a project.

        Args:
            project_id: Project identifier

        Returns:
            True if deletion successful, False otherwise
        """
        logger.info("deleting_project", project_id=project_id)
        return self.project_service.delete_project(project_id)

    @safe_operation(OperationType.UPDATE, "Project")
    def complete_project(self, project_id: str) -> Project | None:
        """Mark a project as completed.

        Args:
            project_id: Project identifier

        Returns:
            Updated Project object if successful, None if not found
        """
        logger.info("completing_project", project_id=project_id)
        return self.project_service.complete_project(project_id)
