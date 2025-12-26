"""Project Coordinator - Coordinates project-related operations

Extracted from RoadmapCore to reduce god object complexity.
Provides a focused API for all project-related concerns.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from roadmap.core.domain import Project
from roadmap.infrastructure.project_operations import ProjectOperations

if TYPE_CHECKING:
    from roadmap.infrastructure.core import RoadmapCore


class ProjectCoordinator:
    """Coordinates all project-related operations."""

    def __init__(self, project_ops: ProjectOperations, core: RoadmapCore | None = None):
        """Initialize coordinator with project operations manager.

        Args:
            project_ops: ProjectOperations instance
            core: RoadmapCore instance for initialization checks
        """
        self._ops = project_ops
        self._core = core

    def list(self) -> list[Project]:
        """List all projects."""
        return self._ops.list_projects()

    def get(self, project_id: str) -> Project | None:
        """Get a specific project by ID or name.

        Tries to find project by ID first, then by name as fallback.
        """
        # Try direct ID lookup first
        project = self._ops.get_project(project_id)
        if project:
            return project

        # Fallback: try to find by name
        for project in self._ops.list_projects():
            if project.name.lower() == project_id.lower():
                return project

        return None

    def create(
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
        return self._ops.create_project(
            name=name,
            description=description,
            milestones=milestones or [],
            status=status,
        )

    def save(self, project: Project) -> bool:
        """Save an updated project to disk."""
        return self._ops.save_project(project)

    def update(self, project_id: str, **updates) -> Project | None:
        """Update a project with the given fields.

        Args:
            project_id: Project identifier
            **updates: Fields to update (name, description, status, priority, etc.)

        Returns:
            Updated Project object if successful, None if not found
        """
        return self._ops.update_project(project_id, **updates)

    def delete(self, project_id: str) -> bool:
        """Delete a project.

        Args:
            project_id: Project identifier

        Returns:
            True if deletion successful, False otherwise
        """
        return self._ops.delete_project(project_id)

    def complete(self, project_id: str) -> Project | None:
        """Mark a project as completed.

        Args:
            project_id: Project identifier

        Returns:
            Updated Project object if successful, None if not found
        """
        return self._ops.complete_project(project_id)
