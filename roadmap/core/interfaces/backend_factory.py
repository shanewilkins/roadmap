"""Backend factory interface for creating sync backends.

Defines contract for backend instantiation without importing adapter implementations.
Allows dynamic backend selection without layer violations.

Updated to use Result<T, SyncError> pattern for explicit error handling.
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from roadmap.common.result import Result
    from roadmap.core.services.sync.sync_errors import SyncError

    from .sync_backend import SyncReport


class SyncBackendFactoryInterface(ABC):
    """Contract for creating sync backends."""

    @abstractmethod
    def create_backend(
        self,
        backend_type: str,  # noqa: F841
        config: dict[str, Any],  # noqa: F841
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
    """Contract for sync backend implementations.

    Updated to use Result<T, SyncError> for explicit error handling.
    """

    @abstractmethod
    def authenticate(self) -> "Result[bool, SyncError]":
        """Authenticate with the backend service.

        Returns:
            Ok(True) if authentication successful
            Err(SyncError) with error details
        """
        pass

    @abstractmethod
    def get_backend_name(self) -> str:
        """Get the backend name.

        Returns:
            Backend identifier string
        """
        pass

    @abstractmethod
    def get_issues(self) -> "Result[dict[str, Any], SyncError]":
        """Get issues from backend.

        Returns:
            Ok(dict) of issues on success
            Err(SyncError) with error details
        """
        pass

    @abstractmethod
    def push_issues(self, issues: dict[str, Any]) -> "Result[SyncReport, SyncError]":  # noqa: F841
        """Push issues to backend.

        Args:
            issues: Dictionary of issues to push

        Returns:
            Ok(SyncReport) with results on success
            Err(SyncError) with fatal error details
        """
        pass

    @abstractmethod
    def push_issue(self, local_issue: Any) -> "Result[bool, SyncError]":  # noqa: F841
        """Push a single issue to backend.

        Delegates to push_issues by default but can be overridden.

        Args:
            local_issue: Issue object to push

        Returns:
            Ok(True) if successful
            Err(SyncError) with error details
        """
        pass

    @abstractmethod
    def pull_issues(self, issue_ids: list[str]) -> "Result[SyncReport, SyncError]":
        """Pull issues from backend.

        Args:
            issue_ids: List of issue IDs to pull

        Returns:
            Ok(SyncReport) with results on success
            Err(SyncError) with fatal error details
        """
        pass

    @abstractmethod
    def pull_issue(self, issue_id: str) -> "Result[bool, SyncError]":
        """Pull a single issue from backend.

        Delegates to pull_issues by default but can be overridden.

        Args:
            issue_id: Issue ID to pull

        Returns:
            Ok(True) if successful
            Err(SyncError) with error details
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
