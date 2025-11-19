"""Configuration management service for roadmap application.

Consolidates settings and credentials management into a single service layer,
providing unified access to application configuration and secrets.
"""

from pathlib import Path
from typing import Any

from roadmap.infrastructure.security.credentials import (
    CredentialManager,
    CredentialManagerError,
    mask_token,
)
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

    def set_setting(self, key: str, value: Any) -> None:
        """Set a configuration setting.

        Args:
            key: Configuration key
            value: Value to set
        """
        self._settings.set(key, value)

    def get_all_settings(self) -> dict[str, Any]:
        """Get all configuration settings.

        Returns:
            Dictionary of all settings
        """
        return self._settings.to_dict()

    def get_database_config(self) -> dict[str, Any]:
        """Get database configuration.

        Returns:
            Database configuration dictionary with path, timeout, backup_count
        """
        return {
            "path": self.get_setting("database.path", "~/.roadmap/roadmap.db"),
            "timeout": self.get_setting("database.timeout", 30.0),
            "backup_count": self.get_setting("database.backup_count", 5),
        }

    def get_logging_config(self) -> dict[str, Any]:
        """Get logging configuration.

        Returns:
            Logging configuration dictionary
        """
        return {
            "level": self.get_setting("logging.level", "INFO"),
            "to_file": self.get_setting("logging.to_file", True),
            "log_dir": self.get_setting("logging.log_dir", "~/.roadmap/logs"),
            "max_file_size": self.get_setting("logging.max_file_size", "10MB"),
            "backup_count": self.get_setting("logging.backup_count", 5),
        }

    def get_git_config(self) -> dict[str, Any]:
        """Get git configuration.

        Returns:
            Git configuration dictionary
        """
        return {
            "auto_sync": self.get_setting("git.auto_sync", True),
            "hooks_enabled": self.get_setting("git.hooks_enabled", True),
            "default_branch": self.get_setting("git.default_branch", "main"),
        }

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

    def get_cli_config(self) -> dict[str, Any]:
        """Get CLI configuration.

        Returns:
            CLI configuration dictionary
        """
        return {
            "default_editor": self.get_setting("cli.default_editor", "nano"),
            "pager": self.get_setting("cli.pager", "less"),
            "output_format": self.get_setting("cli.output_format", "table"),
            "color": self.get_setting("cli.color", True),
        }

    def get_defaults_config(self) -> dict[str, Any]:
        """Get default values configuration.

        Returns:
            Defaults configuration dictionary
        """
        return {
            "issue_type": self.get_setting("defaults.issue_type", "task"),
            "priority": self.get_setting("defaults.priority", "medium"),
            "status": self.get_setting("defaults.status", "open"),
        }

    def get_performance_config(self) -> dict[str, Any]:
        """Get performance configuration.

        Returns:
            Performance configuration dictionary
        """
        return {
            "cache_enabled": self.get_setting("performance.cache_enabled", True),
            "cache_size": self.get_setting("performance.cache_size", "100MB"),
            "cache_ttl": self.get_setting("performance.cache_ttl", 3600),
        }

    def get_export_config(self) -> dict[str, Any]:
        """Get export configuration.

        Returns:
            Export configuration dictionary
        """
        return {
            "default_format": self.get_setting("export.default_format", "csv"),
            "include_metadata": self.get_setting("export.include_metadata", False),
            "date_format": self.get_setting("export.date_format", "%Y-%m-%d"),
        }

    # ==================== Credential Management ====================

    def store_github_token(
        self, token: str, repo_info: dict[str, str] | None = None
    ) -> bool:
        """Store GitHub token securely.

        Args:
            token: GitHub personal access token
            repo_info: Optional repository information (owner, repo)

        Returns:
            True if stored successfully, False otherwise
        """
        try:
            return self.credential_manager.store_token(token, repo_info)
        except CredentialManagerError:
            return False

    def get_github_token(self) -> str | None:
        """Retrieve GitHub token securely.

        Returns:
            GitHub token if found, None otherwise
        """
        return self.credential_manager.get_token()

    def delete_github_token(self) -> bool:
        """Delete stored GitHub token.

        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            return self.credential_manager.delete_token()
        except CredentialManagerError:
            return False

    def is_credential_storage_available(self) -> bool:
        """Check if secure credential storage is available.

        Returns:
            True if credential storage is available, False otherwise
        """
        return self.credential_manager.is_available()

    def get_masked_token(self) -> str:
        """Get masked GitHub token for display purposes.

        Returns:
            Masked token showing only last 4 characters
        """
        token = self.get_github_token()
        return mask_token(token) if token else "Not configured"

    # ==================== Configuration Paths ====================

    def get_config_paths(self) -> dict[str, Path]:
        """Get configuration file paths.

        Returns:
            Dictionary of configuration file paths
        """
        from roadmap.settings import get_config_paths

        return get_config_paths()

    def get_home_config_dir(self) -> Path:
        """Get home directory configuration path.

        Returns:
            Path to ~/.roadmap
        """
        return Path.home() / ".roadmap"

    def get_local_config_dir(self) -> Path:
        """Get local project configuration path.

        Returns:
            Path to .roadmap in current directory
        """
        return Path.cwd() / ".roadmap"
