"""Project Coordinator - Coordinates project-related operations

Extracted from RoadmapCore to reduce god object complexity.
Provides a focused API for all project-related concerns.
"""

from __future__ import annotations

from roadmap.core.domain import Project
from roadmap.infrastructure.project_operations import ProjectOperations


class ProjectCoordinator:
    """Coordinates all project-related operations."""

    def __init__(self, project_ops: ProjectOperations):
        """Initialize coordinator with project operations manager.

        Args:
            project_ops: ProjectOperations instance
        """
        self._ops = project_ops

    def list(self) -> list[Project]:
        """List all projects."""
        return self._ops.list_projects()

    def get(self, project_id: str) -> Project | None:
        """Get a specific project by ID."""
        return self._ops.get_project(project_id)

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
