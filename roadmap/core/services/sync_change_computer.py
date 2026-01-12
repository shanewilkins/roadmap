"""Helpers to compute changes between baseline and local/remote states.

Extracted from `SyncStateComparator` to keep comparison logic testable
and allow the comparator to delegate responsibility.
"""

from __future__ import annotations

from typing import Any


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
                    except Exception:
                        pass
        except Exception as e:
            if logger is not None:
                try:
                    logger.warning(
                        "field_change_detection_error",
                        source="local",
                        field=field_name,
                        error=str(e),
                    )
                except Exception:
                    pass
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
    try:
        from roadmap.common.constants import Priority, Status
    except Exception:  # pragma: no cover - defensive import
        Priority = None  # type: ignore
        Status = None  # type: ignore

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

            if (
                field_name == "status"
                and remote_value is not None
                and Status is not None
            ):
                if isinstance(remote_value, str):
                    try:
                        remote_value = Status(remote_value)
                    except (ValueError, KeyError):
                        try:
                            remote_value = Status(remote_value.lower())
                        except (ValueError, KeyError):
                            pass

            if (
                field_name == "priority"
                and remote_value is not None
                and Priority is not None
            ):
                if isinstance(remote_value, str):
                    try:
                        remote_value = Priority(remote_value)
                    except (ValueError, KeyError):
                        try:
                            remote_value = Priority(remote_value.lower())
                        except (ValueError, KeyError):
                            pass

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
                    except Exception:
                        pass
        except Exception as e:
            if logger is not None:
                try:
                    logger.warning(
                        "field_change_detection_error_remote",
                        field=field_name,
                        error=str(e),
                    )
                except Exception:
                    pass
            continue

    return changes
