"""Vanilla Git backend for self-hosting scenarios.

For self-hosted deployments (no remote database), this backend is a no-op.
The sync workflow is:
1. User runs 'roadmap sync' to sync with GitHub API (via github_sync_backend)
2. Sync creates/modifies .roadmap/issues/*.md files
3. User manually runs 'git add' and 'git commit' to persist changes
4. User manually runs 'git push' to push to git remote

This backend does not perform git operations - that's the user's responsibility.
"""

from typing import Any

from roadmap.core.domain.issue import Issue
from roadmap.core.interfaces import (
    SyncConflict,
    SyncReport,
)
from roadmap.core.models.sync_models import (
    SyncIssue,
    SyncMilestone,
    SyncProject,
)
from roadmap.infrastructure.core import RoadmapCore


class VanillaGitSyncBackend:
    """No-op backend for self-hosting scenarios.

    For self-hosted deployments without a remote database, this backend
    delegates all operations to the user. The user is responsible for:
    1. Git add/commit of modified .roadmap/issues/ files
    2. Git push to sync with remote

    This backend exists for interface compatibility but does not perform
    any git operations.

    Attributes:
        core: RoadmapCore instance with access to local issues
        config: Configuration dict (unused, kept for interface compatibility)
    """

    def __init__(self, core: RoadmapCore, config: dict[str, Any]):
        """Initialize vanilla git sync backend.

        Args:
            core: RoadmapCore instance
            config: Configuration dict (unused)
        """
        self.core = core
        self.config = config

    def get_backend_name(self) -> str:
        """Get the canonical name of this backend.

        Returns:
            'git' - used as key in Issue.remote_ids dict
        """
        return "git"

    def authenticate(self) -> bool:
        """No-op authentication for self-hosting.

        For self-hosted scenarios without a remote database, authentication
        always succeeds - the user is responsible for git operations.

        Returns:
            Always True (no remote auth needed)
        """
        return True

    def get_issues(self) -> dict[str, SyncIssue]:
        """No-op: Get issues from remote.

        For self-hosting without a remote database, always returns empty dict.
        The user is responsible for syncing via git operations.

        Returns:
            Empty dict (no remote issues in self-hosted scenario)
        """
        return {}

    def push_issue(self, local_issue: Issue) -> bool:
        """No-op: Push a single issue.

        For self-hosting, the user is responsible for git operations.

        Args:
            local_issue: The Issue object (unused)

        Returns:
            True (no-op succeeds)
        """
        return True

    def push_issues(self, local_issues: list[Issue]) -> SyncReport:
        """No-op: Push multiple issues.

        For self-hosting, the user is responsible for git operations.

        Args:
            local_issues: List of Issue objects (unused)

        Returns:
            Empty SyncReport (no-op)
        """
        return SyncReport()

    def pull_issues(self, issue_ids: list[str]) -> SyncReport:
        """No-op: Pull specified remote issues.

        For self-hosting, the user is responsible for git operations.

        Args:
            issue_ids: List of issue IDs to pull (unused)

        Returns:
            Empty SyncReport (no-op)
        """
        return SyncReport()

    def pull_issue(self, issue_id: str) -> bool:
        """No-op: Pull a single issue.

        For self-hosting, the user is responsible for git operations.

        Args:
            issue_id: The issue ID (unused)

        Returns:
            True (no-op succeeds)
        """
        return True

    def get_conflict_resolution_options(self, conflict: SyncConflict) -> list[str]:
        """Get available resolution strategies.

        For self-hosting, no conflict resolution options (no remote to conflict with).

        Args:
            conflict: The SyncConflict (unused)

        Returns:
            Empty list (no remote database)
        """
        return []

    def resolve_conflict(self, conflict: SyncConflict, resolution: str) -> bool:
        """No-op: Resolve a conflict.

        For self-hosting, no conflicts can occur (no remote database).

        Args:
            conflict: The SyncConflict (unused)
            resolution: The resolution strategy (unused)

        Returns:
            True (no-op succeeds)
        """
        return True

    def get_milestones(self) -> dict[str, SyncMilestone]:
        """No-op: Get milestones from remote.

        For self-hosting without a remote database, always returns empty dict.

        Returns:
            Empty dict (no remote milestones in self-hosted scenario)
        """
        return {}

    def get_projects(self) -> dict[str, SyncProject]:
        """No-op: Get projects from remote.

        For self-hosting without a remote database, always returns empty dict.

        Returns:
            Empty dict (no remote projects in self-hosted scenario)
        """
        return {}
