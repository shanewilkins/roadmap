"""Backend factory interface for creating sync backends.

Defines contract for backend instantiation without importing adapter implementations.
Allows dynamic backend selection without layer violations.
"""

from abc import ABC, abstractmethod
from typing import Any


class SyncBackendFactoryInterface(ABC):
    """Contract for creating sync backends."""

    @abstractmethod
    def create_backend(
        self, backend_type: str, config: dict[str, Any]
    ) -> "SyncBackendInterface":
        """Create a sync backend instance.

        Args:
            backend_type: Type of backend to create (e.g., 'github', 'gitlab')
            config: Configuration dictionary for the backend

        Returns:
            SyncBackendInterface implementation

        Raises:
            ValueError: If backend_type is not supported
        """
        pass

    @abstractmethod
    def list_supported_backends(self) -> list[str]:
        """List all supported backend types.

        Returns:
            List of backend type identifiers
        """
        pass

    @abstractmethod
    def get_default_backend(self) -> str:
        """Get the default backend type.

        Returns:
            Backend type identifier
        """
        pass


class SyncBackendInterface(ABC):
    """Contract for sync backend implementations."""

    @abstractmethod
    def authenticate(self) -> bool:
        """Authenticate with the backend service.

        Returns:
            True if authentication successful
        """
        pass

    @abstractmethod
    def get_issues(self) -> dict[str, Any]:
        """Get issues from backend.

        Returns:
            Dictionary of issues
        """
        pass

    @abstractmethod
    def push_issue(self, local_issue: Any) -> bool:  # noqa: F841
        """Push a single issue to backend.

        Args:
            local_issue: Issue object to push

        Returns:
            True if successful
        """
        pass

    @abstractmethod
    def push_issues(self, issues: dict[str, Any]) -> bool:
        """Push issues to backend.

        Args:
            issues: Dictionary of issues to push

        Returns:
            True if successful
        """
        pass

    @abstractmethod
    def pull_issues(self) -> dict[str, Any]:
        """Pull issues from backend.

        Returns:
            Dictionary of pulled issues
        """
        pass

    @abstractmethod
    def get_conflict_resolution_options(self, conflict: Any) -> list[str]:  # noqa: F841
        """Get conflict resolution options.

        Args:
            conflict: Conflict object

        Returns:
            List of resolution options
        """
        pass

    @abstractmethod
    def resolve_conflict(self, conflict: Any, resolution: str) -> bool:  # noqa: F841
        """Resolve a conflict.

        Args:
            conflict: Conflict object
            resolution: Resolution option selected

        Returns:
            True if resolved successfully
        """
        pass

    @abstractmethod
    def get_backend_name(self) -> str:
        """Get the backend name.

        Returns:
            Backend identifier string
        """
        pass
