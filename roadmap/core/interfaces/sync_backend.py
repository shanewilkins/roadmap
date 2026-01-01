"""Protocol definitions for pluggable sync backends.

This module defines the SyncBackendInterface that all sync backends must implement,
enabling support for multiple sync targets (GitHub, vanilla Git, GitLab, etc.)
without coupling the core sync logic to specific implementations.
"""

from typing import Any, Protocol

from roadmap.core.domain.issue import Issue


class SyncConflict:
    """Represents a conflict during sync operations."""

    def __init__(
        self,
        issue_id: str,
        local_version: Issue | None,
        remote_version: dict[str, Any] | None,
        conflict_type: str,
    ):
        """Initialize a sync conflict.

        Args:
            issue_id: ID of the conflicting issue
            local_version: Local Issue object (may be None if deleted remotely)
            remote_version: Remote issue dict (may be None if deleted locally)
            conflict_type: Type of conflict ('both_modified', 'deleted_locally', 'deleted_remotely')
        """
        self.issue_id = issue_id
        self.local_version = local_version
        self.remote_version = remote_version
        self.conflict_type = conflict_type


class SyncReport:
    """Report of sync operations with status and conflicts."""

    def __init__(self):
        """Initialize an empty sync report."""
        self.pushed: list[str] = []  # Issue IDs successfully pushed
        self.pulled: list[str] = []  # Issue IDs successfully pulled
        self.conflicts: list[SyncConflict] = []  # Issues with conflicts
        self.errors: dict[str, str] = {}  # Issue ID -> error message


class SyncBackendInterface(Protocol):
    """Abstract interface for sync backends.

    Defines the contract that all sync backends must implement to enable
    pluggable sync functionality. Allows support for GitHub, vanilla Git,
    GitLab, Jira, and other sync targets.

    All methods should handle errors gracefully and return status/report objects
    rather than raising exceptions, enabling dry-run and conflict resolution
    workflows.
    """

    def authenticate(self) -> bool:
        """Verify credentials and remote connectivity.

        Returns:
            True if authentication succeeds, False otherwise.
            Should not raise exceptions; return False on auth failure.

        Raises:
            No exceptions should be raised. Return False for any auth failure.
        """
        ...

    def get_issues(self) -> dict[str, Any]:
        """Fetch all issues from remote.

        Returns:
            Dictionary mapping issue_id -> issue_data (as dict).
            Empty dict if no issues exist or remote is not available.

        Notes:
            - Should return local/cached copy if remote unavailable
            - Issue data should include at minimum: id, title, status, priority
            - May include additional fields like github_issue, labels, etc.
        """
        ...

    def push_issue(self, local_issue: Issue) -> bool:
        """Push a single local issue to remote.

        Args:
            local_issue: The Issue object to push to remote

        Returns:
            True if push succeeds, False if conflict or error.

        Notes:
            - Should handle conflicts gracefully (return False, not raise)
            - May update local_issue.github_issue or similar fields
            - Idempotent: pushing same issue twice should be safe
        """
        ...

    def push_issues(self, local_issues: list[Issue]) -> SyncReport:
        """Push multiple local issues to remote.

        Args:
            local_issues: List of Issue objects to push

        Returns:
            SyncReport with pushed, conflicts, and errors.

        Notes:
            - Should not stop on first error; attempt all issues
            - Populate report.pushed with successful issue IDs
            - Populate report.conflicts with conflicting issues
            - Populate report.errors with issue_id -> error_message
        """
        ...

    def pull_issues(self) -> SyncReport:
        """Pull all remote issues to local.

        Returns:
            SyncReport with pulled, conflicts, and errors.

        Notes:
            - Should detect conflicts with existing local issues
            - Populate report.pulled with issue IDs successfully integrated
            - Populate report.conflicts with conflicting issues
            - Populate report.errors with issue_id -> error_message
        """
        ...

    def get_conflict_resolution_options(self, conflict: SyncConflict) -> list[str]:
        """Get available resolution strategies for a conflict.

        Args:
            conflict: The SyncConflict to resolve

        Returns:
            List of resolution option codes (e.g., ['use_local', 'use_remote', 'merge'])

        Notes:
            - Different backends may support different strategies
            - At minimum should support 'use_local' and 'use_remote'
            - Merge strategies optional and backend-specific
        """
        ...

    def resolve_conflict(self, conflict: SyncConflict, resolution: str) -> bool:
        """Resolve a sync conflict using specified strategy.

        Args:
            conflict: The SyncConflict to resolve
            resolution: The resolution strategy code (from get_conflict_resolution_options)

        Returns:
            True if resolution succeeds, False otherwise.

        Notes:
            - Should not raise exceptions; return False on failure
            - After resolution, issue should be in consistent state
            - May involve local or remote modifications
        """
        ...
