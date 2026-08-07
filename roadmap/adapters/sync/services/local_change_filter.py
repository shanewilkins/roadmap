"""Filters local changes from baseline for sync operations.

Extracted from SyncMergeEngine to separate change filtering logic.
"""

from structlog import get_logger

logger = get_logger(__name__)


class LocalChangeFilter:
    """Filters and identifies local changes since baseline."""

    @staticmethod
    def filter_unchanged_from_base(
        issues: list, current_local: dict, base_state_issues: dict
    ) -> list:
        """Filter out unchanged issues, keeping only changed or new ones.

        Args:
            issues: List of issues to filter
            current_local: Dict of current local issues keyed by ID
            base_state_issues: Dict of baseline state issues keyed by ID

        Returns:
            Filtered list containing only changed or new issues
        """
        if not base_state_issues:
            logger.debug(
                "filter_no_base_state",
                input_count=len(issues),
                reason="first_sync_no_previous_state",
            )
            return issues

        filtered = []
        skipped_count = 0
        new_count = 0
        changed_count = 0

        for issue in issues:
            issue_id = issue.id if hasattr(issue, "id") else issue
            if issue_id not in current_local:
                logger.debug(
                    "filter_issue_not_in_local",
                    issue_id=issue_id,
                    reason="might_be_stale",
                )
                continue
            if issue_id not in base_state_issues:
                logger.debug(
                    "filter_new_local_issue",
                    issue_id=issue_id,
                    reason="not_in_previous_sync",
                )
                new_count += 1
                filtered.append(issue)
                continue

            local_issue = current_local[issue_id]
            base_state = base_state_issues[issue_id]

            fields_to_check = {
                "status": lambda obj: (
                    obj.status.value
                    if hasattr(obj.status, "value")
                    else str(obj.status)
                ),
                "assignee": lambda obj: obj.assignee,
                "description": lambda obj: obj.description,
                "labels": lambda obj: sorted(obj.labels or []),
            }

            has_local_changes = False
            changed_fields = []

            for field_name, getter in fields_to_check.items():
                try:
                    local_value = getter(local_issue)
                except Exception as e:
                    logger.warning(
                        "filter_field_extraction_failed",
                        issue_id=issue_id,
                        field=field_name,
                        error=str(e),
                    )
                    local_value = None

                base_value = getattr(base_state, field_name, None)

                if local_value != base_value:
                    logger.debug(
                        "filter_local_change_detected",
                        issue_id=issue_id,
                        field=field_name,
                        base_value=base_value,
                        local_value=local_value,
                    )
                    changed_fields.append(field_name)
                    has_local_changes = True

            if has_local_changes:
                logger.debug(
                    "filter_issue_has_local_changes",
                    issue_id=issue_id,
                    changed_fields=changed_fields,
                )
                changed_count += 1
                filtered.append(issue)
            else:
                logger.debug(
                    "filter_issue_unchanged_since_sync",
                    issue_id=issue_id,
                    reason="no_local_modifications",
                )
                skipped_count += 1

        logger.info(
            "filter_complete",
            input_count=len(issues),
            output_count=len(filtered),
            skipped_count=skipped_count,
            new_count=new_count,
            changed_count=changed_count,
            filtered_out_percentage=round((skipped_count / len(issues) * 100), 1)
            if len(issues) > 0
            else 0,
        )
        return filtered
