"""Repository abstraction layer for persistence.

This module defines protocols (interfaces) for data persistence operations.
Implementations can be swapped (YAML, JSON, database) without affecting services.
"""

from typing import Protocol

from roadmap.core.domain.issue import Issue
from roadmap.core.domain.milestone import Milestone
from roadmap.core.domain.project import Project


class IssueRepository(Protocol):
    """Protocol for issue data persistence."""

    def get(self, issue_id: str) -> Issue | None:
        """Get a specific issue by ID.

        Args:
            issue_id: Issue identifier

        Returns:
            Issue object if found, None otherwise
        """
        ...

    def list(
        self, milestone: str | None = None, status: str | None = None
    ) -> list[Issue]:
        """List issues with optional filtering.

        Args:
            milestone: Optional milestone filter
            status: Optional status filter

        Returns:
            List of Issue objects matching filters
        """
        ...

    def save(self, issue: Issue) -> None:
        """Save/create an issue.

        Args:
            issue: Issue object to save
        """
        ...

    def update(self, issue_id: str, updates: dict) -> Issue | None:
        """Update specific fields of an issue.

        Args:
            issue_id: Issue identifier
            updates: Dictionary of field updates

        Returns:
            Updated Issue object if found, None otherwise
        """
        ...

    def delete(self, issue_id: str) -> bool:
        """Delete an issue.

        Args:
            issue_id: Issue identifier

        Returns:
            True if deleted, False if not found
        """
        ...


class MilestoneRepository(Protocol):
    """Protocol for milestone data persistence."""

    def get(self, milestone_id: str) -> Milestone | None:
        """Get a specific milestone by ID or name.

        Args:
            milestone_id: Milestone identifier or name

        Returns:
            Milestone object if found, None otherwise
        """
        ...

    def list(self) -> list[Milestone]:
        """List all milestones.

        Returns:
            List of all Milestone objects
        """
        ...

    def save(self, milestone: Milestone) -> None:
        """Save/create a milestone.

        Args:
            milestone: Milestone object to save
        """
        ...

    def update(self, milestone_id: str, updates: dict) -> Milestone | None:
        """Update specific fields of a milestone.

        Args:
            milestone_id: Milestone identifier
            updates: Dictionary of field updates

        Returns:
            Updated Milestone object if found, None otherwise
        """
        ...

    def delete(self, milestone_id: str) -> bool:
        """Delete a milestone.

        Args:
            milestone_id: Milestone identifier

        Returns:
            True if deleted, False if not found
        """
        ...


class ProjectRepository(Protocol):
    """Protocol for project data persistence."""

    def get(self, project_id: str) -> Project | None:
        """Get a specific project by ID.

        Args:
            project_id: Project identifier

        Returns:
            Project object if found, None otherwise
        """
        ...

    def list(self) -> list[Project]:
        """List all projects.

        Returns:
            List of all Project objects
        """
        ...

    def save(self, project: Project) -> None:
        """Save/create a project.

        Args:
            project: Project object to save
        """
        ...

    def update(self, project_id: str, updates: dict) -> Project | None:
        """Update specific fields of a project.

        Args:
            project_id: Project identifier
            updates: Dictionary of field updates

        Returns:
            Updated Project object if found, None otherwise
        """
        ...

    def delete(self, project_id: str) -> bool:
        """Delete a project.

        Args:
            project_id: Project identifier

        Returns:
            True if deleted, False if not found
        """
        ...
