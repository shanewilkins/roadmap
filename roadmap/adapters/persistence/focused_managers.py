"""Focused state manager adapters for StateManager.

These adapters wrap StateManager to provide focused, single-responsibility
interfaces. This allows code to depend on focused protocols instead of the
monolithic StateManager.
"""

from typing import Any

from roadmap.core.interfaces import (
    IssueStateManager,
    MilestoneStateManager,
    ProjectStateManager,
    QueryStateManager,
    SyncStateManager,
)


class FocusedProjectStateManager(ProjectStateManager):
    """Project-focused view of StateManager."""

    def __init__(self, state_manager):
        """Initialize with StateManager instance."""
        self._state_manager = state_manager

    def create_project(self, project_data: dict[str, Any]) -> str:
        """Create a new project."""
        return self._state_manager.create_project(project_data)

    def get_project(self, project_id: str) -> dict[str, Any] | None:
        """Get project by ID."""
        return self._state_manager.get_project(project_id)

    def list_projects(self) -> list[dict[str, Any]]:
        """List all projects."""
        return self._state_manager.list_projects()

    def update_project(self, project_id: str, updates: dict[str, Any]) -> bool:
        """Update project."""
        return self._state_manager.update_project(project_id, updates)

    def delete_project(self, project_id: str) -> bool:
        """Delete project."""
        return self._state_manager.delete_project(project_id)

    def mark_project_archived(self, project_id: str, archived: bool = True) -> bool:
        """Mark a project as archived or unarchived."""
        return self._state_manager.mark_project_archived(project_id, archived)


class FocusedMilestoneStateManager(MilestoneStateManager):
    """Milestone-focused view of StateManager."""

    def __init__(self, state_manager):
        """Initialize with StateManager instance."""
        self._state_manager = state_manager

    def create_milestone(self, milestone_data: dict[str, Any]) -> str:
        """Create a new milestone."""
        return self._state_manager.create_milestone(milestone_data)

    def get_milestone(self, milestone_id: str) -> dict[str, Any] | None:
        """Get milestone by ID."""
        return self._state_manager.get_milestone(milestone_id)

    def update_milestone(self, milestone_id: str, updates: dict[str, Any]) -> bool:
        """Update milestone."""
        return self._state_manager.update_milestone(milestone_id, updates)

    def mark_milestone_archived(self, milestone_id: str, archived: bool = True) -> bool:
        """Mark a milestone as archived or unarchived."""
        return self._state_manager.mark_milestone_archived(milestone_id, archived)


class FocusedIssueStateManager(IssueStateManager):
    """Issue-focused view of StateManager."""

    def __init__(self, state_manager):
        """Initialize with StateManager instance."""
        self._state_manager = state_manager

    def create_issue(self, issue_data: dict[str, Any]) -> str:
        """Create a new issue."""
        return self._state_manager.create_issue(issue_data)

    def get_issue(self, issue_id: str) -> dict[str, Any] | None:
        """Get issue by ID."""
        return self._state_manager.get_issue(issue_id)

    def update_issue(self, issue_id: str, updates: dict[str, Any]) -> bool:
        """Update issue."""
        return self._state_manager.update_issue(issue_id, updates)

    def delete_issue(self, issue_id: str) -> bool:
        """Delete issue."""
        return self._state_manager.delete_issue(issue_id)

    def mark_issue_archived(self, issue_id: str, archived: bool = True) -> bool:
        """Mark an issue as archived or unarchived."""
        return self._state_manager.mark_issue_archived(issue_id, archived)


class FocusedSyncStateManager(SyncStateManager):
    """Sync state-focused view of StateManager."""

    def __init__(self, state_manager):
        """Initialize with StateManager instance."""
        self._state_manager = state_manager

    def get_sync_state(self, key: str) -> str | None:
        """Get sync state value."""
        return self._state_manager.get_sync_state(key)

    def set_sync_state(self, key: str, value: str):
        """Set sync state value."""
        self._state_manager.set_sync_state(key, value)


class FocusedQueryStateManager(QueryStateManager):
    """Query-focused view of StateManager."""

    def __init__(self, state_manager):
        """Initialize with StateManager instance."""
        self._state_manager = state_manager

    def get_all_issues(self) -> list[dict[str, Any]]:
        """Get all issues from database."""
        return self._state_manager.get_all_issues()

    def get_all_milestones(self) -> list[dict[str, Any]]:
        """Get all milestones from database."""
        return self._state_manager.get_all_milestones()

    def get_milestone_progress(self, milestone_name: str) -> dict[str, int]:
        """Get progress stats for a milestone."""
        return self._state_manager.get_milestone_progress(milestone_name)

    def get_issues_by_status(self) -> dict[str, int]:
        """Get issue counts by status."""
        return self._state_manager.get_issues_by_status()
