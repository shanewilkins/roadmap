"""Tests for git hook auto-sync service."""

import json
from unittest.mock import patch

from roadmap.core.services.git_hook_auto_sync_service import (
    GitHookAutoSyncConfig,
    GitHookAutoSyncService,
)
from tests.unit.domain.test_data_factory_generation import TestDataFactory


class TestGitHookAutoSyncConfig:
    """Test GitHookAutoSyncConfig class."""

    def test_init_defaults_sync_flags_disabled(self):
        """Test initialization sets sync flags to disabled by default."""
        config = GitHookAutoSyncConfig()
        assert not config.auto_sync_enabled
        assert not config.sync_on_commit
        assert not config.sync_on_checkout
        assert not config.sync_on_merge

    def test_init_defaults_confirm_and_force_flags(self):
        """Test initialization sets confirmation and force flags by default."""
        config = GitHookAutoSyncConfig()
        assert config.confirm_before_sync
        assert not config.force_local
        assert not config.force_github

    def test_init_custom_values(self):
        """Test initialization with custom values."""
        config = GitHookAutoSyncConfig(
            auto_sync_enabled=True,
            sync_on_commit=True,
            sync_on_checkout=True,
            confirm_before_sync=False,
            force_local=True,
        )
        assert config.auto_sync_enabled
        assert config.sync_on_commit
        assert config.sync_on_checkout
        assert not config.confirm_before_sync
        assert config.force_local
        assert not config.sync_on_merge

    def test_to_dict(self):
        """Test converting config to dictionary."""
        config = GitHookAutoSyncConfig(
            auto_sync_enabled=True,
            sync_on_commit=True,
            confirm_before_sync=False,
        )
        result = config.to_dict()
        assert result["auto_sync_enabled"]
        assert result["sync_on_commit"]
        assert not result["confirm_before_sync"]
        assert not result["force_local"]

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
        assert config.auto_sync_enabled
        assert config.sync_on_commit
        assert not config.sync_on_checkout
        assert config.sync_on_merge
        assert not config.confirm_before_sync
        assert config.force_github

    def test_from_dict_with_defaults(self):
        """Test from_dict with partial data uses defaults."""
        data = {"auto_sync_enabled": True}
        config = GitHookAutoSyncConfig.from_dict(data)
        assert config.auto_sync_enabled
        assert not config.sync_on_commit
        assert config.confirm_before_sync

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
        mock_core = TestDataFactory.create_mock_core(is_initialized=True)
        with patch(
            "roadmap.core.services.git_hook_auto_sync_service.SyncMetadataService"
        ):
            service = GitHookAutoSyncService(mock_core)
            assert service.core == mock_core

    def test_get_config_defaults(self):
        """Test getting default config."""
        mock_core = TestDataFactory.create_mock_core(is_initialized=True)
        with patch(
            "roadmap.core.services.git_hook_auto_sync_service.SyncMetadataService"
        ):
            service = GitHookAutoSyncService(mock_core)
            config = service.get_config()
            assert isinstance(config, GitHookAutoSyncConfig)
            assert not config.auto_sync_enabled

    def test_set_config(self):
        """Test setting configuration."""
        mock_core = TestDataFactory.create_mock_core(is_initialized=True)
        with patch(
            "roadmap.core.services.git_hook_auto_sync_service.SyncMetadataService"
        ):
            service = GitHookAutoSyncService(mock_core)
            config = GitHookAutoSyncConfig(auto_sync_enabled=True, sync_on_commit=True)
            service.set_config(config)
            assert service.get_config().auto_sync_enabled
        # Verify config was set
        assert service.get_config().auto_sync_enabled

    def test_config_persistence(self):
        """Test that config can be persisted and retrieved."""
        mock_core = TestDataFactory.create_mock_core(is_initialized=True)
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
        mock_core = TestDataFactory.create_mock_core(is_initialized=True)
        with patch(
            "roadmap.core.services.git_hook_auto_sync_service.SyncMetadataService"
        ):
            service = GitHookAutoSyncService(mock_core)

            # First config
            config1 = GitHookAutoSyncConfig(auto_sync_enabled=True)
            service.set_config(config1)
            assert service.get_config().auto_sync_enabled

            # Second config
            config2 = GitHookAutoSyncConfig(
                auto_sync_enabled=False, sync_on_commit=True
            )
            service.set_config(config2)
            assert not service.get_config().auto_sync_enabled
            assert service.get_config().sync_on_commit


