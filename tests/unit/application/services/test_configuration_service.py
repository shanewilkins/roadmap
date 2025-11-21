"""Unit tests for ConfigurationService."""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from roadmap.application.services.configuration_service import ConfigurationService


@pytest.fixture
def mock_settings():
    """Create a mock settings object."""
    settings = Mock()
    settings.get = Mock(side_effect=lambda key, default=None: default)
    settings.set = Mock()
    settings.to_dict = Mock(return_value={})
    return settings


@pytest.fixture
def mock_credential_manager():
    """Create a mock credential manager."""
    manager = Mock()
    manager.store_token = Mock(return_value=True)
    manager.get_token = Mock(return_value=None)
    manager.delete_token = Mock(return_value=True)
    manager.is_available = Mock(return_value=True)
    return manager


@pytest.fixture
def config_service(mock_settings, mock_credential_manager):
    """Create a ConfigurationService with mocked dependencies."""
    with patch(
        "roadmap.application.services.configuration_service.CredentialManager",
        return_value=mock_credential_manager,
    ):
        with patch(
            "roadmap.application.services.configuration_service.settings", mock_settings
        ):
            service = ConfigurationService()
            service._settings = mock_settings
            service.credential_manager = mock_credential_manager
            return service


class TestConfigurationServiceInit:
    """Test ConfigurationService initialization."""

    def test_init_creates_credential_manager(self):
        """Test initialization creates credential manager."""
        with patch(
            "roadmap.application.services.configuration_service.CredentialManager"
        ) as mock_cm:
            service = ConfigurationService()

            mock_cm.assert_called_once()
            assert service.credential_manager is not None


class TestConfigurationServiceSettings:
    """Test settings access methods."""

    def test_get_setting_returns_value(self, config_service, mock_settings):
        """Test getting a setting returns value."""
        mock_settings.get.side_effect = (
            lambda key, default: "test_value" if key == "test.key" else default
        )

        result = config_service.get_setting("test.key")

        assert result == "test_value"
        mock_settings.get.assert_called_with("test.key", None)

    def test_get_setting_returns_default(self, config_service, mock_settings):
        """Test getting non-existent setting returns default."""
        mock_settings.get.side_effect = lambda key, default: default

        result = config_service.get_setting("nonexistent.key", "default_value")

        assert result == "default_value"

    def test_get_setting_handles_exception(self, config_service, mock_settings):
        """Test get_setting handles exceptions gracefully."""
        mock_settings.get.side_effect = Exception("Settings error")

        result = config_service.get_setting("test.key", "fallback")

        assert result == "fallback"

    def test_set_setting(self, config_service, mock_settings):
        """Test setting a configuration value."""
        config_service.set_setting("test.key", "new_value")

        mock_settings.set.assert_called_once_with("test.key", "new_value")

    def test_get_all_settings(self, config_service, mock_settings):
        """Test getting all settings."""
        expected_dict = {"key1": "value1", "key2": "value2"}
        mock_settings.to_dict.return_value = expected_dict

        result = config_service.get_all_settings()

        assert result == expected_dict
        mock_settings.to_dict.assert_called_once()


class TestConfigurationServiceDatabaseConfig:
    """Test database configuration methods."""

    def test_get_database_config_defaults(self, config_service):
        """Test getting database config with defaults."""
        result = config_service.get_database_config()

        assert "path" in result
        assert "timeout" in result
        assert "backup_count" in result
        assert result["path"] == "~/.roadmap/roadmap.db"
        assert result["timeout"] == 30.0
        assert result["backup_count"] == 5

    def test_get_database_config_custom_values(self, config_service, mock_settings):
        """Test getting database config with custom values."""
        mock_settings.get.side_effect = lambda key, default: {
            "database.path": "/custom/path/db.sqlite",
            "database.timeout": 60.0,
            "database.backup_count": 10,
        }.get(key, default)

        result = config_service.get_database_config()

        assert result["path"] == "/custom/path/db.sqlite"
        assert result["timeout"] == 60.0
        assert result["backup_count"] == 10


class TestConfigurationServiceLoggingConfig:
    """Test logging configuration methods."""

    def test_get_logging_config_defaults(self, config_service):
        """Test getting logging config with defaults."""
        result = config_service.get_logging_config()

        assert result["level"] == "INFO"
        assert result["to_file"] is True
        assert result["log_dir"] == "~/.roadmap/logs"
        assert result["max_file_size"] == "10MB"
        assert result["backup_count"] == 5

    def test_get_logging_config_custom_values(self, config_service, mock_settings):
        """Test getting logging config with custom values."""
        mock_settings.get.side_effect = lambda key, default: {
            "logging.level": "DEBUG",
            "logging.to_file": False,
            "logging.log_dir": "/var/log/roadmap",
            "logging.max_file_size": "50MB",
            "logging.backup_count": 3,
        }.get(key, default)

        result = config_service.get_logging_config()

        assert result["level"] == "DEBUG"
        assert result["to_file"] is False


