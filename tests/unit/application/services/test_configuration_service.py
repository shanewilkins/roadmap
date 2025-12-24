"""Unit tests for ConfigurationService."""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from roadmap.core.services.configuration_service import ConfigurationService


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
    service = ConfigurationService(credential_provider=mock_credential_manager)
    service._settings = mock_settings
    service.credential_provider = mock_credential_manager  # type: ignore[attr-defined]
    return service


class TestConfigurationServiceInit:
    """Test ConfigurationService initialization."""

    def test_init_creates_credential_manager(self):
        """Test initialization creates credential manager."""
        mock_provider = Mock()
        service = ConfigurationService(credential_provider=mock_provider)

        assert service.credential_manager is mock_provider


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


class TestConfigurationServiceGitHubConfig:
    """Test GitHub configuration methods."""

    def test_get_github_config_defaults(self, config_service):
        """Test getting GitHub config with defaults."""
        result = config_service.get_github_config()

        assert not result["enabled"]
        assert result["repo"] == ""
        assert result["sync_labels"]

    def test_get_github_config_custom_values(self, config_service, mock_settings):
        """Test getting GitHub config with custom values."""
        mock_settings.get.side_effect = lambda key, default: {
            "github.enabled": True,
            "github.repo": "owner/repo",
            "github.sync_labels": False,
        }.get(key, default)

        result = config_service.get_github_config()

        assert result["enabled"]
        assert result["repo"] == "owner/repo"
        assert not result["sync_labels"]


class TestConfigurationServiceCredentials:
    """Test credential management methods."""

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
