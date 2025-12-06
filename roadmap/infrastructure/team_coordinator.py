"""Team Coordinator - Coordinates team and user-related operations

Extracted from RoadmapCore to reduce god object complexity.
Provides a focused API for all team and user management concerns.
"""

from __future__ import annotations

from roadmap.core.domain import Issue
from roadmap.infrastructure.user_operations import UserOperations


class TeamCoordinator:
    """Coordinates all team and user-related operations."""

    def __init__(self, user_ops: UserOperations):
        """Initialize coordinator with user operations manager.

        Args:
            user_ops: UserOperations instance
        """
        self._ops = user_ops

    def get_members(self) -> list[str]:
        """Get team members from GitHub repository.

        Returns:
            List of usernames if GitHub is configured, empty list otherwise
        """
        return self._ops.get_team_members()

    def get_current_user(self) -> str | None:
        """Get the current user from config.

        Returns:
            Current user's name from config if set, None otherwise
        """
        return self._ops.get_current_user()

    def get_assigned_issues(self, assignee: str) -> list[Issue]:
        """Get all issues assigned to a specific user."""
        return self._ops.get_assigned_issues(assignee)

    def get_my_issues(self) -> list[Issue]:
        """Get all issues assigned to the current user."""
        return self._ops.get_my_issues()

    def get_all_assigned_issues(self) -> dict[str, list[Issue]]:
        """Get all issues grouped by assignee.

        Returns:
            Dictionary mapping assignee usernames to their assigned issues
        """
        return self._ops.get_all_assigned_issues()

    def validate_assignee(self, assignee: str) -> tuple[bool, str]:
        """Validate an assignee using the identity management system.

        Args:
            assignee: Username to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        return self._ops.validate_assignee(assignee)

    def get_canonical_assignee(self, assignee: str) -> str:
        """Get the canonical form of an assignee name.

        Args:
            assignee: Input assignee name

        Returns:
            Canonical assignee name (may be same as input if no mapping exists)
        """
        return self._ops.get_canonical_assignee(assignee)

    def get_cached_team_members(self) -> list[str]:
        """Get team members with caching (5 minute cache)."""
        return self._ops.get_cached_team_members()
