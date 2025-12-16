"""Project storage operations."""

from typing import Any

from roadmap.common.errors import OperationType, safe_operation
from roadmap.common.logging import get_logger

from ..repositories import ProjectRepository

logger = get_logger(__name__)


class ProjectStorage:
    """Handles project CRUD operations."""

    def __init__(self, project_repo: ProjectRepository):
        """Initialize project storage.

        Args:
            project_repo: ProjectRepository instance for data access
        """
        self._project_repo = project_repo
        logger.debug("ProjectStorage initialized")

    @safe_operation(OperationType.CREATE, "Project", include_traceback=True)
    def create(self, project_data: dict[str, Any]) -> str:
        """Create a new project.

        Args:
            project_data: Project data dictionary

        Returns:
            str: ID of created project
        """
        logger.debug("Creating project", keys=list(project_data.keys()))
        return self._project_repo.create(project_data)

    def get(self, project_id: str) -> dict[str, Any] | None:
        """Get project by ID.

        Args:
            project_id: Project identifier

        Returns:
            dict: Project data or None if not found
        """
        logger.debug("Getting project", project_id=project_id)
        return self._project_repo.get(project_id)

    def list_all(self) -> list[dict[str, Any]]:
        """List all projects.

        Returns:
            list: List of project data dictionaries
        """
        logger.debug("Listing all projects")
        return self._project_repo.list_all()

    @safe_operation(OperationType.UPDATE, "Project", include_traceback=True)
    def update(self, project_id: str, updates: dict[str, Any]) -> bool:
        """Update project.

        Args:
            project_id: Project identifier
            updates: Dictionary of fields to update

        Returns:
            bool: True if update successful
        """
        logger.debug(
            "Updating project", project_id=project_id, keys=list(updates.keys())
        )
        return self._project_repo.update(project_id, updates)

    @safe_operation(OperationType.DELETE, "Project", include_traceback=True)
    def delete(self, project_id: str) -> bool:
        """Delete project and all related data.

        Args:
            project_id: Project identifier

        Returns:
            bool: True if deletion successful
        """
        logger.debug("Deleting project", project_id=project_id)
        return self._project_repo.delete(project_id)

    @safe_operation(OperationType.UPDATE, "Project")
    def mark_archived(self, project_id: str, archived: bool = True) -> bool:
        """Mark a project as archived or unarchived.

        Args:
            project_id: Project identifier
            archived: Whether to archive (True) or unarchive (False)

        Returns:
            bool: True if operation successful
        """
        logger.debug(
            "Marking project archived", project_id=project_id, archived=archived
        )
        return self._project_repo.mark_archived(project_id, archived)
