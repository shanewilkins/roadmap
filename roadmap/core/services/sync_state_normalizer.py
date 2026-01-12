"""Helpers for normalizing remote sync state and extracting timestamps.

This module contains pure helpers extracted from SyncStateComparator to
encapsulate timestamp parsing and remote object normalization so they can be
tested and reused independently.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any


def extract_timestamp(
    data: dict[str, Any] | object,
    timestamp_field: str = "updated_at",
    logger: Any | None = None,
) -> datetime | None:
    """Extract and parse a timestamp from remote issue data.

    Mirrors the behavior previously implemented on SyncStateComparator.
    Accepts an optional `logger` to preserve debug logging when available.
    """
    try:
        if isinstance(data, dict):
            ts = data.get(timestamp_field)
        else:
            ts = getattr(data, timestamp_field, None)

        if ts is None:
            return None

        if isinstance(ts, datetime):
            return ts

        if isinstance(ts, str):
            if ts.endswith("Z"):
                ts = ts[:-1] + "+00:00"
            return datetime.fromisoformat(ts)

        return None

    except Exception as e:  # pragma: no cover - defensive logging
        if logger is not None:
            try:
                logger.debug(
                    "timestamp_extraction_error",
                    field=timestamp_field,
                    error=str(e),
                )
            except Exception:
                pass
        return None


def normalize_remote_state(
    remote: Any, logger: Any | None = None
) -> dict[str, Any] | None:
    """Normalize remote representations into a plain dict for comparison.

    Accepts either a dict-like remote or an object. Returns a dict or None.
    """
    try:
        if isinstance(remote, dict) or remote is None:
            return remote

        return {
            "id": getattr(remote, "id", None),
            "title": getattr(remote, "title", None),
            "status": getattr(remote, "status", None),
            "assignee": getattr(remote, "assignee", None),
            "milestone": getattr(remote, "milestone", None),
            "description": getattr(remote, "headline", None)
            or getattr(remote, "description", None),
            "labels": list(getattr(remote, "labels", []) or []),
            "updated_at": getattr(remote, "updated_at", None)
            or getattr(remote, "updated", None),
        }
    except Exception as e:  # pragma: no cover - defensive logging
        if logger is not None:
            try:
                logger.debug("normalize_remote_state_error", error=str(e))
            except Exception:
                pass
        return None
