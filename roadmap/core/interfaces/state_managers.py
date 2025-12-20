"""Protocol definitions for focused state managers.

Splits the monolithic StateManager into focused, single-responsibility
interfaces for better testability and maintainability.
"""

from typing import Any, Protocol


class ProjectStateManager(Protocol):
    """Protocol for project state persistence."""

    def create_project(self, project_data: dict[str, Any]) -> str:
        """Create a new project."""
        ...

    def get_project(self, project_id: str) -> dict[str, Any] | None:
        """Get project by ID."""
        ...

    def list_projects(self) -> list[dict[str, Any]]:
        """List all projects."""
        ...

    def update_project(self, project_id: str, updates: dict[str, Any]) -> bool:
        """Update project."""
        ...

    def delete_project(self, project_id: str) -> bool:
        """Delete project."""
        ...

    def mark_project_archived(self, project_id: str, archived: bool = True) -> bool:
        """Mark a project as archived or unarchived."""
        ...


class MilestoneStateManager(Protocol):
    """Protocol for milestone state persistence."""

    def create_milestone(self, milestone_data: dict[str, Any]) -> str:
        """Create a new milestone."""
        ...

    def get_milestone(self, milestone_id: str) -> dict[str, Any] | None:
        """Get milestone by ID."""
        ...

    def update_milestone(self, milestone_id: str, updates: dict[str, Any]) -> bool:
        """Update milestone."""
        ...

    def mark_milestone_archived(self, milestone_id: str, archived: bool = True) -> bool:
        """Mark a milestone as archived or unarchived."""
        ...


class IssueStateManager(Protocol):
    """Protocol for issue state persistence."""

    def create_issue(self, issue_data: dict[str, Any]) -> str:
        """Create a new issue."""
        ...

    def get_issue(self, issue_id: str) -> dict[str, Any] | None:
        """Get issue by ID."""
        ...

    def update_issue(self, issue_id: str, updates: dict[str, Any]) -> bool:
        """Update issue."""
        ...

    def delete_issue(self, issue_id: str) -> bool:
        """Delete issue."""
        ...

    def mark_issue_archived(self, issue_id: str, archived: bool = True) -> bool:
        """Mark an issue as archived or unarchived."""
        ...


class SyncStateManager(Protocol):
    """Protocol for sync state persistence."""

    def get_sync_state(self, key: str) -> str | None:
        """Get sync state value."""
        ...

    def set_sync_state(self, key: str, value: str):
        """Set sync state value."""
        ...


class QueryStateManager(Protocol):
    """Protocol for complex query operations on state."""

    def get_all_issues(self) -> list[dict[str, Any]]:
        """Get all issues from database."""
        ...

    def get_all_milestones(self) -> list[dict[str, Any]]:
        """Get all milestones from database."""
        ...

    def get_milestone_progress(self, milestone_name: str) -> dict[str, int]:
        """Get progress stats for a milestone."""
        ...

    def get_issues_by_status(self) -> dict[str, int]:
        """Get issue counts by status."""
        ...
