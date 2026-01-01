"""Protocol definitions for dependency injection and service abstraction."""

from typing import Protocol

from .state_managers import (
    IssueStateManager,
    MilestoneStateManager,
    ProjectStateManager,
    QueryStateManager,
    SyncStateManager,
)
from .sync_backend import (
    SyncBackendInterface,
    SyncConflict,
    SyncReport,
)

__all__ = [
    "CredentialProvider",
    "AssigneeValidator",
    "ProjectStateManager",
    "MilestoneStateManager",
    "IssueStateManager",
    "SyncStateManager",
    "QueryStateManager",
    "SyncBackendInterface",
    "SyncConflict",
    "SyncReport",
]


class CredentialProvider(Protocol):
    """Abstract interface for credential management.

    Defines the contract that any credential provider must implement.
    Allows services to work with different credential backends without
    depending on concrete implementations.
    """

    def get_token(self) -> str | None:
        """Retrieve a stored token.

        Returns:
            Token string if found, None otherwise
        """
        ...

    def store_token(self, token: str, repo_info: dict[str, str] | None = None) -> bool:
        """Store a token securely.

        Args:
            token: Token to store
            repo_info: Optional repository information (owner, repo)

        Returns:
            True if stored successfully, False otherwise
        """
        ...

    def delete_token(self) -> bool:
        """Delete a stored token.

        Returns:
            True if deleted successfully, False otherwise
        """
        ...

    def is_available(self) -> bool:
        """Check if the credential provider is available on this system.

        Returns:
            True if available, False otherwise
        """
        ...


class AssigneeValidator(Protocol):
    """Abstract interface for assignee validation.

    Allows core services to validate assignees using different backends
    (GitHub, local rules, identity systems) without hard coupling to
    any specific implementation.
    """

    def validate(self, assignee: str) -> tuple[bool, str, str]:  # noqa: F841
        """Validate an assignee.

        Args:
            assignee: Username to validate

        Returns:
            Tuple of (is_valid, error_message, canonical_id)
        """
        ...
