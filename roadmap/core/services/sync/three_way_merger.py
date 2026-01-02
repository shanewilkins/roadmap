"""Three-way merge logic for intelligent sync conflict resolution.

Implements the core algorithm: base vs local vs remote comparison
to automatically resolve most conflicts without data loss.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any


class MergeStatus(str, Enum):
    """Result of merging a field."""

    CLEAN = "clean"  # Auto-resolved, no conflict
    CONFLICT = "conflict"  # Both sides changed differently


@dataclass
class FieldMergeResult:
    """Result of merging a single field."""

    value: Any
    status: MergeStatus
    reason: str  # Why this decision was made

    def is_conflict(self) -> bool:
        """Check if this is a conflict."""
        return self.status == MergeStatus.CONFLICT


class ThreeWayMerger:
    """Implements three-way merge logic.

    Given base, local, and remote versions of a field, intelligently
    determines the merged value using this algorithm:

    - If only local changed: take local
    - If only remote changed: take remote
    - If both changed the same way: take either (no conflict)
    - If neither changed: take either (no conflict)
    - If both changed differently: CONFLICT (needs resolution)
    """

    def merge_field(
        self,
        field_name: str,
        base: Any,
        local: Any,
        remote: Any,
    ) -> FieldMergeResult:
        """Merge a single field using three-way logic.

        Args:
            field_name: Name of the field (for debugging)
            base: The agreed-upon value from last sync
            local: Current local value
            remote: Current remote value

        Returns:
            FieldMergeResult with merged value and status
        """
        # Case 1: Neither changed (everything stayed at base)
        if local == base and remote == base:
            return FieldMergeResult(
                value=local,
                status=MergeStatus.CLEAN,
                reason=f"{field_name}: no changes",
            )

        # Case 2: Only local changed (remote stayed at base)
        if local != base and remote == base:
            return FieldMergeResult(
                value=local,
                status=MergeStatus.CLEAN,
                reason=f"{field_name}: only local changed",
            )

        # Case 3: Only remote changed (local stayed at base)
        if remote != base and local == base:
            return FieldMergeResult(
                value=remote,
                status=MergeStatus.CLEAN,
                reason=f"{field_name}: only remote changed",
            )

        # Case 4: Both changed, but to the same value
        if local == remote:
            return FieldMergeResult(
                value=local,
                status=MergeStatus.CLEAN,
                reason=f"{field_name}: both changed to same value",
            )

        # Case 5: Both changed differently - TRUE CONFLICT
        return FieldMergeResult(
            value=None,  # Can't auto-resolve
            status=MergeStatus.CONFLICT,
            reason=f"{field_name}: both sides changed differently (base={base}, local={local}, remote={remote})",
        )

    def merge_issue(
        self,
        issue_id: str,
        base: dict[str, Any],
        local: dict[str, Any],
        remote: dict[str, Any],
    ) -> tuple[dict[str, Any], list[str]]:
        """Merge all fields of an issue.

        Returns:
            (merged_fields, list_of_conflicted_field_names)

        Note: Conflicted fields are NOT included in merged_fields.
        They must be resolved separately by ConflictResolver.
        """
        merged = {}
        conflicts = []

        # Get all field names from all three versions
        all_fields = set(base.keys()) | set(local.keys()) | set(remote.keys())

        for field in all_fields:
            result = self.merge_field(
                field,
                base.get(field),
                local.get(field),
                remote.get(field),
            )

            if result.is_conflict():
                conflicts.append(field)
                # Don't include conflicted fields in merged
                # They'll be handled by ConflictResolver
            else:
                merged[field] = result.value

        return merged, conflicts

    def merge_issues(
        self,
        issues: dict[str, dict[str, Any]],
        base_issues: dict[str, dict[str, Any]],
        local_issues: dict[str, dict[str, Any]],
        remote_issues: dict[str, dict[str, Any]],
    ) -> tuple[dict[str, tuple[dict, list[str]]], list[str]]:
        """Merge multiple issues.

        Returns:
            (issue_results, deleted_issues)

        where issue_results[issue_id] = (merged_fields, conflict_fields)
        and deleted_issues is a list of issues removed on remote
        """
        results = {}
        deleted = []

        # Get all issue IDs from all three versions
        all_issues = (
            set(base_issues.keys())
            | set(local_issues.keys())
            | set(remote_issues.keys())
        )

        for issue_id in all_issues:
            base = base_issues.get(issue_id, {})
            local = local_issues.get(issue_id, {})
            remote = remote_issues.get(issue_id, {})

            # If issue was deleted remotely and not modified locally, skip it
            if not remote and base and not local:
                deleted.append(issue_id)
                continue

            merged, conflicts = self.merge_issue(issue_id, base, local, remote)
            results[issue_id] = (merged, conflicts)

        return results, deleted
