"""Team Coordinator - Coordinates team and user-related operations

Extracted from RoadmapCore to reduce god object complexity.
Provides a focused API for all team and user management concerns.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from roadmap.common.errors.error_standards import OperationType, safe_operation
from roadmap.common.logging import get_logger
from roadmap.core.domain import Issue
from roadmap.infrastructure.user_operations import UserOperations

if TYPE_CHECKING:
    from roadmap.infrastructure.core import RoadmapCore

logger = get_logger(__name__)


class TeamCoordinator:
    """Coordinates all team and user-related operations."""

    def __init__(self, user_ops: UserOperations, core: RoadmapCore | None = None):
        """Initialize coordinator with user operations manager.

        Args:
            user_ops: UserOperations instance
            core: RoadmapCore instance for initialization checks
        """
        self._ops = user_ops
        self._core = core

    @safe_operation(OperationType.READ, "Team")
    def get_members(self) -> list[str]:
        """Get team members from GitHub repository.

        Returns:
            List of usernames if GitHub is configured, empty list otherwise
        """
        logger.info("getting_team_members")
        return self._ops.get_team_members()

    @safe_operation(OperationType.READ, "User")
    def get_current_user(self) -> str | None:
        """Get the current user from config.

        Returns:
            Current user's name from config if set, None otherwise
        """
        logger.info("getting_current_user")
        return self._ops.get_current_user()

    @safe_operation(OperationType.READ, "Issue")
    def get_assigned_issues(self, assignee: str) -> list[Issue]:
        """Get all issues assigned to a specific user."""
        logger.info("getting_assigned_issues", assignee=assignee)
        return self._ops.get_assigned_issues(assignee)

    @safe_operation(OperationType.READ, "Issue")
    def get_my_issues(self) -> list[Issue]:
        """Get all issues assigned to the current user."""
        logger.info("getting_my_issues")
        return self._ops.get_my_issues()

    @safe_operation(OperationType.READ, "Issue")
    def get_all_assigned_issues(self) -> dict[str, list[Issue]]:
        """Get all issues grouped by assignee.

        Returns:
            Dictionary mapping assignee usernames to their assigned issues
        """
        logger.info("getting_all_assigned_issues")
        return self._ops.get_all_assigned_issues()

    @safe_operation(OperationType.READ, "Assignee")
    def validate_assignee(self, assignee: str) -> tuple[bool, str]:
        """Validate an assignee using the identity management system.

        Args:
            assignee: Username to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        logger.info("validating_assignee", assignee=assignee)
        return self._ops.validate_assignee(assignee)

    @safe_operation(OperationType.READ, "Assignee")
    def get_canonical_assignee(self, assignee: str) -> str:
        """Get the canonical form of an assignee name.

        Args:
            assignee: Input assignee name

        Returns:
            Canonical assignee name (may be same as input if no mapping exists)
        """
        logger.info("getting_canonical_assignee", assignee=assignee)
        return self._ops.get_canonical_assignee(assignee)

    @safe_operation(OperationType.READ, "Team")
    def get_cached_team_members(self) -> list[str]:
        """Get team members with caching (5 minute cache)."""
        logger.info("getting_cached_team_members")
        return self._ops.get_cached_team_members()
