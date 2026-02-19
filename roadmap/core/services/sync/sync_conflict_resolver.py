"""Sync conflict resolution service.

Provides conflict detection and resolution logic that is backend-agnostic
and can be reused across all sync backends (GitHub, Vanilla Git, etc.).
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from structlog import get_logger

from roadmap.core.domain.issue import Issue

logger = get_logger()


class ConflictStrategy(Enum):
    """Strategy for resolving sync conflicts."""

    KEEP_LOCAL = "keep_local"
    KEEP_REMOTE = "keep_remote"
    AUTO_MERGE = "auto_merge"


@dataclass
class ConflictField:
    """Represents a field conflict between local and remote."""

    field_name: str
    local_value: Any
    remote_value: Any
    local_updated: datetime | None = None
    remote_updated: datetime | None = None

    def __str__(self) -> str:
        """Get human-readable representation."""
        return f"{self.field_name}: local={self.local_value!r} vs remote={self.remote_value!r}"


@dataclass
class Conflict:
    """Represents all conflicts for a single issue."""

    issue_id: str
    local_issue: Issue
    remote_issue: dict[str, Any]
    fields: list[ConflictField]
    local_updated: datetime
    remote_updated: datetime | None = None

    def __str__(self) -> str:
        """Get human-readable representation."""
        field_list = ", ".join(str(f) for f in self.fields)
        return f"Issue {self.issue_id}: {field_list}"

    @property
    def field_names(self) -> list[str]:
        """Get list of conflicting field names.

        Returns:
            List of field names that conflict
        """
        return [f.field_name for f in self.fields]


class SyncConflictResolver:
    """Resolves conflicts between local and remote issues.

    Backend-agnostic resolution logic that applies the same strategy
    regardless of sync backend (GitHub, Git, etc.). Handles three
    strategies:
    - KEEP_LOCAL: Always use local version
    - KEEP_REMOTE: Always use remote version
    - AUTO_MERGE: Prefer newer version, with fallback to local if equal
    """

    def __init__(self):
        """Initialize the conflict resolver."""
        self.logger = get_logger()
        self.logger.debug("sync_conflict_resolver_initialized")

    def resolve(
        self,
        conflict: Conflict,
        strategy: ConflictStrategy = ConflictStrategy.AUTO_MERGE,
    ) -> Issue:
        """Resolve a single conflict using the specified strategy.

        Args:
            conflict: The Conflict to resolve
            strategy: The strategy to use (default: AUTO_MERGE)

        Returns:
            Resolved Issue instance

        Raises:
            ValueError: If conflict data is invalid
        """
        self.logger.debug(
            "resolve_conflict",
            issue_id=conflict.issue_id,
            strategy=strategy.value,
            fields=conflict.field_names,
        )

        try:
            if strategy == ConflictStrategy.KEEP_LOCAL:
                self.logger.debug("keeping_local_version", issue_id=conflict.issue_id)
                return conflict.local_issue

            elif strategy == ConflictStrategy.KEEP_REMOTE:
                self.logger.debug("keeping_remote_version", issue_id=conflict.issue_id)
                return self._convert_remote_to_local(
                    conflict.issue_id, conflict.remote_issue
                )

            elif strategy == ConflictStrategy.AUTO_MERGE:
                self.logger.debug("auto_merging", issue_id=conflict.issue_id)
                return self._auto_merge(conflict)

            else:
                raise ValueError(f"Unknown conflict strategy: {strategy}")

        except Exception as e:
            self.logger.error(
                "conflict_resolution_failed",
                issue_id=conflict.issue_id,
                strategy=strategy.value,
                error=str(e),
            )
            raise

    def resolve_batch(
        self,
        conflicts: list[Conflict],
        strategy: ConflictStrategy = ConflictStrategy.AUTO_MERGE,
    ) -> list[Issue]:
        """Resolve multiple conflicts using the same strategy.

        Args:
            conflicts: List of Conflicts to resolve
            strategy: The strategy to use for all conflicts

        Returns:
            List of resolved Issues

        Raises:
            ValueError: If any conflict resolution fails
        """
        self.logger.info(
            "resolve_batch_conflicts",
            count=len(conflicts),
            strategy=strategy.value,
        )

        resolved = []
        errors = []

        for conflict in conflicts:
            try:
                resolved_issue = self.resolve(conflict, strategy)
                resolved.append(resolved_issue)
            except Exception as e:
                error_msg = f"Failed to resolve {conflict.issue_id}: {str(e)}"
                self.logger.warning("conflict_resolution_error", reason=error_msg)
                errors.append(error_msg)

        if errors:
            self.logger.error("batch_resolution_had_errors", error_count=len(errors))
            if len(errors) == len(conflicts):
                # All failed - raise
                raise ValueError(f"Failed to resolve all conflicts: {errors}")

        self.logger.info("batch_conflicts_resolved", count=len(resolved))
        return resolved

    def _auto_merge(self, conflict: Conflict) -> Issue:
        """Automatically merge local and remote versions.

        Strategy:
        1. If local is newer: use local
        2. If remote is newer: use remote
        3. If timestamps are equal: use local (prefer local on tie)
        4. If local field is unchanged: use remote (remote is newer change)

        Args:
            conflict: The Conflict to merge

        Returns:
            Merged Issue instance

        Raises:
            ValueError: If merge logic encounters invalid data
        """
        self.logger.debug(
            "auto_merge_start",
            issue_id=conflict.issue_id,
            local_updated=conflict.local_updated.isoformat(),
            remote_updated=(
                conflict.remote_updated.isoformat() if conflict.remote_updated else None
            ),
        )

        # No remote timestamp means we can't compare - keep local
        if conflict.remote_updated is None:
            self.logger.debug(
                "no_remote_timestamp_keeping_local", issue_id=conflict.issue_id
            )
            return conflict.local_issue

        # If local is newer, keep it
        if conflict.local_updated > conflict.remote_updated:
            self.logger.debug(
                "local_is_newer_keeping_local",
                issue_id=conflict.issue_id,
                local_age_seconds=(
                    conflict.local_updated - conflict.remote_updated
                ).total_seconds(),
            )
            return conflict.local_issue

        # If remote is newer, prefer remote
        if conflict.remote_updated > conflict.local_updated:
            self.logger.debug(
                "remote_is_newer_keeping_remote",
                issue_id=conflict.issue_id,
                remote_age_seconds=(
                    conflict.remote_updated - conflict.local_updated
                ).total_seconds(),
            )
            return self._convert_remote_to_local(
                conflict.issue_id, conflict.remote_issue
            )

        # Timestamps are equal - use local (no change indicated)
        self.logger.debug(
            "timestamps_equal_keeping_local",
            issue_id=conflict.issue_id,
        )
        return conflict.local_issue

    def _convert_remote_to_local(
        self, issue_id: str, remote_issue: dict[str, Any]
    ) -> Issue:
        """Convert remote issue dict to local Issue instance.

        Reconstructs a local Issue from remote data. This is called when
        the remote version is newer and should be applied locally.

        Args:
            issue_id: The local issue ID
            remote_issue: The remote issue data dict

        Returns:
            Issue instance with remote data applied

        Raises:
            ValueError: If remote data cannot be converted to Issue
        """
        from datetime import datetime

        from roadmap.core.domain.issue import (
            Issue,
            IssueType,
            Priority,
        )
        from roadmap.core.domain.issue import (
            Status as IssueStatus,
        )

        self.logger.debug(
            "converting_remote_to_local",
            issue_id=issue_id,
            remote_id=remote_issue.get("id"),
        )

        try:
            # Convert remote dict to Issue
            # Remote dict should contain at least: id, title, status
            # Optional: description, priority, assignee, milestone, labels, updated_at, etc.

            title = remote_issue.get("title", "")
            status_str = remote_issue.get("status", "todo")
            priority_str = remote_issue.get("priority", "medium")

            # Convert status string to Status enum
            try:
                status = IssueStatus(status_str)
            except (ValueError, KeyError):
                status = IssueStatus.TODO

            # Convert priority string to Priority enum
            try:
                priority = Priority(priority_str)
            except (ValueError, KeyError):
                priority = Priority.MEDIUM

            # Parse timestamps
            updated_at_str = remote_issue.get("updated_at")
            if updated_at_str:
                try:
                    if isinstance(updated_at_str, str):
                        updated = datetime.fromisoformat(
                            updated_at_str.replace("Z", "+00:00")
                        )
                    else:
                        updated = updated_at_str
                except (ValueError, AttributeError):
                    updated = datetime.now(UTC)
            else:
                updated = datetime.now(UTC)

            created_at_str = remote_issue.get("created_at")
            if created_at_str:
                try:
                    if isinstance(created_at_str, str):
                        created = datetime.fromisoformat(
                            created_at_str.replace("Z", "+00:00")
                        )
                    else:
                        created = created_at_str
                except (ValueError, AttributeError):
                    created = updated
            else:
                created = updated

            # Construct Issue with remote data
            issue = Issue(
                id=issue_id,
                title=title,
                status=status,
                priority=priority,
                issue_type=IssueType(remote_issue.get("issue_type", "other")),
                created=created,
                updated=updated,
                milestone=remote_issue.get("milestone"),
                assignee=remote_issue.get("assignee"),
                labels=remote_issue.get("labels", []),
                content=remote_issue.get("description", ""),
                estimated_hours=remote_issue.get("estimated_hours"),
                due_date=remote_issue.get("due_date"),
                # Add other fields as needed
            )

            self.logger.debug(
                "remote_converted_to_local",
                issue_id=issue_id,
                title=title,
                status=status.value,
            )

            return issue

        except Exception as e:
            self.logger.error(
                "remote_conversion_failed",
                issue_id=issue_id,
                error=str(e),
            )
            raise ValueError(
                f"Failed to convert remote issue {issue_id}: {str(e)}"
            ) from e

    def detect_field_conflicts(
        self,
        local: Issue,
        remote: dict[str, Any],
        fields_to_check: list[str] | None = None,
    ) -> list[ConflictField]:
        """Detect field-level conflicts between local and remote.

        Args:
            local: The local Issue
            remote: The remote issue dict
            fields_to_check: Specific fields to check (default: common fields)

        Returns:
            List of ConflictFields representing conflicts

        Raises:
            ValueError: If field data types don't match for comparison
        """
        if fields_to_check is None:
            fields_to_check = ["title", "status", "priority", "content"]

        conflicts = []

        for field_name in fields_to_check:
            try:
                local_val = getattr(local, field_name, None)
                remote_val = remote.get(field_name)

                # Treat empty strings as equivalent to None for comparison purposes
                local_normalized = (
                    None
                    if (
                        local_val is None
                        or (isinstance(local_val, str) and local_val.strip() == "")
                    )
                    else local_val
                )
                remote_normalized = (
                    None
                    if (
                        remote_val is None
                        or (isinstance(remote_val, str) and remote_val.strip() == "")
                    )
                    else remote_val
                )

                # If both normalize to None, no conflict
                if local_normalized is None and remote_normalized is None:
                    continue

                # If values differ after normalization, it's a conflict
                if local_normalized != remote_normalized:
                    conflict_field = ConflictField(
                        field_name=field_name,
                        local_value=local_val,
                        remote_value=remote_val,
                        local_updated=local.updated,
                        remote_updated=(
                            remote.get("updated_at")
                            if isinstance(remote.get("updated_at"), datetime)
                            else None
                        ),
                    )
                    conflicts.append(conflict_field)
                    self.logger.debug(
                        "field_conflict_detected",
                        issue_id=local.id,
                        field=field_name,
                        local=local_val,
                        remote=remote_val,
                    )

            except Exception as e:
                self.logger.warning(
                    "field_conflict_detection_error",
                    issue_id=local.id,
                    field=field_name,
                    error=str(e),
                )
                continue

        return conflicts
