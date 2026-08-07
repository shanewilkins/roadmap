"""Normalizes remote issue state for comparison with local state.

Extracted from SyncStateComparator to separate state normalization logic.
"""

from datetime import datetime
from typing import Any

from structlog import get_logger

logger = get_logger(__name__)


class RemoteStateNormalizer:
    """Normalizes remote issue state for sync operations."""

    @staticmethod
    def normalize_remote_state(remote: Any) -> dict[str, Any] | None:
        """Normalize remote issue state to standard format.

        Args:
            remote: Remote issue object or dict

        Returns:
            Normalized state dict, or None if invalid
        """
        if remote is None:
            return None

        try:
            if isinstance(remote, dict):
                return remote.copy()

            # Convert object to dict
            state = {}

            # Extract standard fields
            for field in [
                "id",
                "status",
                "title",
                "content",
                "labels",
                "assignee",
                "milestone",
            ]:
                value = getattr(remote, field, None)
                if value is not None:
                    state[field] = value

            # Handle timestamps
            for ts_field in ["updated_at", "created_at"]:
                if hasattr(remote, ts_field):
                    state[ts_field] = getattr(remote, ts_field)

            return state if state else None

        except Exception as e:
            logger.debug(
                "normalize_remote_state_failed",
                error=str(e),
                remote_type=type(remote).__name__,
            )
            return None

    @staticmethod
    def extract_timestamp(
        remote: Any, field_name: str = "updated_at"
    ) -> datetime | None:
        """Extract timestamp from remote issue.

        Args:
            remote: Remote issue object or dict
            field_name: Name of timestamp field (default: "updated_at")

        Returns:
            Datetime object, or None if not found/invalid
        """
        if remote is None:
            return None

        try:
            if isinstance(remote, dict):
                value = remote.get(field_name)
            else:
                value = getattr(remote, field_name, None)

            if value is None:
                return None

            if isinstance(value, datetime):
                return value

            if isinstance(value, str):
                # Try ISO format
                try:
                    return datetime.fromisoformat(value.replace("Z", "+00:00"))
                except (ValueError, AttributeError):
                    return None

            return None

        except Exception as e:
            logger.debug(
                "normalize_state_failed",
                operation="normalize_state",
                error=str(e),
                action="Returning None",
            )
            return None
