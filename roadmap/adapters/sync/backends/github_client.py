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

    def __init__(
        self, token: str | None, owner: str | None = None, repo: str | None = None
    ):
        """Initialize GitHubClientWrapper.

        Args:
            token: GitHub API token.
            owner: Repository owner (username or organization).
            repo: Repository name.
        """
        self._client = None
        if token:
            try:
                # delayed import to reduce module import cost
                from roadmap.core.services.github.github_issue_client import (
                    GitHubIssueClient,
                )

                self._client = GitHubIssueClient(token)
                # Store owner and repo for later use if needed
                self._owner = owner
                self._repo = repo
            except Exception as e:
                logger.warning(
                    "github_client_init_failed",
                    error=str(e),
                    error_type=type(e).__name__,
                    severity="infrastructure",
                )

    def __getattr__(self, item: str) -> Any:
        """Get attribute from wrapped GitHub client.

        Lazy-initializes client on first method access if not already initialized.
        """
        # Lazy initialization: if client is None, try to initialize it now
        if self._client is None:
            try:
                # Try to get token from environment or credential manager
                import os

                token = os.getenv("GITHUB_TOKEN")

                if not token:
                    from roadmap.infrastructure.security.credentials import (
                        CredentialManager,
                    )

                    cred_manager = CredentialManager()  # type: ignore[call-arg]
                    token = cred_manager.get_token()

                if token:
                    from roadmap.core.services.github.github_issue_client import (
                        GitHubIssueClient,
                    )

                    self._client = GitHubIssueClient(token)
                    logger.debug("github_client_lazy_initialized")
            except Exception as e:
                logger.debug(
                    "github_client_lazy_init_failed",
                    error=str(e),
                    error_type=type(e).__name__,
                )

        if self._client is None:
            raise AttributeError(f"GitHub client not initialized, no attribute {item}")
        return getattr(self._client, item)

    def is_initialized(self) -> bool:
        """Check if the GitHub client is initialized.

        Returns:
            True if client is initialized, False otherwise.
        """
        return self._client is not None
