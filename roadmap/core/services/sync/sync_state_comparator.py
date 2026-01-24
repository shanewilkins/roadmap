"""Sync state comparison service.

Provides logic to compare local and remote issue states, identifying
what needs to be pushed, pulled, or resolved. Backend-agnostic.
Supports both two-way (legacy) and three-way merge analysis.
"""

from collections.abc import Mapping
from datetime import datetime
from typing import Any

from structlog import get_logger

from roadmap.core.domain.issue import Issue
from roadmap.core.models.sync_models import SyncIssue
from roadmap.core.models.sync_state import IssueBaseState
from roadmap.core.services.sync.sync_change_computer import (
    compute_changes as _compute_changes_helper,
)
from roadmap.core.services.sync.sync_change_computer import (
    compute_changes_remote as _compute_changes_remote_helper,
)
from roadmap.core.services.sync.sync_conflict_detector import (
    detect_field_conflicts as _detect_field_conflicts_helper,
)
from roadmap.core.services.sync.sync_conflict_resolver import Conflict, ConflictField
from roadmap.core.services.sync.sync_key_normalizer import (
    normalize_remote_keys as _normalize_remote_keys_helper,
)
from roadmap.core.services.sync.sync_report import IssueChange
from roadmap.core.services.sync.sync_state_normalizer import (
    extract_timestamp as _extract_timestamp_helper,
)
from roadmap.core.services.sync.sync_state_normalizer import (
    normalize_remote_state as _normalize_remote_state_helper,
)
from roadmap.core.services.sync.sync_three_way import (
    build_issue_change as _build_issue_change_helper,
)

logger = get_logger()