class TestConfigurationServiceGitConfig:
    """Test git configuration methods."""

    def test_get_git_config_defaults(self, config_service):
        """Test getting git config with defaults."""
        result = config_service.get_git_config()

        assert result["auto_sync"] is True
        assert result["hooks_enabled"] is True
        assert result["default_branch"] == "main"

    def test_get_git_config_custom_values(self, config_service, mock_settings):
        """Test getting git config with custom values."""
        mock_settings.get.side_effect = lambda key, default: {
            "git.auto_sync": False,
            "git.hooks_enabled": False,
            "git.default_branch": "master",
        }.get(key, default)

        result = config_service.get_git_config()

        assert result["auto_sync"] is False
        assert result["hooks_enabled"] is False
        assert result["default_branch"] == "master"


class TestConfigurationServiceGitHubConfig:
    """Test GitHub configuration methods."""

    def test_get_github_config_defaults(self, config_service):
        """Test getting GitHub config with defaults."""
        result = config_service.get_github_config()

        assert result["enabled"] is False
        assert result["repo"] == ""
        assert result["sync_labels"] is True

    def test_get_github_config_custom_values(self, config_service, mock_settings):
        """Test getting GitHub config with custom values."""
        mock_settings.get.side_effect = lambda key, default: {
            "github.enabled": True,
            "github.repo": "owner/repo",
            "github.sync_labels": False,
        }.get(key, default)

        result = config_service.get_github_config()

        assert result["enabled"] is True
        assert result["repo"] == "owner/repo"
        assert result["sync_labels"] is False


class TestConfigurationServiceCLIConfig:
    """Test CLI configuration methods."""

    def test_get_cli_config_defaults(self, config_service):
        """Test getting CLI config with defaults."""
        result = config_service.get_cli_config()

        assert result["default_editor"] == "nano"
        assert result["pager"] == "less"
        assert result["output_format"] == "table"
        assert result["color"] is True

    def test_get_cli_config_custom_values(self, config_service, mock_settings):
        """Test getting CLI config with custom values."""
        mock_settings.get.side_effect = lambda key, default: {
            "cli.default_editor": "vim",
            "cli.pager": "more",
            "cli.output_format": "json",
            "cli.color": False,
        }.get(key, default)

        result = config_service.get_cli_config()

        assert result["default_editor"] == "vim"
        assert result["output_format"] == "json"


class TestConfigurationServiceDefaultsConfig:
    """Test defaults configuration methods."""

    def test_get_defaults_config_defaults(self, config_service):
        """Test getting defaults config with defaults."""
        result = config_service.get_defaults_config()

        assert result["issue_type"] == "task"
        assert result["priority"] == "medium"
        assert result["status"] == "open"

    def test_get_defaults_config_custom_values(self, config_service, mock_settings):
        """Test getting defaults config with custom values."""
        mock_settings.get.side_effect = lambda key, default: {
            "defaults.issue_type": "bug",
            "defaults.priority": "high",
            "defaults.status": "todo",
        }.get(key, default)

        result = config_service.get_defaults_config()

        assert result["issue_type"] == "bug"
        assert result["priority"] == "high"


class TestConfigurationServicePerformanceConfig:
    """Test performance configuration methods."""

    def test_get_performance_config_defaults(self, config_service):
        """Test getting performance config with defaults."""
        result = config_service.get_performance_config()

        assert result["cache_enabled"] is True
        assert result["cache_size"] == "100MB"
        assert result["cache_ttl"] == 3600

    def test_get_performance_config_custom_values(self, config_service, mock_settings):
        """Test getting performance config with custom values."""
        mock_settings.get.side_effect = lambda key, default: {
            "performance.cache_enabled": False,
            "performance.cache_size": "500MB",
            "performance.cache_ttl": 7200,
        }.get(key, default)

        result = config_service.get_performance_config()

        assert result["cache_enabled"] is False
        assert result["cache_size"] == "500MB"


