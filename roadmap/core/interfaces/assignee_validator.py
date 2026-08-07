"""Assignee validator interface.

Defines the contract for assignee validation implementations that can be
swapped based on the configured sync backend.
"""

from typing import Protocol


class AssigneeValidator(Protocol):
    """Protocol for assignee validation.

    Implementations validate assignees according to their backend's rules.
    For example, GitHub validator checks against repository collaborators,
    while a no-op validator always accepts any assignee.
    """

    def validate(self, assignee: str) -> tuple[bool, str]:
        """Validate an assignee.

        Args:
            assignee: Username to validate

        Returns:
            Tuple of (is_valid, error_message)
            - (True, "") if valid
            - (False, error_message) if invalid
        """
        ...

    def get_canonical_assignee(self, assignee: str) -> str:
        """Get the canonical form of an assignee name.

        Args:
            assignee: Input assignee name

        Returns:
            Canonical assignee name (may be same as input if no mapping exists)
        """
        ...
