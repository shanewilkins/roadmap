"""Sync state comparison service.

Provides logic to compare local and remote issue states, identifying
what needs to be pushed, pulled, or resolved. Backend-agnostic.
"""

from datetime import datetime
from typing import Any

from structlog import get_logger

from roadmap.core.domain.issue import Issue
from roadmap.core.services.sync_conflict_resolver import Conflict, ConflictField

logger = get_logger()


class SyncStateComparator:
    """Compares local and remote issue states.

    Identifies conflicts, updates, and items requiring push/pull
    without knowledge of the backend implementation.
    """

    def __init__(self, fields_to_sync: list[str] | None = None):
        """Initialize the state comparator.

        Args:
            fields_to_sync: Fields to check for changes (default: common fields)
        """
        self.logger = get_logger()
        self.fields_to_sync = fields_to_sync or [
            "title",
            "status",
            "priority",
            "content",
            "labels",
            "assignee",
        ]
        self.logger.debug(
            "sync_state_comparator_initialized",
            fields_to_sync=self.fields_to_sync,
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
                    pulls.append(remote_issue)
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
                    pulls.append(remote_issue)

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
        remote: dict[str, Any],
    ) -> list[ConflictField]:
        """Detect field-level conflicts between local and remote issues.

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
                remote_val = remote.get(field_name)

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
        data: dict[str, Any],
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
            ts = data.get(timestamp_field)

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
