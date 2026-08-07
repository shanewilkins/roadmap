"""Protocol definitions for pluggable sync backends.

This module defines the SyncBackendInterface that all sync backends must implement,
enabling support for multiple sync targets (GitHub, vanilla Git, GitLab, etc.)
without coupling the core sync logic to specific implementations.

Updated to use Result<T, SyncError> pattern for explicit error handling.
"""

from typing import Any, Protocol

from roadmap.common.result import Result
from roadmap.core.domain.issue import Issue
from roadmap.core.models.sync_models import SyncIssue, SyncMilestone, SyncProject
from roadmap.core.services.sync.sync_errors import SyncError


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
        self.error: str | None = None  # Overall sync error (if fatal)


class SyncBackendInterface(Protocol):
    """Abstract interface for sync backends.

    Defines the contract that all sync backends must implement to enable
    pluggable sync functionality. Allows support for GitHub, vanilla Git,
    GitLab, Jira, and other sync targets.

    All methods should handle errors gracefully and return status/report objects
    rather than raising exceptions, enabling dry-run and conflict resolution
    workflows.
    """

    def authenticate(self) -> Result[bool, SyncError]:
        """Verify credentials and remote connectivity.

        Returns:
            Ok(True) if authentication succeeds
            Err(SyncError) with authentication error details

        Notes:
            - No longer raises exceptions
            - Returns Err with AUTHENTICATION_FAILED error type on failure
            - May return TOKEN_EXPIRED or PERMISSION_DENIED error types
        """
        ...

    def get_backend_name(self) -> str:
        """Get the canonical name of this backend.

        Returns:
            Backend name (e.g., 'github', 'git', 'gitlab')
            Used as key in Issue.remote_ids dict to track remote issue IDs.
        """
        ...

    def get_issues(self) -> Result[dict[str, SyncIssue], SyncError]:
        """Fetch all issues from remote.

        Returns:
            Ok(dict) mapping issue_id -> SyncIssue on success
            Err(SyncError) with error details on failure

        Notes:
            - Backends normalize their API responses to SyncIssue format
            - All fields are populated from backend data, including raw_response
            - May return NETWORK_ERROR, API_RATE_LIMIT, or other error types
        """
        ...

    def push_issues(self, local_issues: list[Issue]) -> Result[SyncReport, SyncError]:
        """Push multiple local issues to remote.

        Args:
            local_issues: List of Issue objects to push

        Returns:
            Ok(SyncReport) with pushed, conflicts, and errors on success
            Err(SyncError) with fatal error details if operation cannot proceed

        Notes:
            - Should not stop on first error; attempt all issues
            - Individual issue errors go in report.errors dict
            - Fatal errors (auth, network) return Err
            - Populate report.pushed with successful issue IDs
            - Populate report.conflicts with conflicting issues
        """
        ...

    def push_issue(self, local_issue: Issue) -> Result[bool, SyncError]:
        """Push a single local issue to remote.

        Args:
            local_issue: The Issue object to push to remote

        Returns:
            Ok(True) if push succeeds
            Err(SyncError) with error details if push fails

        Notes:
            - Default implementation: delegates to push_issues()
            - Backends may override for optimization
            - Idempotent: pushing same issue twice should be safe
        """
        report_result = self.push_issues([local_issue])
        if report_result.is_err():
            return report_result  # type: ignore[return-value]

        report = report_result.unwrap()
        if len(report.pushed) > 0 and len(report.errors) == 0:
            from roadmap.common.result import Ok

            return Ok(True)
        else:
            from roadmap.common.result import Err
            from roadmap.core.services.sync.sync_errors import SyncError, SyncErrorType

            error_msg = report.errors.get(str(local_issue.id), "Push failed")
            return Err(
                SyncError(
                    error_type=SyncErrorType.UNKNOWN_ERROR,
                    message=error_msg,
                    entity_type="Issue",
                    entity_id=str(local_issue.id),
                )
            )

    def pull_issues(self, issue_ids: list[str]) -> Result[SyncReport, SyncError]:
        """Pull specified remote issues to local.

        Args:
            issue_ids: List of remote issue IDs to pull. Empty list means pull nothing.

        Returns:
            Ok(SyncReport) with pulled, conflicts, and errors on success
            Err(SyncError) with fatal error details if operation cannot proceed

        Notes:
            - Should detect conflicts with existing local issues
            - Individual issue errors go in report.errors dict
            - Fatal errors (auth, network) return Err
            - Populate report.pulled with issue IDs successfully integrated
            - Populate report.conflicts with conflicting issues
            - Backend can optimize this (batch API calls, parallel processing, etc.)
        """
        ...

    def pull_issue(self, issue_id: str) -> Result[bool, SyncError]:
        """Pull a single remote issue to local.

        Args:
            issue_id: The remote issue ID to pull

        Returns:
            Ok(True) if pull succeeds
            Err(SyncError) with error details if pull fails

        Notes:
            - Default implementation: delegates to pull_issues()
            - Backends may override for optimization
            - Fetches the remote issue and updates local
        """
        report_result = self.pull_issues([issue_id])
        if report_result.is_err():
            return report_result  # type: ignore[return-value]

        report = report_result.unwrap()
        if len(report.pulled) > 0 and len(report.errors) == 0:
            from roadmap.common.result import Ok

            return Ok(True)
        else:
            from roadmap.common.result import Err
            from roadmap.core.services.sync.sync_errors import SyncError, SyncErrorType

            error_msg = report.errors.get(issue_id, "Pull failed")
            return Err(
                SyncError(
                    error_type=SyncErrorType.UNKNOWN_ERROR,
                    message=error_msg,
                    entity_type="Issue",
                    entity_id=issue_id,
                )
            )

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

    def get_milestones(self) -> Result[dict[str, SyncMilestone], SyncError]:
        """Fetch all milestones from remote.

        Returns:
            Ok(dict) mapping milestone_id -> SyncMilestone on success
            Err(SyncError) with error details on failure

        Notes:
            - Empty dict in Ok indicates no milestones exist
            - Network errors return Err
        """
        ...

    def get_projects(self) -> Result[dict[str, SyncProject], SyncError]:
        """Fetch all projects from remote.

        Returns:
            Ok(dict) mapping project_id -> SyncProject on success
            Err(SyncError) with error details on failure

        Notes:
            - Empty dict in Ok indicates no projects exist
            - Network errors return Err
        """
        ...
