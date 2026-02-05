"""Configuration management service for roadmap application.

Consolidates settings and credentials management into a single service layer,
providing unified access to application configuration and secrets.
"""

from pathlib import Path
from typing import Any

import structlog

from roadmap.core.interfaces import CredentialProvider
from roadmap.settings import settings

logger = structlog.get_logger()


class ConfigurationService:
    """Service for managing application configuration and credentials."""

    def __init__(self, credential_provider: CredentialProvider | None = None):
        """Initialize configuration service.

        Args:
            credential_provider: Optional credential provider implementation.
                                If None, defaults to infrastructure CredentialManager.
        """
        if credential_provider is None:
            from roadmap.infrastructure.security.credentials import CredentialManager

            credential_provider = CredentialManager()

        self.credential_manager = credential_provider
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
        except Exception as e:
            logger.debug(
                "config_get_failed",
                operation="get_config",
                key=key,
                error=str(e),
                action="Returning default value",
            )
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

    def get_sync_config(self) -> dict[str, Any]:
        """Get sync operation configuration.

        Returns:
            Sync configuration dictionary including duplicate detection thresholds
        """
        return {
            "enable_duplicate_detection": self.get_setting(
                "sync.enable_duplicate_detection", True
            ),
            "duplicate_title_threshold": self.get_setting(
                "sync.duplicate_title_threshold", 0.90
            ),
            "duplicate_content_threshold": self.get_setting(
                "sync.duplicate_content_threshold", 0.85
            ),
            "duplicate_auto_resolve_threshold": self.get_setting(
                "sync.duplicate_auto_resolve_threshold", 0.95
            ),
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
