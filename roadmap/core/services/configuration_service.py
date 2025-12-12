"""Configuration management service for roadmap application.

Consolidates settings and credentials management into a single service layer,
providing unified access to application configuration and secrets.
"""

from pathlib import Path
from typing import Any

from roadmap.infrastructure.security.credentials import CredentialManager
from roadmap.settings import settings


class ConfigurationService:
    """Service for managing application configuration and credentials."""

    def __init__(self):
        """Initialize configuration service."""
        self.credential_manager = CredentialManager()
        self._settings = settings

    # ==================== Configuration Access ====================

    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get a configuration setting by key.

        Args:
            key: Configuration key (dot notation supported, e.g. 'database.path')
            default: Default value if setting not found

        Returns:
            Configuration value or default
        """
        try:
            return self._settings.get(key, default)
        except Exception:
            return default

    def get_github_config(self) -> dict[str, Any]:
        """Get GitHub integration configuration.

        Returns:
            GitHub configuration dictionary
        """
        return {
            "enabled": self.get_setting("github.enabled", False),
            "repo": self.get_setting("github.repo", ""),
            "sync_labels": self.get_setting("github.sync_labels", True),
        }

    # ==================== Credential Management ====================

    def get_github_token(self) -> str | None:
        """Retrieve GitHub token securely.

        Returns:
            GitHub token if found, None otherwise
        """
        return self.credential_manager.get_token()

    # ==================== Configuration Paths ====================

    def get_config_paths(self) -> dict[str, Path]:
        """Get configuration file paths.

        Returns:
            Dictionary of configuration file paths
        """
        from roadmap.settings import get_config_paths

        return get_config_paths()
