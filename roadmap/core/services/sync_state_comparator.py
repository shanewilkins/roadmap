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
from roadmap.core.services.sync_conflict_resolver import Conflict, ConflictField
from roadmap.core.services.sync_report import IssueChange

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
        if not self.backend:
            # Without backend info, can't normalize keys
            return local, remote

        backend_name = self.backend.get_backend_name()
        normalized_remote = {}

        # Build reverse mapping: remote_id → local_uuid
        # Priority 1: Try database lookups (fast)
        remote_id_to_local_uuid = {}
        db_lookup_available = False

        # Check if backend has access to RemoteLinkRepository
        remote_link_repo = getattr(self.backend, "remote_link_repo", None)
        if remote_link_repo:
            db_lookup_available = True
            # Use database for reverse lookup: remote_id → issue_uuid
            db_links = remote_link_repo.get_all_links_for_backend(backend_name)
            for issue_uuid, remote_id in db_links.items():
                remote_id_key = str(remote_id)
                remote_id_to_local_uuid[remote_id_key] = issue_uuid
            self.logger.debug(
                "loaded_remote_links_from_database",
                backend=backend_name,
                link_count=len(remote_id_to_local_uuid),
            )

        # Priority 2: If database not available or incomplete, supplement from YAML
        # (for backward compatibility or if database is out of sync)
        if not db_lookup_available or len(remote_id_to_local_uuid) < len(local):
            for local_uuid, local_issue in local.items():
                if local_issue.remote_ids and backend_name in local_issue.remote_ids:
                    remote_id = local_issue.remote_ids[backend_name]
                    # Normalize remote_id to string for matching
                    remote_id_key = str(remote_id)
                    # Only add if not already in database mapping
                    if remote_id_key not in remote_id_to_local_uuid:
                        remote_id_to_local_uuid[remote_id_key] = local_uuid
                        self.logger.debug(
                            "loaded_remote_id_from_yaml",
                            remote_id=remote_id_key,
                            local_uuid=local_uuid,
                            backend=backend_name,
                        )

        # Remap remote issues using the combined mapping
        unmatched_remote = []
        for remote_key, remote_issue in remote.items():
            remote_key_str = str(remote_key)
            if remote_key_str in remote_id_to_local_uuid:
                # Found matching local issue - use its UUID as key
                local_uuid = remote_id_to_local_uuid[remote_key_str]
                normalized_remote[local_uuid] = remote_issue
                self.logger.debug(
                    "normalized_remote_key",
                    original_key=remote_key_str,
                    normalized_to=local_uuid,
                    source="database" if db_lookup_available else "yaml",
                )
            else:
                # No matching local issue found - keep original key
                # This represents a new issue from remote
                unmatched_remote.append((remote_key, remote_issue))

        # Add unmatched remote issues with prefixed keys to distinguish from local UUIDs
        for remote_key, remote_issue in unmatched_remote:
            prefixed_key = f"_remote_{remote_key}"
            normalized_remote[prefixed_key] = remote_issue
            self.logger.debug(
                "new_remote_issue",
                remote_key=str(remote_key),
                prefixed_key=prefixed_key,
            )

        self.logger.info(
            "remote_keys_normalized",
            original_remote_count=len(remote),
            normalized_count=len(normalized_remote),
            matched=len(remote) - len(unmatched_remote),
            unmatched=len(unmatched_remote),
            backend=backend_name,
            db_lookup_used=db_lookup_available,
        )

        return local, normalized_remote

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
        from roadmap.common.constants import Priority, Status

        conflicts = []

        for field_name in self.fields_to_sync:
            try:
                local_val = getattr(local, field_name, None)
                # remote may be a dict or an object (SyncIssue). Handle both.
                if isinstance(remote, dict):
                    remote_val = remote.get(field_name)
                else:
                    remote_val = getattr(remote, field_name, None)

                # Normalize enum values for comparison
                if field_name == "status" and remote_val is not None:
                    if isinstance(remote_val, str):
                        try:
                            # Try exact match first, then try lowercase
                            try:
                                remote_val = Status(remote_val)
                            except (ValueError, KeyError):
                                remote_val = Status(remote_val.lower())
                        except (ValueError, KeyError, AttributeError):
                            # If conversion fails, keep original value
                            pass

                if field_name == "priority" and remote_val is not None:
                    if isinstance(remote_val, str):
                        try:
                            # Try exact match first, then try lowercase
                            try:
                                remote_val = Priority(remote_val)
                            except (ValueError, KeyError):
                                remote_val = Priority(remote_val.lower())
                        except (ValueError, KeyError, AttributeError):
                            # If conversion fails, keep original value
                            pass

                # Skip if both are None/empty
                if not local_val and not remote_val:
                    continue

                # Check for conflict
                if local_val != remote_val:
                    conflict_field = ConflictField(
                        field_name=field_name,
                        local_value=local_val,
                        remote_value=remote_val,
                        local_updated=local.updated,
                        remote_updated=self._extract_timestamp(remote, "updated_at"),
                    )
                    conflicts.append(conflict_field)

            except Exception as e:
                self.logger.debug(
                    "field_conflict_check_error",
                    field=field_name,
                    error=str(e),
                )
                continue

        return conflicts

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
        try:
            # Support dict-like or object remote representations
            if isinstance(data, dict):
                ts = data.get(timestamp_field)
            else:
                ts = getattr(data, timestamp_field, None)

            if ts is None:
                return None

            # Already a datetime?
            if isinstance(ts, datetime):
                return ts

            # String timestamp? Try parsing ISO format
            if isinstance(ts, str):
                # Handle ISO format with and without timezone
                if ts.endswith("Z"):
                    ts = ts[:-1] + "+00:00"
                return datetime.fromisoformat(ts)

            return None

        except Exception as e:
            self.logger.debug(
                "timestamp_extraction_error",
                field=timestamp_field,
                error=str(e),
            )
            return None

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
                local_issue = local.get(issue_id)
                remote_issue = remote.get(issue_id)
                baseline_state = baseline.get(issue_id)

                # Get title (use local, then remote, then baseline, then default)
                remote_title = None
                if remote_issue:
                    # remote_issue may be a SyncIssue object or a dict
                    if isinstance(remote_issue, dict):
                        remote_title = remote_issue.get("title")
                    else:
                        remote_title = getattr(remote_issue, "title", None)

                title = (
                    local_issue.title
                    if local_issue
                    else (
                        remote_title
                        if remote_title
                        else (baseline_state.title if baseline_state else None)
                    )
                ) or "Unknown"

                # Analyze local changes (baseline → local)
                local_changes = {}
                if baseline_state and local_issue:
                    local_changes = self._compute_changes(
                        baseline_state, local_issue, "local"
                    )
                elif not baseline_state and local_issue:
                    # New issue (not in baseline)
                    local_changes = {"_new": True}

                # Analyze remote changes (baseline → remote)
                remote_changes = {}
                if baseline_state and remote_issue:
                    remote_changes = self._compute_changes_remote(
                        baseline_state, remote_issue
                    )
                elif not baseline_state and remote_issue:
                    # New issue (not in baseline)
                    remote_changes = {"_new": True}

                # Determine conflict type
                conflict_type = "no_change"

                # Special case: first sync with both local and remote new
                # Check if they're actually the same issue with same content
                if (
                    not baseline_state
                    and local_issue
                    and remote_issue
                    and local_changes == {"_new": True}
                    and remote_changes == {"_new": True}
                ):
                    # Both sides are new and we don't have a baseline
                    # Treat as "no_change" only if they have identical content

                    local_status = getattr(local_issue, "status", None)
                    # remote_status may be attribute or dict entry
                    if isinstance(remote_issue, dict):
                        remote_status = remote_issue.get("status")
                    else:
                        remote_status = getattr(remote_issue, "status", None)

                    # Normalize status values for comparison
                    local_status_str = (
                        local_status.value
                        if hasattr(local_status, "value")
                        else str(local_status).lower()
                    )
                    remote_status_str = str(remote_status).lower()

                    local_title = getattr(local_issue, "title", "")
                    remote_title = (
                        remote_issue.get("title")
                        if isinstance(remote_issue, dict)
                        else getattr(remote_issue, "title", "")
                    ) or ""

                    # Only treat as no_change if status and title are identical
                    # Otherwise, both_changed (real conflict)
                    if (
                        local_status_str == remote_status_str
                        and local_title == remote_title
                    ):
                        conflict_type = "no_change"
                        # Clear the _new markers since they're identical
                        local_changes = {}
                        remote_changes = {}
                    else:
                        # Different content = conflict
                        conflict_type = "both_changed"
                elif local_changes and remote_changes:
                    conflict_type = "both_changed"
                elif local_changes:
                    conflict_type = "local_only"
                elif remote_changes:
                    conflict_type = "remote_only"

                # Create IssueChange with three-way context
                # Handle both Issue objects and dicts for remote_state
                remote_state_dict: dict[str, Any] | None = None
                if remote_issue:
                    to_dict = getattr(remote_issue, "to_dict", None)
                    if callable(to_dict):
                        result = to_dict()
                        if isinstance(result, dict):
                            remote_state_dict = result
                    elif isinstance(remote_issue, dict):
                        remote_state_dict = remote_issue

                issue_change = IssueChange(
                    issue_id=issue_id,
                    title=title,
                    baseline_state=baseline_state,
                    local_state=local_issue,
                    remote_state=remote_state_dict,
                    local_changes=local_changes,
                    remote_changes=remote_changes,
                    conflict_type=conflict_type,
                    has_conflict=(conflict_type == "both_changed"),
                )

                changes.append(issue_change)
                self.logger.debug(
                    "three_way_analysis_complete",
                    issue_id=issue_id,
                    conflict_type=conflict_type,
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
        baseline: IssueBaseState,
        local: Issue,
        source: str = "local",
    ) -> dict[str, Any]:
        """Compute what changed between baseline and local issue.

        Args:
            baseline: The baseline state
            local: The current local issue
            source: Description of source (for logging)

        Returns:
            Dict of field → value for changed fields
        """
        changes = {}

        # Map of field names to compare
        field_map = {
            "status": (
                "status",
                lambda x: x.status.value
                if hasattr(x.status, "value")
                else str(x.status),
            ),
            "assignee": ("assignee", lambda x: x.assignee),
            "content": ("content", lambda x: x.content),
            "labels": ("labels", lambda x: sorted(x.labels or [])),
        }

        for field_name, (baseline_attr, local_getter) in field_map.items():
            try:
                baseline_value = getattr(baseline, baseline_attr, None)
                local_value = local_getter(local)

                if baseline_value != local_value:
                    changes[field_name] = {
                        "from": baseline_value,
                        "to": local_value,
                    }
                    self.logger.debug(
                        "field_changed_detected",
                        source=source,
                        field=field_name,
                        baseline=baseline_value,
                        current=local_value,
                    )
            except Exception as e:
                self.logger.warning(
                    "field_change_detection_error",
                    source=source,
                    field=field_name,
                    error=str(e),
                )
                continue

        return changes

    def _compute_changes_remote(
        self,
        baseline: IssueBaseState,
        remote: SyncIssue | dict[str, Any],
    ) -> dict[str, Any]:
        """Compute what changed between baseline and remote issue.

        Args:
            baseline: The baseline state
            remote: The current remote SyncIssue

        Returns:
            Dict of field → value for changed fields
        """
        from roadmap.common.constants import Priority, Status

        changes = {}

        # Helper to get field value from remote (handles both SyncIssue and dict)
        def get_remote_field(field_name: str, default: Any = None) -> Any:
            # Remote may be a SyncIssue object or a dict; handle both.
            if isinstance(remote, dict):
                return remote.get(field_name, default)
            return getattr(remote, field_name, default)

        # Map of field names to compare
        # Remote (SyncIssue or dict) field names
        # Support both 'content' and 'description' keys for backwards compatibility
        field_map = {
            "status": ("status", lambda: get_remote_field("status")),
            "assignee": ("assignee", lambda: get_remote_field("assignee")),
            "content": (
                "content",
                lambda: get_remote_field("content")
                or get_remote_field("description")
                or "",
            ),
            "labels": (
                "labels",
                lambda: sorted(get_remote_field("labels", []))
                if get_remote_field("labels")
                else [],
            ),
        }

        for field_name, (baseline_attr, remote_getter) in field_map.items():
            try:
                baseline_value = getattr(baseline, baseline_attr, None)
                remote_value = remote_getter()

                # Normalize enum values for comparison
                if field_name == "status" and remote_value is not None:
                    if isinstance(remote_value, str):
                        try:
                            remote_value = Status(remote_value)
                        except (ValueError, KeyError):
                            try:
                                remote_value = Status(remote_value.lower())
                            except (ValueError, KeyError):
                                pass

                if field_name == "priority" and remote_value is not None:
                    if isinstance(remote_value, str):
                        try:
                            remote_value = Priority(remote_value)
                        except (ValueError, KeyError):
                            try:
                                remote_value = Priority(remote_value.lower())
                            except (ValueError, KeyError):
                                pass

                if baseline_value != remote_value:
                    changes[field_name] = {
                        "from": baseline_value,
                        "to": remote_value,
                    }
                    self.logger.debug(
                        "field_changed_detected",
                        source="remote",
                        field=field_name,
                        baseline=baseline_value,
                        current=remote_value,
                    )
            except Exception as e:
                self.logger.warning(
                    "field_change_detection_error_remote",
                    field=field_name,
                    error=str(e),
                )
                continue

        return changes
