"""Detects field-level conflicts between local and remote issues.

Extracted from SyncStateComparator to separate conflict detection logic.
"""

from typing import Any

from structlog import get_logger

from roadmap.core.domain.issue import Issue
from roadmap.core.services.sync_conflict_resolver import ConflictField

logger = get_logger(__name__)


class FieldConflictDetector:
    """Detects field-level conflicts between local and remote issues."""

    def __init__(self, fields_to_sync: list[str] | None = None):
        """Initialize with fields to check for conflicts.

        Args:
            fields_to_sync: List of field names to check for conflicts
        """
        self.fields_to_sync = fields_to_sync or [
            "status",
            "priority",
            "content",
            "labels",
            "assignee",
        ]

    def detect_field_conflicts(
        self, local_issue: Issue, remote_issue: Any, extractors: dict | None = None
    ) -> list[ConflictField]:
        """Detect which fields differ between local and remote issues.

        Args:
            local_issue: Local Issue object
            remote_issue: Remote issue object or dict
            extractors: Optional dict of field→extractor function mappings

        Returns:
            List of ConflictField objects for conflicting fields
        """
        conflicting_fields = []

        if extractors is None:
            extractors = {}

        for field in self.fields_to_sync:
            try:
                # Get local value
                local_value = self._get_field_value(local_issue, field)

                # Get remote value
                remote_value = self._get_field_value(remote_issue, field)

                # Check for conflict
                if local_value != remote_value:
                    conflict_field = ConflictField(
                        field_name=field,
                        local_value=local_value,
                        remote_value=remote_value,
                        local_updated=getattr(local_issue, "updated", None),
                        remote_updated=getattr(remote_issue, "updated_at", None),
                    )
                    conflicting_fields.append(conflict_field)
                    logger.debug(
                        "conflict_detected_in_field",
                        field=field,
                        local_value=str(local_value)[:100],
                        remote_value=str(remote_value)[:100],
                    )

            except Exception as e:
                logger.warning(
                    "conflict_detection_error",
                    field=field,
                    error=str(e),
                )
                continue

        return conflicting_fields

    @staticmethod
    def _get_field_value(obj: Any, field: str) -> Any:
        """Get field value from object (handles dict and objects).

        Args:
            obj: Object or dict to extract field from
            field: Field name

        Returns:
            Field value, or None if not found
        """
        if obj is None:
            return None

        try:
            if isinstance(obj, dict):
                return obj.get(field)

            # Handle enums (e.g., Status enum)
            value = getattr(obj, field, None)
            if value is None:
                return None

            # If it's an enum with .value, use that
            if hasattr(value, "value"):
                return value.value

            # Handle special cases
            if field == "labels" and isinstance(value, list):
                return sorted(value) if value else []

            return value

        except Exception:
            return None
