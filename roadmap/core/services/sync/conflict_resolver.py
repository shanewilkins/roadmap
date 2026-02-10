"""Conflict resolution strategies for handling merge conflicts.

When three-way merge detects a true conflict (both sides changed
differently), this module applies field-level strategies to decide
what to do with that conflict.
"""

from enum import StrEnum
from typing import Any


class ConflictResolutionStrategy(StrEnum):
    """Strategy for resolving a conflict."""

    FLAG_FOR_REVIEW = "flag_for_review"  # Return None, needs manual review
    GITHUB_WINS = "github_wins"  # Use remote value
    LOCAL_WINS = "local_wins"  # Use local value
    MERGE_UNION = "merge_union"  # Combine lists (for labels)
    MERGE_APPEND = "merge_append"  # Append both (for comments/description)


class ConflictResolver:
    """Applies field-level strategies to resolve conflicts.

    Each field has a predefined strategy for what to do when
    the three-way merge detects a conflict on that field.

    Critical fields (status, assignee) are flagged for review.
    Non-critical fields (labels, comments) are auto-merged.
    """

    # Field-level rules (from the sync implementation plan)
    RULES = {
        # Critical fields - flag for review (user must decide)
        "status": ConflictResolutionStrategy.FLAG_FOR_REVIEW,
        "assignee": ConflictResolutionStrategy.FLAG_FOR_REVIEW,
        "milestone": ConflictResolutionStrategy.FLAG_FOR_REVIEW,
        # Merge-friendly fields
        "labels": ConflictResolutionStrategy.MERGE_UNION,
        "description": ConflictResolutionStrategy.MERGE_APPEND,
        "comments": ConflictResolutionStrategy.MERGE_APPEND,
        # Metadata - GitHub is authoritative
        "created_at": ConflictResolutionStrategy.GITHUB_WINS,
        "updated_at": ConflictResolutionStrategy.GITHUB_WINS,
        # Default: flag for review if not in RULES
    }

    def resolve_conflict(
        self,
        field: str,
        base: Any,
        local: Any,
        remote: Any,
    ) -> tuple[Any, bool]:
        """Resolve a single field conflict.

        Args:
            field: Field name
            base: Base value (from last sync)
            local: Local value (current local state)
            remote: Remote value (current remote state)

        Returns:
            (resolved_value, is_flagged)
            where is_flagged=True means this needs manual review
        """
        strategy = self.RULES.get(field, ConflictResolutionStrategy.FLAG_FOR_REVIEW)

        if strategy == ConflictResolutionStrategy.FLAG_FOR_REVIEW:
            # Return None to indicate this needs manual review
            return None, True

        elif strategy == ConflictResolutionStrategy.GITHUB_WINS:
            return remote, False

        elif strategy == ConflictResolutionStrategy.LOCAL_WINS:
            return local, False

        elif strategy == ConflictResolutionStrategy.MERGE_UNION:
            # For labels: combine both lists, deduplicate
            local_list = local if isinstance(local, list) else [local] if local else []
            remote_list = (
                remote if isinstance(remote, list) else [remote] if remote else []
            )
            merged = list(set(local_list + remote_list))
            return merged, False

        elif strategy == ConflictResolutionStrategy.MERGE_APPEND:
            # For comments/description: append both with source markers
            local_str = str(local) if local else ""
            remote_str = str(remote) if remote else ""
            result = f"{local_str}\n\n--- REMOTE CHANGES ---\n{remote_str}"
            # Still flag for manual cleanup of markers
            return result, True

        else:
            # Unexpected strategy, flag for review
            return None, True

    def resolve_issue_conflicts(
        self,
        issue_id: str,
        base: dict[str, Any],
        local: dict[str, Any],
        remote: dict[str, Any],
        conflict_fields: list[str],
    ) -> tuple[dict[str, Any], list[str]]:
        """Resolve all conflicts in an issue.

        Args:
            issue_id: Issue identifier (for logging)
            base: Base version of issue
            local: Local version of issue
            remote: Remote version of issue
            conflict_fields: List of field names that have conflicts

        Returns:
            (resolved_fields, list_of_fields_still_flagged)

        The resolved_fields dict contains fields that were
        auto-resolved. Fields still flagged need manual review.
        """
        resolved = {}
        flagged = []

        for field in conflict_fields:
            value, is_flagged = self.resolve_conflict(
                field,
                base.get(field),
                local.get(field),
                remote.get(field),
            )

            if is_flagged:
                flagged.append(field)
                # Don't include in resolved yet; needs manual review
            else:
                if value is not None:
                    resolved[field] = value

        return resolved, flagged

    def has_critical_conflicts(self, flagged_fields: list[str]) -> bool:
        """Check if flagged fields include critical ones.

        Critical fields are status, assignee, milestone.
        If these have conflicts, user MUST review.
        """
        critical = {"status", "assignee", "milestone"}
        return any(field in critical for field in flagged_fields)

    def get_strategy_for_field(self, field: str) -> ConflictResolutionStrategy:
        """Get the strategy for a specific field."""
        return self.RULES.get(field, ConflictResolutionStrategy.FLAG_FOR_REVIEW)
