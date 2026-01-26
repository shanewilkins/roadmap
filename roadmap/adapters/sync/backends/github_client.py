"""Thin wrapper around the project's `GitHubIssueClient`.

This module centralizes instantiation and error-safe access to the
GitHub API client used by the sync backend. It intentionally exposes
the same attribute/method surface as the underlying client via
delegation so it can be swapped-in with minimal changes.
"""

from typing import Any

from structlog import get_logger

logger = get_logger()


class GitHubClientWrapper:
    """Wraps the core `GitHubIssueClient` with safe initialization.

    Using a wrapper avoids importing heavy third-party dependencies
    in the larger backend module and makes it easier to test and
    stub behaviours.
    """

    def __init__(self, token: str | None):
        """Initialize GitHubClientWrapper.

        Args:
            token: GitHub API token.
        """
        self._client = None
        if token:
            try:
                # delayed import to reduce module import cost
                from roadmap.core.services.github.github_issue_client import (
                    GitHubIssueClient,
                )

                self._client = GitHubIssueClient(token)
            except Exception as e:
                logger.warning(
                    "github_client_init_failed",
                    error=str(e),
                    error_type=type(e).__name__,
                    severity="infrastructure",
                )

    def __getattr__(self, item: str) -> Any:
        """Get attribute from wrapped GitHub client."""
        if self._client is None:
            raise AttributeError(f"GitHub client not initialized, no attribute {item}")
        return getattr(self._client, item)

    def is_initialized(self) -> bool:
        """Check if the GitHub client is initialized.

        Returns:
            True if client is initialized, False otherwise.
        """
        return self._client is not None