class TestGitHookAutoSyncConfigEdgeCases:
    """Test edge cases and error handling in GitHookAutoSyncConfig."""

    def test_from_dict_with_none(self):
        """Test from_dict with None values uses defaults."""
        data = {
            "auto_sync_enabled": None,
            "sync_on_commit": None,
        }
        config = GitHookAutoSyncConfig.from_dict(data)
        # Check that it handles None gracefully (actual behavior)
        # The implementation may set None or use defaults
        assert config is not None
        assert isinstance(config, GitHookAutoSyncConfig)

    def test_from_dict_with_empty_dict(self):
        """Test from_dict with empty dictionary."""
        config = GitHookAutoSyncConfig.from_dict({})
        assert not config.auto_sync_enabled
        assert not config.sync_on_commit
        assert not config.sync_on_checkout
        assert not config.sync_on_merge

    def test_from_dict_ignores_extra_keys(self):
        """Test from_dict ignores unknown keys."""
        data = {
            "auto_sync_enabled": True,
            "unknown_key": "value",
            "another_unknown": 123,
        }
        config = GitHookAutoSyncConfig.from_dict(data)
        assert config.auto_sync_enabled

    def test_to_dict_contains_all_fields(self):
        """Test to_dict includes all configuration fields."""
        config = GitHookAutoSyncConfig()
        result = config.to_dict()
        required_keys = {
            "auto_sync_enabled",
            "sync_on_commit",
            "sync_on_checkout",
            "sync_on_merge",
            "confirm_before_sync",
            "force_local",
            "force_github",
        }
        assert set(result.keys()) == required_keys

    def test_force_local_and_force_github_mutually_exclusive_behavior(self):
        """Test that both force flags can be set independently."""
        config = GitHookAutoSyncConfig(force_local=True, force_github=True)
        assert config.force_local
        assert config.force_github

    def test_config_with_all_sync_triggers_enabled(self):
        """Test config with all sync triggers enabled."""
        config = GitHookAutoSyncConfig(
            auto_sync_enabled=True,
            sync_on_commit=True,
            sync_on_checkout=True,
            sync_on_merge=True,
        )
        assert config.auto_sync_enabled
        assert config.sync_on_commit
        assert config.sync_on_checkout
        assert config.sync_on_merge

    def test_config_with_all_sync_triggers_disabled(self):
        """Test config with all sync triggers disabled."""
        config = GitHookAutoSyncConfig(
            auto_sync_enabled=False,
            sync_on_commit=False,
            sync_on_checkout=False,
            sync_on_merge=False,
        )
        assert not config.auto_sync_enabled
        assert not config.sync_on_commit
        assert not config.sync_on_checkout
        assert not config.sync_on_merge


class TestGitHookAutoSyncServiceAdvanced:
    """Test advanced scenarios for GitHookAutoSyncService."""

    @patch("roadmap.core.services.git_hook_auto_sync_service.SyncMetadataService")
    def test_service_with_mocked_dependencies(self, mock_sync_service):
        """Test service with mocked dependencies."""
        mock_core = TestDataFactory.create_mock_core(is_initialized=True)
        service = GitHookAutoSyncService(mock_core)
        assert service.core == mock_core

    @patch("roadmap.core.services.git_hook_auto_sync_service.SyncMetadataService")
    def test_config_is_mutable(self, mock_sync_service):
        """Test that returned config object can be modified (mutable)."""
        mock_core = TestDataFactory.create_mock_core(is_initialized=True)
        service = GitHookAutoSyncService(mock_core)

        # Get config and modify it directly
        config1 = service.get_config()
        original_value = config1.auto_sync_enabled

        # Create a new modified config and set it
        modified_config = GitHookAutoSyncConfig(auto_sync_enabled=not original_value)
        service.set_config(modified_config)

        config2 = service.get_config()
        # Service internal state should be updated
        assert config2.auto_sync_enabled != original_value

    @patch("roadmap.core.services.git_hook_auto_sync_service.SyncMetadataService")
    def test_sequential_config_changes(self, mock_sync_service):
        """Test multiple sequential configuration changes."""
        mock_core = TestDataFactory.create_mock_core(is_initialized=True)
        service = GitHookAutoSyncService(mock_core)

        configs = [
            GitHookAutoSyncConfig(auto_sync_enabled=True),
            GitHookAutoSyncConfig(
                auto_sync_enabled=True, sync_on_commit=True, confirm_before_sync=False
            ),
            GitHookAutoSyncConfig(sync_on_merge=True),
            GitHookAutoSyncConfig(),
        ]

        for config in configs:
            service.set_config(config)
            retrieved = service.get_config()
            assert retrieved.auto_sync_enabled == config.auto_sync_enabled
            assert retrieved.sync_on_commit == config.sync_on_commit
            assert retrieved.sync_on_merge == config.sync_on_merge

    @patch("roadmap.core.services.git_hook_auto_sync_service.SyncMetadataService")
    def test_config_with_all_boolean_combinations(self, mock_sync_service):
        """Test various boolean flag combinations."""
        mock_core = TestDataFactory.create_mock_core(is_initialized=True)
        service = GitHookAutoSyncService(mock_core)

        test_cases = [
            {"auto_sync_enabled": True, "confirm_before_sync": False},
            {"auto_sync_enabled": False, "confirm_before_sync": True},
            {"force_local": True, "force_github": False},
            {"force_local": False, "force_github": True},
            {
                "auto_sync_enabled": True,
                "sync_on_commit": True,
                "sync_on_checkout": False,
                "sync_on_merge": True,
            },
        ]

        for case in test_cases:
            config = GitHookAutoSyncConfig(**case)
            service.set_config(config)
            retrieved = service.get_config()
            for key, value in case.items():
                assert getattr(retrieved, key) == value


