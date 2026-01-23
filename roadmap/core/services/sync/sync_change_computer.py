"""Helpers to compute changes between baseline and local/remote states.

Extracted from `SyncStateComparator` to keep comparison logic testable
and allow the comparator to delegate responsibility.
"""

from __future__ import annotations

from typing import Any

import structlog

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


def compute_changes(
    baseline: Any | None,
    local: Any,
    *,
    logger: Any | None = None,
) -> dict[str, Any]:
    """Compute what changed between baseline and local issue.

    This mirrors the behavior from the original comparator implementation.
    """
    changes: dict[str, Any] = {}

    field_map = {
        "status": (
            "status",
            lambda x: x.status.value if hasattr(x.status, "value") else str(x.status),
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
                changes[field_name] = {"from": baseline_value, "to": local_value}
                if logger is not None:
                    try:
                        logger.debug(
                            "field_changed_detected",
                            source="local",
                            field=field_name,
                            baseline=baseline_value,
                            current=local_value,
                        )
                    except Exception as logging_error:
                        logger.error(
                            "logger_failed",
                            operation="compute_changes (debug logging)",
                            error=str(logging_error),
                        )
        except Exception as e:
            if logger is not None:
                try:
                    logger.warning(
                        "field_change_detection_error",
                        source="local",
                        field=field_name,
                        error=str(e),
                    )
                except Exception as logging_error:
                    logger.error(
                        "logger_failed",
                        operation="compute_changes (warning logging)",
                        error=str(logging_error),
                    )
            continue

    return changes


def compute_changes_remote(
    baseline: Any | None,
    remote: Any,
    *,
    logger: Any | None = None,
) -> dict[str, Any]:
    """Compute what changed between baseline and remote issue.

    Accepts either dict-like or object remote representations.
    """
    changes: dict[str, Any] = {}

    def get_remote_field(field_name: str, default: Any = None) -> Any:
        if isinstance(remote, dict):
            return remote.get(field_name, default)
        return getattr(remote, field_name, default)

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

            # Convert enum strings to types
            remote_value = _convert_enum_field(field_name, remote_value)

            if baseline_value != remote_value:
                changes[field_name] = {"from": baseline_value, "to": remote_value}
                if logger is not None:
                    try:
                        logger.debug(
                            "field_changed_detected",
                            source="remote",
                            field=field_name,
                            baseline=baseline_value,
                            current=remote_value,
                        )
                    except Exception as logging_error:
                        logger.error(
                            "logger_failed",
                            operation="compute_changes_remote (debug logging)",
                            error=str(logging_error),
                        )
        except Exception as e:
            if logger is not None:
                try:
                    logger.warning(
                        "field_change_detection_error_remote",
                        field=field_name,
                        error=str(e),
                    )
                except Exception as logging_error:
                    logger.error(
                        "logger_failed",
                        operation="compute_changes_remote (warning logging)",
                        error=str(logging_error),
                    )
            continue

    return changes
