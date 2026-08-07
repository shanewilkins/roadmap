"""GitHub backend interface for core services.

Defines contract for GitHub operations without importing adapter implementations.
Allows core services to work with GitHub without layer violations.
"""

from abc import ABC, abstractmethod
from typing import Any

from roadmap.core.domain import Issue


class GitHubBackendInterface(ABC):
    """Contract for GitHub backend operations."""

    @abstractmethod
    def authenticate(self) -> bool:
        """Authenticate with GitHub.

        Returns:
            True if authentication successful, False otherwise
        """
        pass

    @abstractmethod
    def get_issues(self) -> dict[str, Any]:
        """Get all issues from GitHub repository.

        Returns:
            Dictionary mapping issue IDs to issue data
        """
        pass

    @abstractmethod
    def get_issue(self, issue_id: str) -> Any:
        """Get a specific issue from GitHub.

        Args:
            issue_id: The GitHub issue ID

        Returns:
            Issue data or None if not found
        """
        pass

    @abstractmethod
    def create_issue(self, issue: Issue) -> str:
        """Create an issue on GitHub.

        Args:
            issue: Issue domain object to create

        Returns:
            GitHub issue ID of created issue
        """
        pass

    @abstractmethod
    def update_issue(self, issue_id: str, issue: Issue) -> bool:
        """Update an issue on GitHub.

        Args:
            issue_id: GitHub issue ID
            issue: Updated issue data

        Returns:
            True if successful, False otherwise
        """
        pass

    @abstractmethod
    def close_issue(self, issue_id: str) -> bool:
        """Close an issue on GitHub.

        Args:
            issue_id: GitHub issue ID

        Returns:
            True if successful, False otherwise
        """
        pass

    @abstractmethod
    def list_repositories(self) -> list[str]:
        """List accessible repositories.

        Returns:
            List of repository identifiers
        """
        pass

    @abstractmethod
    def validate_credentials(self, token: str) -> bool:
        """Validate GitHub API credentials.

        Args:
            token: GitHub API token

        Returns:
            True if credentials are valid
        """
        pass
