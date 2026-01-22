"""Gateway to GitHub adapter layer for core services.

This module mediates all core service access to GitHub adapter implementations,
ensuring proper layer separation between Core and Adapters layers.

All imports from roadmap.adapters.github are localized to this module.
Core services import from this gateway instead of directly from adapters.
"""

from typing import Any


class GitHubGateway:
    """Gateway for GitHub adapter operations.

    Provides a centralized interface for core services to access GitHub
    client and API functionality without direct adapter imports.
    """

    @staticmethod
    def get_github_client(config: Any) -> Any:
        """Get a GitHub client instance.

        Args:
            config: Configuration for the GitHub client

        Returns:
            GitHubClient instance
        """
        from roadmap.adapters.github.github import GitHubClient

        return GitHubClient(config)

    @staticmethod
    def get_github_api_error() -> type:
        """Get the GitHubAPIError exception class.

        Returns:
            GitHubAPIError exception class
        """
        from roadmap.adapters.github.handlers.base import GitHubAPIError

        return GitHubAPIError
