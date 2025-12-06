"""Validation Coordinator - Coordinates validation operations

Extracted from RoadmapCore to reduce god object complexity.
Provides a focused API for validation concerns.
"""

from __future__ import annotations

from roadmap.core.services import GitHubIntegrationService


class ValidationCoordinator:
    """Coordinates all validation operations."""

    def __init__(self, github_service: GitHubIntegrationService):
        """Initialize coordinator with GitHub service.

        Args:
            github_service: GitHubIntegrationService instance
        """
        self._github_service = github_service

    def get_github_config(self) -> tuple[str | None, str | None, str | None]:
        """Get GitHub configuration from config file and credentials.

        Returns:
            Tuple of (token, owner, repo) or (None, None, None) if not configured
        """
        return self._github_service.get_github_config()
