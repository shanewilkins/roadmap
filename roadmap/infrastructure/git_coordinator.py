"""Git Coordinator - Coordinates git-related operations

Extracted from RoadmapCore to reduce god object complexity.
Provides a focused API for all git integration concerns.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from roadmap.adapters.git.git import GitIntegration
from roadmap.core.domain import Issue
from roadmap.infrastructure.git_integration_ops import GitIntegrationOps

if TYPE_CHECKING:
    from roadmap.infrastructure.core import RoadmapCore


class GitCoordinator:
    """Coordinates all git-related operations."""

    def __init__(self, git_ops: GitIntegrationOps, core: RoadmapCore | None = None):
        """Initialize coordinator with git operations manager.

        Args:
            git_ops: GitIntegrationOps instance
            core: RoadmapCore instance for initialization checks
        """
        self._ops: GitIntegrationOps = git_ops
        self._git: GitIntegration = git_ops.git
        self._core = core

    def get_context(self) -> dict[str, Any]:
        """Get Git repository context information."""
        return self._ops.get_git_context()

    def get_current_user(self) -> str | None:
        """Get current user from Git configuration."""
        return self._ops.get_current_user_from_git()

    def create_issue_with_branch(self, title: str, **kwargs) -> Issue | None:
        """Create an issue and optionally create a Git branch for it."""
        return self._ops.create_issue_with_git_branch(title, **kwargs)

    def link_issue_to_branch(self, issue_id: str) -> bool:
        """Link an issue to the current Git branch."""
        return self._ops.link_issue_to_current_branch(issue_id)

    def get_commits_for_issue(self, issue_id: str, since: str | None = None) -> list:
        """Get Git commits that reference this issue."""
        return self._ops.get_commits_for_issue(issue_id, since)

    def update_issue_from_activity(self, issue_id: str) -> bool:
        """Update issue progress and status based on Git commit activity."""
        return self._ops.update_issue_from_git_activity(issue_id)

    def suggest_branch_name(self, issue_id: str) -> str | None:
        """Suggest a branch name for an issue."""
        return self._ops.suggest_branch_name_for_issue(issue_id)

    def get_branch_linked_issues(self) -> dict[str, list[str]]:
        """Get mapping of branches to their linked issue IDs."""
        return self._ops.get_branch_linked_issues()

    def is_git_repository(self) -> bool:
        """Check if current directory is a git repository."""
        return self._ops.git.is_git_repository()

    def create_branch_for_issue(self, issue: Issue, checkout: bool = True) -> bool:
        """Create a Git branch for an issue.

        Args:
            issue: The Issue object to create a branch for
            checkout: If True, checkout the created branch (default: True)

        Returns:
            True if branch was created successfully, False otherwise
        """
        return self._ops.git.create_branch_for_issue(issue, checkout=checkout)

    @property
    def repo_path(self):
        """Get the repository path (for backward compatibility)."""
        return self._ops.git.repo_path

    def get_repository_info(self) -> dict[str, Any]:
        """Get repository information.

        Returns:
            Dictionary with repository metadata
        """
        return self._git.get_repository_info()

    def get_current_branch(self) -> str | None:
        """Get the current Git branch name.

        Returns:
            Current branch name or None if not in a git repo
        """
        branch = self._git.get_current_branch()
        return branch.name if branch else None
