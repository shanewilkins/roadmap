"""Protocol definitions for dependency injection and service abstraction."""

from importlib import import_module
from typing import Protocol


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

    def store_token(self, token: str, repo_info: dict[str, str] | None = None) -> bool:  # noqa: F841
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


# Define CredentialProvider before compatibility re-exports: state_storage
# reaches services that import this protocol during package initialization.
from .assignee_validator import AssigneeValidator  # noqa: E402
from .github import GitHubBackendInterface  # noqa: E402
from .parsers import (  # noqa: E402
    FrontmatterParserInterface,
    IssueParserInterface,
    MilestoneParserInterface,
    ProjectParserInterface,
)
from .persistence import (  # noqa: E402
    FileNotFound,
    GitHistoryError,
    PersistenceInterface,
)
from .state_managers import (  # noqa: E402
    IssueStateManager,
    MilestoneStateManager,
    ProjectStateManager,
    QueryStateManager,
    SyncStateManager,
)


def __getattr__(name: str):  # noqa: ANN202
    if name in {"SyncBackendInterface", "SyncConflict", "SyncReport"}:
        return getattr(import_module(f"{__name__}.sync_backend"), name)
    raise AttributeError(name)


__all__ = [
    "CredentialProvider",
    "AssigneeValidator",
    "ProjectStateManager",
    "MilestoneStateManager",
    "IssueStateManager",
    "SyncStateManager",
    "QueryStateManager",
    "PersistenceInterface",
    "IssueParserInterface",
    "FrontmatterParserInterface",
    "MilestoneParserInterface",
    "ProjectParserInterface",
    "GitHubBackendInterface",
    "FileNotFound",
    "GitHistoryError",
]
