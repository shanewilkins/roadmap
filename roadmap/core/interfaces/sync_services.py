"""Specialized adapter interfaces for sync services.

Defines contracts for sync-specific operations without layer violations.
"""

from abc import ABC, abstractmethod
from typing import Any


class SyncLinkingServiceInterface(ABC):
    """Contract for sync linking operations.

    Handles linking/unlinking of local and remote issues during sync.
    """

    @abstractmethod
    def link_issues(self, local_id: str, remote_id: str) -> bool:  # noqa: F841
        """Link a local issue to a remote issue.

        Args:
            local_id: Local issue ID
            remote_id: Remote issue ID

        Returns:
            True if successful
        """
        pass

    @abstractmethod
    def unlink_issue(self, local_id: str) -> bool:  # noqa: F841
        """Unlink an issue from its remote mapping.

        Args:
            local_id: Local issue ID

        Returns:
            True if successful
        """
        pass

    @abstractmethod
    def get_linked_remote_id(self, local_id: str) -> str | None:  # noqa: F841
        """Get the remote issue ID for a local issue.

        Args:
            local_id: Local issue ID

        Returns:
            Remote issue ID or None if not linked
        """
        pass

    @abstractmethod
    def get_linked_local_id(self, remote_id: str) -> str | None:
        """Get the local issue ID for a remote issue.

        Args:
            remote_id: Remote issue ID

        Returns:
            Local issue ID or None if not linked
        """
        pass


class SyncCacheServiceInterface(ABC):
    """Contract for sync caching operations.

    Manages cache of remote state to reduce API calls.
    """

    @abstractmethod
    def cache_remote_issue(self, issue_id: str, issue_data: dict[str, Any]) -> bool:
        """Cache remote issue data.

        Args:
            issue_id: Issue identifier
            issue_data: Issue data dictionary

        Returns:
            True if successful
        """
        pass

    @abstractmethod
    def get_cached_remote_issue(self, issue_id: str) -> dict[str, Any] | None:
        """Get cached remote issue data.

        Args:
            issue_id: Issue identifier

        Returns:
            Issue data or None if not cached
        """
        pass

    @abstractmethod
    def invalidate_cache(self, issue_id: str | None = None) -> bool:
        """Invalidate cache.

        Args:
            issue_id: Specific issue ID to invalidate, or None for all

        Returns:
            True if successful
        """
        pass

    @abstractmethod
    def is_cache_fresh(self, issue_id: str) -> bool:
        """Check if cached data is still fresh.

        Args:
            issue_id: Issue identifier

        Returns:
            True if cache is valid and fresh
        """
        pass
