"""Tests for git hook auto-sync service."""

from unittest.mock import MagicMock, patch

from roadmap.core.services.git_hook_auto_sync_service import (
    GitHookAutoSyncConfig,
    GitHookAutoSyncService,
)


class TestGitHookAutoSyncConfig:
    """Test GitHookAutoSyncConfig class."""

    def test_init_defaults(self):
        """Test initialization with default values."""
        config = GitHookAutoSyncConfig()
        assert config.auto_sync_enabled is False
        assert config.sync_on_commit is False
        assert config.sync_on_checkout is False
        assert config.sync_on_merge is False
        assert config.confirm_before_sync is True
        assert config.force_local is False
        assert config.force_github is False

    def test_init_custom_values(self):
        """Test initialization with custom values."""
        config = GitHookAutoSyncConfig(
            auto_sync_enabled=True,
            sync_on_commit=True,
            sync_on_checkout=True,
            confirm_before_sync=False,
            force_local=True,
        )
        assert config.auto_sync_enabled is True
        assert config.sync_on_commit is True
        assert config.sync_on_checkout is True
        assert config.confirm_before_sync is False
        assert config.force_local is True
        assert config.sync_on_merge is False

    def test_to_dict(self):
        """Test converting config to dictionary."""
        config = GitHookAutoSyncConfig(
            auto_sync_enabled=True,
            sync_on_commit=True,
            confirm_before_sync=False,
        )
        result = config.to_dict()
        assert result["auto_sync_enabled"] is True
        assert result["sync_on_commit"] is True
        assert result["confirm_before_sync"] is False
        assert result["force_local"] is False

    def test_from_dict(self):
        """Test creating config from dictionary."""
        data = {
            "auto_sync_enabled": True,
            "sync_on_commit": True,
            "sync_on_checkout": False,
            "sync_on_merge": True,
            "confirm_before_sync": False,
            "force_local": False,
            "force_github": True,
        }
        config = GitHookAutoSyncConfig.from_dict(data)
        assert config.auto_sync_enabled is True
        assert config.sync_on_commit is True
        assert config.sync_on_checkout is False
        assert config.sync_on_merge is True
        assert config.confirm_before_sync is False
        assert config.force_github is True

    def test_from_dict_with_defaults(self):
        """Test from_dict with partial data uses defaults."""
        data = {"auto_sync_enabled": True}
        config = GitHookAutoSyncConfig.from_dict(data)
        assert config.auto_sync_enabled is True
        assert config.sync_on_commit is False
        assert config.confirm_before_sync is True

    def test_to_dict_from_dict_roundtrip(self):
        """Test roundtrip conversion."""
        original = GitHookAutoSyncConfig(
            auto_sync_enabled=True,
            sync_on_commit=True,
            sync_on_merge=True,
            confirm_before_sync=False,
        )
        data = original.to_dict()
        restored = GitHookAutoSyncConfig.from_dict(data)
        assert restored.auto_sync_enabled == original.auto_sync_enabled
        assert restored.sync_on_commit == original.sync_on_commit
        assert restored.confirm_before_sync == original.confirm_before_sync


class TestGitHookAutoSyncService:
    """Test GitHookAutoSyncService class."""

    def test_init_basic(self):
        """Test service initialization."""
        mock_core = MagicMock()
        with patch(
            "roadmap.core.services.git_hook_auto_sync_service.SyncMetadataService"
        ):
            service = GitHookAutoSyncService(mock_core)
            assert service.core == mock_core

    def test_get_config_defaults(self):
        """Test getting default config."""
        mock_core = MagicMock()
        with patch(
            "roadmap.core.services.git_hook_auto_sync_service.SyncMetadataService"
        ):
            service = GitHookAutoSyncService(mock_core)
            config = service.get_config()
            assert isinstance(config, GitHookAutoSyncConfig)
            assert config.auto_sync_enabled is False

    def test_set_config(self):
        """Test setting configuration."""
        mock_core = MagicMock()
        with patch(
            "roadmap.core.services.git_hook_auto_sync_service.SyncMetadataService"
        ):
            service = GitHookAutoSyncService(mock_core)
            config = GitHookAutoSyncConfig(auto_sync_enabled=True, sync_on_commit=True)
            service.set_config(config)
            assert service.get_config().auto_sync_enabled is True
        # Verify config was set
        assert service.get_config().auto_sync_enabled is True

    def test_config_persistence(self):
        """Test that config can be persisted and retrieved."""
        mock_core = MagicMock()
        with patch(
            "roadmap.core.services.git_hook_auto_sync_service.SyncMetadataService"
        ):
            service = GitHookAutoSyncService(mock_core)
            original_config = GitHookAutoSyncConfig(
                auto_sync_enabled=True,
                sync_on_commit=True,
                confirm_before_sync=False,
            )
            service.set_config(original_config)
            retrieved_config = service.get_config()
            assert (
                retrieved_config.auto_sync_enabled == original_config.auto_sync_enabled
            )
            assert retrieved_config.sync_on_commit == original_config.sync_on_commit

    def test_multiple_config_updates(self):
        """Test multiple configuration updates."""
        mock_core = MagicMock()
        with patch(
            "roadmap.core.services.git_hook_auto_sync_service.SyncMetadataService"
        ):
            service = GitHookAutoSyncService(mock_core)

            # First config
            config1 = GitHookAutoSyncConfig(auto_sync_enabled=True)
            service.set_config(config1)
            assert service.get_config().auto_sync_enabled is True

            # Second config
            config2 = GitHookAutoSyncConfig(
                auto_sync_enabled=False, sync_on_commit=True
            )
            service.set_config(config2)
            assert service.get_config().auto_sync_enabled is False
            assert service.get_config().sync_on_commit is True
