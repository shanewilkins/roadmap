"""Converts issue changes to conflicts for resolution.

Extracted from SyncMergeEngine to separate conflict conversion logic.
"""

from structlog import get_logger

from roadmap.core.services.sync_conflict_resolver import Conflict, ConflictField

logger = get_logger(__name__)


class ConflictConverter:
    """Converts issue changes to conflict objects."""

    def __init__(self, state_comparator):
        """Initialize with state comparator.

        Args:
            state_comparator: SyncStateComparator for timestamp extraction
        """
        self.state_comparator = state_comparator

    def convert_changes_to_conflicts(self, issue_changes: list) -> list[Conflict]:
        """Convert issue changes with conflicts to conflict objects.

        Args:
            issue_changes: List of IssueChange objects with conflict info

        Returns:
            List of Conflict objects ready for resolution
        """
        conflicts: list[Conflict] = []

        for change in issue_changes:
            if (
                not change.has_conflict
                or not change.local_state
                or not change.remote_state
            ):
                continue
            try:
                conflicting_fields = []
                if change.local_changes:
                    for field_name, _change_info in change.local_changes.items():
                        if field_name in change.remote_changes:
                            conflict_field = ConflictField(
                                field_name=field_name,
                                local_value=change.local_state.__dict__.get(
                                    field_name, None
                                ),
                                remote_value=change.remote_state.get(field_name),
                                local_updated=change.local_state.updated,
                                remote_updated=self.state_comparator._extract_timestamp(
                                    change.remote_state, "updated_at"
                                ),
                            )
                            conflicting_fields.append(conflict_field)

                if conflicting_fields:
                    conflict = Conflict(
                        issue_id=change.issue_id,
                        local_issue=change.local_state,
                        remote_issue=change.remote_state,
                        fields=conflicting_fields,
                        local_updated=change.local_state.updated,
                        remote_updated=self.state_comparator._extract_timestamp(
                            change.remote_state, "updated_at"
                        ),
                    )
                    conflicts.append(conflict)

            except Exception as e:
                logger.warning(
                    "conflict_conversion_failed",
                    issue_id=change.issue_id,
                    operation="analyze_conflicts",
                    error_type=type(e).__name__,
                    error=str(e),
                    is_recoverable=True,
                    suggested_action="skip_issue",
                )
                continue

        return conflicts
