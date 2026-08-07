"""Field-level conflict detection helpers.

Extracted from SyncStateComparator._detect_field_conflicts to allow focused
testing and reuse.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Any

import structlog

from roadmap.core.services.sync.sync_conflict_resolver import ConflictField

logger = structlog.get_logger()


def _convert_enum_field(field_name: str, value: Any) -> Any:
    """Convert string enum values to enum types for status/priority fields.

    Args:
        field_name: Name of field ("status", "priority", etc.)
        value: Value to potentially convert

    Returns:
        Converted enum value, or original value if conversion fails/not applicable
    """
    if not isinstance(value, str) or value is None:
        return value

    if field_name == "status":
        try:
            from roadmap.common.constants import Status

            try:
                return Status(value)
            except (ValueError, KeyError):
                return Status(value.lower())
        except Exception as e:
            logger.debug(
                "enum_conversion_failed",
                operation="convert_enum_field",
                field="status",
                provided_value=value,
                error=str(e),
                action="Using fallback value",
            )
            return value

    if field_name == "priority":
        try:
            from roadmap.common.constants import Priority

            try:
                return Priority(value)
            except (ValueError, KeyError):
                return Priority(value.lower())
        except Exception as e:
            logger.debug(
                "enum_conversion_failed",
                operation="convert_enum_field",
                field="priority",
                provided_value=value,
                error=str(e),
                action="Using fallback value",
            )
            return value

    return value


def _get_field_value(obj: dict[str, Any] | object, field_name: str) -> Any:
    """Safely extract field value from dict or object."""
    if isinstance(obj, dict):
        return obj.get(field_name)
    return getattr(obj, field_name, None)


def detect_field_conflicts(
    local: object,
    remote: dict[str, Any] | object,
    fields_to_sync: list[str],
    extract_timestamp: Callable[[object, str], datetime | None] | None = None,
    logger: Any | None = None,
) -> list[ConflictField]:
    """Detect field-level conflicts between local and remote issues.

    Args:
        local: local Issue-like object
        remote: remote dict or object
        fields_to_sync: list of field names to compare
        extract_timestamp: optional callable to extract timestamps from remote
        logger: optional logger for debug/info

    Returns:
        list of ConflictField
    """
    conflicts: list[ConflictField] = []

    for field_name in fields_to_sync:
        try:
            local_val = getattr(local, field_name, None)
            remote_val = _get_field_value(remote, field_name)

            # Convert enum strings to types
            remote_val = _convert_enum_field(field_name, remote_val)

            if not local_val and not remote_val:
                continue

            if local_val != remote_val:
                local_updated = getattr(local, "updated", None)
                remote_updated: datetime | None = None
                if extract_timestamp is not None:
                    try:
                        remote_updated = extract_timestamp(remote, "updated_at")
                    except Exception:
                        remote_updated = None

                conflict_field = ConflictField(
                    field_name=field_name,
                    local_value=local_val,
                    remote_value=remote_val,
                    local_updated=local_updated,
                    remote_updated=remote_updated,
                )
                conflicts.append(conflict_field)

        except Exception as e:
            if logger is not None:
                try:
                    logger.debug(
                        "field_conflict_check_error",
                        field=field_name,
                        error=str(e),
                    )
                except Exception as logging_error:
                    logger.error(
                        "logger_failed",
                        operation="log_field_conflict_error",
                        error=str(logging_error),
                    )
            continue

    return conflicts