class TestConfigurationServiceExportConfig:
    """Test export configuration methods."""

    def test_get_export_config_defaults(self, config_service):
        """Test getting export config with defaults."""
        result = config_service.get_export_config()

        assert result["default_format"] == "csv"
        assert result["include_metadata"] is False
        assert result["date_format"] == "%Y-%m-%d"

    def test_get_export_config_custom_values(self, config_service, mock_settings):
        """Test getting export config with custom values."""
        mock_settings.get.side_effect = lambda key, default: {
            "export.default_format": "json",
            "export.include_metadata": True,
            "export.date_format": "%m/%d/%Y",
        }.get(key, default)

        result = config_service.get_export_config()

        assert result["default_format"] == "json"
        assert result["include_metadata"] is True


class TestConfigurationServiceCredentials:
    """Test credential management methods."""

    def test_store_github_token_success(self, config_service, mock_credential_manager):
        """Test successfully storing GitHub token."""
        result = config_service.store_github_token("test_token_123")

        assert result is True
        mock_credential_manager.store_token.assert_called_once_with(
            "test_token_123", None
        )

    def test_store_github_token_with_repo_info(
        self, config_service, mock_credential_manager
    ):
        """Test storing GitHub token with repo info."""
        repo_info = {"owner": "test", "repo": "repo"}
        result = config_service.store_github_token("token", repo_info)

        assert result is True
        mock_credential_manager.store_token.assert_called_once_with("token", repo_info)

    def test_store_github_token_failure(self, config_service, mock_credential_manager):
        """Test storing GitHub token handles failure."""
        from roadmap.infrastructure.security.credentials import CredentialManagerError

        mock_credential_manager.store_token.side_effect = CredentialManagerError(
            "Error"
        )

        result = config_service.store_github_token("token")

        assert result is False

    def test_get_github_token(self, config_service, mock_credential_manager):
        """Test getting GitHub token."""
        mock_credential_manager.get_token.return_value = "test_token_123"

        result = config_service.get_github_token()

        assert result == "test_token_123"
        mock_credential_manager.get_token.assert_called_once()

    def test_get_github_token_not_found(self, config_service, mock_credential_manager):
        """Test getting GitHub token when not found."""
        mock_credential_manager.get_token.return_value = None

        result = config_service.get_github_token()

        assert result is None

    def test_delete_github_token_success(self, config_service, mock_credential_manager):
        """Test deleting GitHub token."""
        result = config_service.delete_github_token()

        assert result is True
        mock_credential_manager.delete_token.assert_called_once()

    def test_delete_github_token_failure(self, config_service, mock_credential_manager):
        """Test deleting GitHub token handles failure."""
        from roadmap.infrastructure.security.credentials import CredentialManagerError

        mock_credential_manager.delete_token.side_effect = CredentialManagerError(
            "Error"
        )

        result = config_service.delete_github_token()

        assert result is False

    def test_is_credential_storage_available(
        self, config_service, mock_credential_manager
    ):
        """Test checking credential storage availability."""
        result = config_service.is_credential_storage_available()

        assert result is True
        mock_credential_manager.is_available.assert_called_once()

    def test_get_masked_token_with_token(self, config_service, mock_credential_manager):
        """Test getting masked token when token exists."""
        mock_credential_manager.get_token.return_value = "ghp_1234567890abcdef"

        result = config_service.get_masked_token()

        assert "****" in result
        assert result != "ghp_1234567890abcdef"

    def test_get_masked_token_without_token(
        self, config_service, mock_credential_manager
    ):
        """Test getting masked token when no token configured."""
        mock_credential_manager.get_token.return_value = None

        result = config_service.get_masked_token()

        assert result == "Not configured"


class TestConfigurationServicePaths:
    """Test configuration path methods."""

    def test_get_config_paths(self, config_service):
        """Test getting configuration paths."""
        with patch("roadmap.settings.get_config_paths") as mock_get_paths:
            mock_get_paths.return_value = {
                "user": Path("/home/user/.roadmap"),
                "local": Path("/project/.roadmap"),
            }

            result = config_service.get_config_paths()

            assert "user" in result
            assert "local" in result
            mock_get_paths.assert_called_once()

    def test_get_home_config_dir(self, config_service):
        """Test getting home config directory."""
        result = config_service.get_home_config_dir()

        assert isinstance(result, Path)
        assert result.name == ".roadmap"
        assert result.parent == Path.home()

    def test_get_local_config_dir(self, config_service):
        """Test getting local config directory."""
        result = config_service.get_local_config_dir()

        assert isinstance(result, Path)
        assert result.name == ".roadmap"
        assert result.parent == Path.cwd()