class SyncStateComparator:
    """Compares local and remote issue states.

    Identifies conflicts, updates, and items requiring push/pull
    without knowledge of the backend implementation.
    """

    def __init__(
        self,
        fields_to_sync: list[str] | None = None,
        backend=None,  # Optional: SyncBackendInterface for key normalization
    ):
        """Initialize the state comparator.

        Args:
            fields_to_sync: Fields to check for changes (default: common fields)
                Note: 'title' is intentionally excluded as it's display metadata
                that doesn't affect workflow state. Only sync fields that change
                the work item's state (status, labels, priority, etc).
            backend: Optional backend instance for normalizing remote issue keys.
                When provided, remote issue keys are normalized to match local keys
                using backend-specific ID mapping (e.g., gh-42 → 42).
        """
        self.logger = get_logger()
        self.backend = backend
        default_fields = [
            "status",
            "priority",
            "content",
            "labels",
            "assignee",
        ]
        self.fields_to_sync = fields_to_sync or default_fields
        self.logger.debug(
            "sync_state_comparator_initialized",
            fields_to_sync=self.fields_to_sync,
            backend_aware=backend is not None,
            note="title excluded from sync as display metadata",
        )

    def _normalize_remote_keys(
        self,
        local: dict[str, Issue],
        remote: Mapping[str, Any],
    ) -> tuple[dict[str, Issue], Mapping[str, Any]]:
        """Normalize remote issue keys to match local issue keys.

        Local issues are keyed by UUID (e.g., "7e99d67b").
        Remote issues may be keyed by backend-specific IDs (e.g., "gh-42" or "42").

        This method creates a mapping by matching remote IDs to local remote_ids
        using two sources (in order of preference):
        1. Database cache (fast O(1) lookups via RemoteLinkRepository)
        2. YAML files (fallback if database not available)

        Args:
            local: Dict of local issues keyed by UUID
            remote: Dict of remote SyncIssue objects keyed by backend-specific ID

        Returns:
            Tuple of (local, normalized_remote) where normalized_remote is keyed
            by local issue UUIDs for proper matching.
        """
        return _normalize_remote_keys_helper(
            local, remote, self.backend, logger=self.logger
        )

    def identify_conflicts(
        self,
        local: dict[str, Issue],
        remote: dict[str, dict[str, Any]],
    ) -> list[Conflict]:
        """Identify issues that differ in both local and remote.

        A conflict exists when:
        1. Same issue exists in both local and remote
        2. They have different values for at least one field

        Args:
            local: Dict of local issues keyed by ID
            remote: Dict of remote issues keyed by ID

        Returns:
            List of Conflict objects representing detected conflicts

        Raises:
            ValueError: If issue data is invalid
        """
        self.logger.info(
            "identify_conflicts_start",
            local_count=len(local),
            remote_count=len(remote),
        )

        conflicts = []
        common_ids = set(local.keys()) & set(remote.keys())

        self.logger.debug(
            "identifying_conflicts",
            common_issue_count=len(common_ids),
        )

        for issue_id in common_ids:
            try:
                local_issue = local[issue_id]
                remote_issue = remote[issue_id]

                # Detect field-level conflicts
                conflicting_fields = self._detect_field_conflicts(
                    local_issue, remote_issue
                )

                if conflicting_fields:
                    # Extract updated timestamps
                    local_updated = local_issue.updated
                    remote_updated = self._extract_timestamp(remote_issue, "updated_at")

                    conflict = Conflict(
                        issue_id=issue_id,
                        local_issue=local_issue,
                        remote_issue=remote_issue,
                        fields=conflicting_fields,
                        local_updated=local_updated,
                        remote_updated=remote_updated,
                    )

                    conflicts.append(conflict)
                    self.logger.debug(
                        "conflict_identified",
                        issue_id=issue_id,
                        field_count=len(conflicting_fields),
                    )

            except Exception as e:
                self.logger.error(
                    "conflict_detection_error",
                    issue_id=issue_id,
                    error=str(e),
                )
                raise ValueError(
                    f"Failed to detect conflicts for {issue_id}: {str(e)}"
                ) from e

        self.logger.info("identify_conflicts_complete", conflict_count=len(conflicts))
        return conflicts

    def identify_updates(
        self,
        local: dict[str, Issue],
        remote: dict[str, dict[str, Any]],
    ) -> list[Issue]:
        """Identify local issues that need pushing to remote.

        An update is needed when:
        1. Issue exists only in local (new issue)
        2. Issue exists in both but local is newer

        Args:
            local: Dict of local issues keyed by ID
            remote: Dict of remote issues keyed by ID

        Returns:
            List of Issues that need to be pushed

        Raises:
            ValueError: If issue data is invalid
        """
        self.logger.info(
            "identify_updates_start",
            local_count=len(local),
            remote_count=len(remote),
        )

        updates = []

        for issue_id, local_issue in local.items():
            try:
                # New issue (doesn't exist in remote)
                if issue_id not in remote:
                    self.logger.debug("new_local_issue_identified", issue_id=issue_id)
                    updates.append(local_issue)
                    continue

                # Existing issue - check if local is newer
                remote_issue = remote[issue_id]
                remote_updated = self._extract_timestamp(remote_issue, "updated_at")

                if remote_updated is None:
                    # Can't compare - assume local should be pushed
                    self.logger.debug(
                        "no_remote_timestamp_treating_as_update",
                        issue_id=issue_id,
                    )
                    updates.append(local_issue)
                    continue

                if local_issue.updated > remote_updated:
                    time_diff = (local_issue.updated - remote_updated).total_seconds()
                    self.logger.debug(
                        "local_is_newer_needs_update",
                        issue_id=issue_id,
                        seconds_ahead=time_diff,
                    )
                    updates.append(local_issue)

            except Exception as e:
                self.logger.error(
                    "update_detection_error",
                    issue_id=issue_id,
                    error=str(e),
                )
                raise ValueError(
                    f"Failed to detect updates for {issue_id}: {str(e)}"
                ) from e

        self.logger.info("identify_updates_complete", update_count=len(updates))
        return updates

    def identify_pulls(
        self,
        local: dict[str, Issue],
        remote: dict[str, dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Identify remote issues that need pulling to local.

        A pull is needed when:
        1. Issue exists only in remote (new from remote)
        2. Issue exists in both but remote is newer

        Args:
            local: Dict of local issues keyed by ID
            remote: Dict of remote issues keyed by ID

        Returns:
            List of remote issues that need to be pulled

        Raises:
            ValueError: If issue data is invalid
        """
        self.logger.info(
            "identify_pulls_start",
            local_count=len(local),
            remote_count=len(remote),
        )

        pulls = []

        for issue_id, remote_issue in remote.items():
            try:
                # New remote issue (doesn't exist locally)
                if issue_id not in local:
                    self.logger.debug("new_remote_issue_identified", issue_id=issue_id)
                    pulls.append(issue_id)
                    continue

                # Existing issue - check if remote is newer
                local_issue = local[issue_id]
                remote_updated = self._extract_timestamp(remote_issue, "updated_at")

                if remote_updated is None:
                    # Can't compare - skip
                    self.logger.debug(
                        "no_remote_timestamp_skipping_pull",
                        issue_id=issue_id,
                    )
                    continue

                if remote_updated > local_issue.updated:
                    time_diff = (remote_updated - local_issue.updated).total_seconds()
                    self.logger.debug(
                        "remote_is_newer_needs_pull",
                        issue_id=issue_id,
                        seconds_ahead=time_diff,
                    )
                    pulls.append(issue_id)

            except Exception as e:
                self.logger.error(
                    "pull_detection_error",
                    issue_id=issue_id,
                    error=str(e),
                )
                raise ValueError(
                    f"Failed to detect pulls for {issue_id}: {str(e)}"
                ) from e

        self.logger.info("identify_pulls_complete", pull_count=len(pulls))
        return pulls

    def identify_up_to_date(
        self,
        local: dict[str, Issue],
        remote: dict[str, dict[str, Any]],
    ) -> list[str]:
        """Identify issues that are up-to-date in both local and remote.

        An issue is up-to-date when:
        1. It exists in both local and remote
        2. They have identical values (or no conflict detected)
        3. Timestamps are equal

        Args:
            local: Dict of local issues keyed by ID
            remote: Dict of remote issues keyed by ID

        Returns:
            List of issue IDs that are up-to-date

        Raises:
            ValueError: If issue data is invalid
        """
        self.logger.info(
            "identify_up_to_date_start",
            local_count=len(local),
            remote_count=len(remote),
        )

        up_to_date = []
        common_ids = set(local.keys()) & set(remote.keys())

        for issue_id in common_ids:
            try:
                local_issue = local[issue_id]
                remote_issue = remote[issue_id]

                # Check if they have conflicts
                conflicts = self._detect_field_conflicts(local_issue, remote_issue)

                if conflicts:
                    # Has conflicts - not up to date
                    continue

                # Check timestamps
                remote_updated = self._extract_timestamp(remote_issue, "updated_at")

                if remote_updated is not None and local_issue.updated != remote_updated:
                    # Different timestamps - not up to date
                    continue

                # No conflicts and timestamps match (or can't compare)
                up_to_date.append(issue_id)
                self.logger.debug("issue_is_up_to_date", issue_id=issue_id)

            except Exception as e:
                self.logger.warning(
                    "up_to_date_check_error",
                    issue_id=issue_id,
                    error=str(e),
                )
                # If we can't determine, assume not up-to-date
                continue

        self.logger.info(
            "identify_up_to_date_complete", up_to_date_count=len(up_to_date)
        )
        return up_to_date

    def _detect_field_conflicts(
        self,
        local: Issue,
        remote: dict[str, Any] | object,
    ) -> list[ConflictField]:
        """Detect field-level conflicts between local and remote issues.

        Compares only fields that affect workflow state. The 'title' field is
        intentionally excluded as it's metadata that doesn't change work item
        state or require synchronization.

        Args:
            local: The local Issue
            remote: The remote issue dict

        Returns:
            List of ConflictFields representing conflicts

        Raises:
            ValueError: If field data is invalid
        """
        return _detect_field_conflicts_helper(
            local,
            remote,
            self.fields_to_sync,
            extract_timestamp=self._extract_timestamp,
            logger=self.logger,
        )

    def _extract_timestamp(
        self,
        data: dict[str, Any] | object,
        timestamp_field: str = "updated_at",
    ) -> datetime | None:
        """Extract and parse a timestamp from remote issue data.

        Args:
            data: The remote issue dict
            timestamp_field: The field name containing the timestamp

        Returns:
            Parsed datetime or None if not found/invalid

        Raises:
            ValueError: If timestamp format is invalid
        """
        return _extract_timestamp_helper(data, timestamp_field, logger=self.logger)

    def _resolve_issue_title(
        self,
        issue_id: str,
        local: Issue | None,
        remote: Any | None,
        baseline: IssueBaseState | None,
    ) -> str:
        """Resolve a sensible title for presentation and logging."""
        title = None
        if local is not None:
            title = getattr(local, "title", None)
        if not title and remote is not None:
            title = (
                remote.get("title")
                if isinstance(remote, dict)
                else getattr(remote, "title", None)
            )
        if not title and baseline is not None:
            title = getattr(baseline, "title", issue_id)
        return title or issue_id

    def _normalize_remote_state(self, remote: Any) -> dict[str, Any] | None:
        """Normalize remote representations into a plain dict for comparison."""
        return _normalize_remote_state_helper(remote, logger=self.logger)

    def _handle_first_sync_semantics(
        self,
        change: IssueChange,
        local: Issue | None,
        remote_state: dict | None,
        baseline: IssueBaseState | None,
    ) -> None:
        """Handle first-sync special cases where baseline is missing."""
        if local is not None and remote_state is None:
            change.local_changes = (
                self._compute_changes(baseline, local) if local is not None else {}
            )
            change.local_changes["_new"] = True
            change.conflict_type = "local_only"
            change.has_conflict = False
            return

        if remote_state is not None and local is None:
            change.remote_changes = (
                self._compute_changes_remote(baseline, remote_state)
                if remote_state is not None
                else {}
            )
            change.remote_changes["_new"] = True
            change.conflict_type = "remote_only"
            change.has_conflict = False
            return

        if local is not None and remote_state is not None:
            # Both present: simplified rule - differing status => conflict
            from roadmap.common.constants import Status

            # Normalize remote status
            remote_status = (
                remote_state.get("status") if isinstance(remote_state, dict) else None
            )
            try:
                if isinstance(remote_status, str):
                    try:
                        remote_status = Status(remote_status)
                    except Exception:
                        remote_status = Status(remote_status.lower())
            except Exception as e:
                logger.debug(
                    "status_normalization_failed",
                    operation="normalize_status",
                    field="remote_status",
                    error=str(e),
                    action="Skipping status normalization",
                )

            local_status = getattr(local, "status", None)

            def status_value(s):
                if s is None:
                    return None
                return s.value if hasattr(s, "value") else str(s).lower()

            change.local_changes.setdefault("_new", True)
            change.remote_changes.setdefault("_new", True)

            if status_value(local_status) == status_value(remote_status):
                change.local_changes = {}
                change.remote_changes = {}
                change.conflict_type = "no_change"
                change.has_conflict = False
            else:
                mutual_conflicts = self._detect_field_conflicts(local, remote_state)
                flagged = {}
                for c in mutual_conflicts:
                    flagged[c.field_name] = {
                        "local": c.local_value,
                        "remote": c.remote_value,
                    }
                change.flagged_conflicts = flagged
                change.conflict_type = "both_changed"
                change.has_conflict = True

    def _detect_and_flag_conflicts(
        self, change: IssueChange, local: Issue | None, remote_state: dict | None
    ) -> None:
        """Detect field-level conflicts when a baseline exists."""
        if local is not None and remote_state is not None:
            conflicts = self._detect_field_conflicts(local, remote_state)
            if conflicts:
                flagged = {}
                for c in conflicts:
                    flagged[c.field_name] = {
                        "local": c.local_value,
                        "remote": c.remote_value,
                    }
                change.flagged_conflicts = flagged

    def _build_issue_change(
        self,
        issue_id: str,
        local: Issue | None,
        remote: dict[str, Any] | None,
        baseline: IssueBaseState | None = None,
    ) -> IssueChange:
        """Construct an IssueChange for a single issue using three-way context.

        This centralizes the logic of computing local/remote changes, detecting
        field-level conflicts, and setting conflict metadata for the analyzer.
        """
        return _build_issue_change_helper(
            issue_id,
            local,
            remote,
            baseline,
            resolve_title=self._resolve_issue_title,
            normalize_remote_state=self._normalize_remote_state,
            compute_changes=self._compute_changes,
            compute_changes_remote=self._compute_changes_remote,
            handle_first_sync_semantics=self._handle_first_sync_semantics,
            detect_and_flag_conflicts=self._detect_and_flag_conflicts,
            extract_timestamp=self._extract_timestamp,
            fields_to_sync=self.fields_to_sync,
            logger=self.logger,
        )

    def analyze_three_way(
        self,
        local: dict[str, Issue],
        remote: Mapping[str, Any],
        baseline: dict[str, IssueBaseState] | None = None,
    ) -> list[IssueChange]:
        """Analyze changes using three-way merge context.

        Compares baseline → local and baseline → remote to identify
        what changed in each direction, providing complete conflict context.

        Args:
            local: Dict of local issues keyed by ID
            remote: Dict of remote SyncIssue objects keyed by ID
            baseline: Dict of baseline states keyed by ID (from last sync)

        Returns:
            List of IssueChange objects with three-way context

        Raises:
            ValueError: If analysis fails
        """
        self.logger.info(
            "analyze_three_way_start",
            local_count=len(local),
            remote_count=len(remote),
            baseline_count=len(baseline or {}),
            backend_aware=self.backend is not None,
        )

        if baseline is None:
            baseline = {}

        # Normalize remote keys to match local UUIDs (if backend aware)
        local, remote = self._normalize_remote_keys(local, remote)

        changes = []
        all_issue_ids = set(local.keys()) | set(remote.keys())

        for issue_id in all_issue_ids:
            try:
                change = self._build_issue_change(
                    issue_id,
                    local.get(issue_id),
                    remote.get(issue_id),
                    baseline.get(issue_id) if baseline else None,
                )
                changes.append(change)
                self.logger.debug(
                    "three_way_analysis_complete",
                    issue_id=issue_id,
                    conflict_type=change.conflict_type,
                )
            except Exception as e:
                self.logger.error(
                    "three_way_analysis_error",
                    issue_id=issue_id,
                    error=str(e),
                )
                raise ValueError(
                    f"Failed to analyze {issue_id} in three-way merge: {str(e)}"
                ) from e

        self.logger.info("analyze_three_way_complete", change_count=len(changes))
        return changes

    def _compute_changes(
        self,
        baseline: IssueBaseState | None,
        local: Issue,
    ) -> dict[str, Any]:
        """Compute what changed between baseline and local issue.

        Args:
            baseline: The baseline state
            local: The current local issue

        Returns:
            Dict of field → value for changed fields
        """
        return _compute_changes_helper(baseline, local, logger=self.logger)

    def _compute_changes_remote(
        self,
        baseline: IssueBaseState | None,
        remote: SyncIssue | dict[str, Any],
    ) -> dict[str, Any]:
        """Compute what changed between baseline and remote issue.

        Args:
            baseline: The baseline state
            remote: The current remote SyncIssue

        Returns:
            Dict of field → value for changed fields
        """
        return _compute_changes_remote_helper(baseline, remote, logger=self.logger)