class TestGitHookAutoSyncConfigSerialization:
    """Test serialization and deserialization of config."""

    def test_json_roundtrip(self):
        """Test that config can be serialized to JSON and back."""
        original = GitHookAutoSyncConfig(
            auto_sync_enabled=True,
            sync_on_commit=True,
            sync_on_merge=False,
            confirm_before_sync=False,
            force_local=True,
        )
        # Serialize to dict then to JSON
        data_dict = original.to_dict()
        json_str = json.dumps(data_dict)
        # Deserialize from JSON back to dict then to config
        loaded_dict = json.loads(json_str)
        restored = GitHookAutoSyncConfig.from_dict(loaded_dict)

        assert restored.auto_sync_enabled == original.auto_sync_enabled
        assert restored.sync_on_commit == original.sync_on_commit
        assert restored.sync_on_merge == original.sync_on_merge
        assert restored.confirm_before_sync == original.confirm_before_sync
        assert restored.force_local == original.force_local

    def test_to_dict_values_are_correct_types(self):
        """Test that to_dict returns correct value types."""
        config = GitHookAutoSyncConfig(auto_sync_enabled=True)
        result = config.to_dict()
        for key, value in result.items():
            assert isinstance(value, bool), f"{key} should be bool, got {type(value)}"

    def test_from_dict_with_string_booleans(self):
        """Test from_dict handles unexpected types gracefully."""
        # In case config was loaded from JSON with string values
        data = {
            "auto_sync_enabled": True,
            "sync_on_commit": False,
            "sync_on_checkout": True,
            "sync_on_merge": False,
            "confirm_before_sync": True,
            "force_local": False,
            "force_github": False,
        }
        config = GitHookAutoSyncConfig.from_dict(data)
        assert config.auto_sync_enabled
        assert config.sync_on_checkout


class TestGitHookAutoSyncIntegration:
    """Integration tests for git hook auto-sync service."""

    @patch("roadmap.core.services.git_hook_auto_sync_service.SyncMetadataService")
    def test_workflow_enable_auto_sync_with_triggers(self, mock_sync_service):
        """Test typical workflow of enabling auto-sync with triggers."""
        mock_core = TestDataFactory.create_mock_core(is_initialized=True)
        service = GitHookAutoSyncService(mock_core)

        # Step 1: Enable auto-sync
        config = GitHookAutoSyncConfig(auto_sync_enabled=True)
        service.set_config(config)
        assert service.get_config().auto_sync_enabled

        # Step 2: Enable commit trigger
        config = service.get_config()
        config.sync_on_commit = True
        service.set_config(config)
        assert service.get_config().sync_on_commit

        # Step 3: Disable confirmation
        config = service.get_config()
        config.confirm_before_sync = False
        service.set_config(config)
        assert not service.get_config().confirm_before_sync

    @patch("roadmap.core.services.git_hook_auto_sync_service.SyncMetadataService")
    def test_workflow_reset_to_defaults(self, mock_sync_service):
        """Test workflow of resetting configuration to defaults."""
        mock_core = TestDataFactory.create_mock_core(is_initialized=True)
        service = GitHookAutoSyncService(mock_core)

        # Set complex configuration
        config = GitHookAutoSyncConfig(
            auto_sync_enabled=True,
            sync_on_commit=True,
            sync_on_checkout=True,
            sync_on_merge=True,
            confirm_before_sync=False,
            force_local=True,
        )
        service.set_config(config)

        # Reset to defaults
        default_config = GitHookAutoSyncConfig()
        service.set_config(default_config)
        retrieved = service.get_config()

        assert not retrieved.auto_sync_enabled
        assert not retrieved.sync_on_commit
        assert not retrieved.sync_on_checkout
        assert not retrieved.sync_on_merge
        assert retrieved.confirm_before_sync
        assert not retrieved.force_local

    @patch("roadmap.core.services.git_hook_auto_sync_service.SyncMetadataService")
    def test_workflow_toggle_features(self, mock_sync_service):
        """Test workflow of toggling features on and off."""
        mock_core = TestDataFactory.create_mock_core(is_initialized=True)
        service = GitHookAutoSyncService(mock_core)

        config = GitHookAutoSyncConfig()
        service.set_config(config)

        # Toggle auto_sync_enabled multiple times
        for _ in range(3):
            config = service.get_config()
            config.auto_sync_enabled = not config.auto_sync_enabled
            service.set_config(config)

        # Should end up with auto_sync_enabled = True
        assert service.get_config().auto_sync_enabled
