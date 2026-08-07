"""Status change parsing and extraction helpers for sync operations.

This module provides utilities for parsing and extracting information from
status change strings in the format "old_status -> new_status".
"""

from typing import Any


def parse_status_change(change_str: str) -> str | None:
    """Parse and validate change string in format 'old -> new'.

    Args:
        change_str: Change string in format "old -> new"

    Returns:
        The new status string (stripped), or None if format is invalid
    """
    if not isinstance(change_str, str) or " -> " not in change_str:
        return None

    try:
        parts = change_str.split(" -> ")
        if len(parts) != 2:
            return None
        return parts[1].strip()
    except (IndexError, AttributeError):
        return None


def extract_issue_status_update(
    status_change: str,
) -> dict[str, Any] | None:
    """Extract and validate issue status update from change string.

    Args:
        status_change: Change string in format "old -> new"

    Returns:
        Dict with 'github_state' and 'status_enum', or None if invalid
    """
    from roadmap.common.constants import Status

    new_status = parse_status_change(status_change)
    if new_status is None:
        return None

    try:
        # Validate that it's a valid status
        status_enum = Status(new_status)
        # Map local status to GitHub state (closed -> closed, others -> open)
        github_state = "closed" if new_status == Status.CLOSED.value else "open"
        return {
            "github_state": github_state,
            "status_enum": status_enum,
        }
    except (ValueError, KeyError):
        # Invalid status - skip the update
        return None


def extract_milestone_status_update(
    status_change: str,
) -> dict[str, Any] | None:
    """Extract and validate milestone status update from change string.

    Args:
        status_change: Change string in format "old -> new"

    Returns:
        Dict with 'github_state' and 'status_enum', or None if invalid
    """
    from roadmap.common.constants import MilestoneStatus

    new_status = parse_status_change(status_change)
    if new_status is None:
        return None

    github_state = "closed" if new_status == "closed" else "open"

    try:
        status_enum = MilestoneStatus(new_status)
        return {
            "github_state": github_state,
            "status_enum": status_enum,
        }
    except (ValueError, KeyError):
        return None
