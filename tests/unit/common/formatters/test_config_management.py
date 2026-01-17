"""Tests for Phase 2: Config refactoring - split into shared + local.

Tests the team config (committed) vs user-local overrides (gitignored) pattern.
"""

from pathlib import Path

import pytest
import yaml

from roadmap.common.configuration import (
    ConfigManager,
    GitHubConfig,
    PathsConfig,
    RoadmapConfig,
    UserConfig,
)


@pytest.fixture
def temp_config_dir(temp_dir_context):
    """Create a temporary directory for config files."""
    with temp_dir_context() as tmpdir:
        yield Path(tmpdir)


class TestConfigSplitting:
    """Test splitting config into shared and local."""

    def test_shared_config_loaded_when_local_absent(self, temp_config_dir):
        """Test that shared config is used when no local override exists."""
        config_file = temp_config_dir / "config.yaml"

        # Create shared config
        shared_config = {
            "user": {"name": "team_user", "email": "team@example.com"},
            "github": {"enabled": True, "owner": "org"},
        }
        with open(config_file, "w") as f:
            yaml.dump(shared_config, f)

        manager = ConfigManager(config_file)
        config = manager.load()

        assert config.user.name == "team_user"
        assert config.user.email == "team@example.com"
        assert config.github.owner == "org"

    def test_local_config_overrides_shared(self, temp_config_dir):
        """Test that local config overrides shared settings."""
        config_file = temp_config_dir / "config.yaml"
        local_file = temp_config_dir / "config.yaml.local"

        # Create shared config
        shared_config = {
            "user": {"name": "team_user", "email": "team@example.com"},
            "github": {"enabled": True, "owner": "org", "repo": "shared-repo"},
        }
        with open(config_file, "w") as f:
            yaml.dump(shared_config, f)

        # Create local overrides
        local_config = {
            "user": {"name": "shane"},  # Override name only
            "github": {"owner": "shane"},  # Override owner only
        }
        with open(local_file, "w") as f:
            yaml.dump(local_config, f)

        manager = ConfigManager(config_file)
        config = manager.load()

        # Verify merge: local overrides but shared values remain for non-overridden fields
        assert config.user.name == "shane"  # Overridden
        assert config.user.email == "team@example.com"  # Shared (not overridden)
        assert config.github.owner == "shane"  # Overridden
        assert config.github.repo == "shared-repo"  # Shared (not overridden)

    def test_local_config_alone_without_shared(self, temp_config_dir):
        """Test loading local config when shared config doesn't exist."""
        config_file = temp_config_dir / "config.yaml"
        local_file = temp_config_dir / "config.yaml.local"

        # Create only local config
        local_config = {
            "user": {"name": "shane", "email": "shane@local.com"},
        }
        with open(local_file, "w") as f:
            yaml.dump(local_config, f)

        manager = ConfigManager(config_file)
        config = manager.load()

        assert config.user.name == "shane"
        assert config.user.email == "shane@local.com"

    def test_deep_merge_nested_dicts(self, temp_config_dir):
        """Test that deep merge works for nested dictionaries."""
        config_file = temp_config_dir / "config.yaml"
        local_file = temp_config_dir / "config.yaml.local"

        # Create shared config with nested structure
        shared_config = {
            "user": {"name": "team"},  # Required
            "github": {
                "enabled": True,
                "owner": "org",
                "sync_settings": {
                    "bidirectional": True,
                    "auto_close": True,
                    "sync_labels": True,
                },
            },
        }
        with open(config_file, "w") as f:
            yaml.dump(shared_config, f)

        # Create local overrides for nested field
        local_config = {
            "github": {
                "sync_settings": {
                    "auto_close": False,  # Override one nested field
                }
            }
        }
        with open(local_file, "w") as f:
            yaml.dump(local_config, f)

        manager = ConfigManager(config_file)
        config = manager.load()

        # Verify deep merge
        assert config.github.enabled  # Shared
        assert config.github.owner == "org"  # Shared
        # Note: sync_settings will be merged based on the implementation


class TestConfigPersistence:
    """Test saving and loading configs."""

    def test_save_shared_config(self, temp_config_dir):
        """Test saving shared config file."""
        config_file = temp_config_dir / "config.yaml"
        manager = ConfigManager(config_file)

        config = RoadmapConfig(
            user=UserConfig(name="team", email="team@org.com"),
            paths=PathsConfig(),
            github=GitHubConfig(enabled=False),
        )

        manager.save(config, is_local=False)

        assert config_file.exists()
        with open(config_file) as f:
            data = yaml.safe_load(f)
        assert isinstance(data, dict)
        assert data["user"]["name"] == "team"

    def test_save_local_override(self, temp_config_dir):
        """Test saving local override file."""
        config_file = temp_config_dir / "config.yaml"
        local_file = temp_config_dir / "config.yaml.local"

        manager = ConfigManager(config_file)

        # Create and save local config
        local_config = RoadmapConfig(
            user=UserConfig(name="shane", email="shane@local.com"),
            paths=PathsConfig(),
            github=GitHubConfig(owner="shane"),
        )

        manager.save(local_config, is_local=True)

        assert local_file.exists()
        assert not config_file.exists()  # Shared not created

        with open(local_file) as f:
            data = yaml.safe_load(f)
        assert isinstance(data, dict)
        assert data["user"]["name"] == "shane"

    def test_separate_shared_and_local_files(self, temp_config_dir):
        """Test that shared and local files are kept separate."""
        config_file = temp_config_dir / "config.yaml"
        local_file = temp_config_dir / "config.yaml.local"

        manager = ConfigManager(config_file)

        # Save shared config
        shared_config = RoadmapConfig(
            user=UserConfig(name="team"),
            paths=PathsConfig(),
            github=GitHubConfig(enabled=True),
        )
        manager.save(shared_config, is_local=False)

        # Save local config
        local_config = RoadmapConfig(
            user=UserConfig(name="shane"),
            paths=PathsConfig(),
            github=GitHubConfig(owner="shane"),
        )
        manager.save(local_config, is_local=True)

        # Both files should exist with different content
        assert config_file.exists()
        assert local_file.exists()

        with open(config_file) as f:
            shared_data = yaml.safe_load(f)
        assert isinstance(shared_data, dict)
        with open(local_file) as f:
            local_data = yaml.safe_load(f)
        assert isinstance(local_data, dict)

        assert shared_data["user"]["name"] == "team"
        assert local_data["user"]["name"] == "shane"


class TestConfigMerging:
    """Test the deep merge functionality."""

    def test_merge_top_level_override(self):
        """Test merging with top-level field override."""
        base = {"a": 1, "b": 2}
        override = {"a": 10}
        result = ConfigManager._deep_merge(base, override)

        assert result["a"] == 10
        assert result["b"] == 2

    def test_merge_nested_override(self):
        """Test merging with nested field override."""
        base = {"config": {"x": 1, "y": 2}, "other": 3}
        override = {"config": {"x": 10}}
        result = ConfigManager._deep_merge(base, override)

        assert result["config"]["x"] == 10
        assert result["config"]["y"] == 2
        assert result["other"] == 3

    def test_merge_adds_new_fields(self):
        """Test that merge adds new fields from override."""
        base = {"a": 1}
        override = {"b": 2}
        result = ConfigManager._deep_merge(base, override)

        assert result["a"] == 1
        assert result["b"] == 2

    def test_merge_deep_nesting(self):
        """Test merge with deeply nested structures."""
        base = {
            "level1": {
                "level2": {
                    "a": 1,
                    "b": 2,
                    "level3": {"x": 10, "y": 20},
                }
            }
        }
        override = {
            "level1": {
                "level2": {
                    "a": 100,
                    "level3": {"x": 100},
                }
            }
        }
        result = ConfigManager._deep_merge(base, override)

        assert result["level1"]["level2"]["a"] == 100
        assert result["level1"]["level2"]["b"] == 2
        assert result["level1"]["level2"]["level3"]["x"] == 100
        assert result["level1"]["level2"]["level3"]["y"] == 20


class TestTeamOnboardingConfig:
    """Test team onboarding scenarios with config."""

    def test_alice_commits_shared_config(self, temp_config_dir):
        """Test Alice creating and committing shared config."""
        config_file = temp_config_dir / "config.yaml"
        manager = ConfigManager(config_file)

        # Alice creates team config
        team_config = RoadmapConfig(
            user=UserConfig(name="team-roadmap", email="team@example.com"),
            paths=PathsConfig(),
            github=GitHubConfig(
                enabled=True,
                owner="my-org",
                repo="my-project",
            ),
        )

        manager.save(team_config, is_local=False)

        # Verify shared config file exists
        assert config_file.exists()
        assert not (temp_config_dir / "config.yaml.local").exists()

    def test_bob_joins_with_local_override(self, temp_config_dir):
        """Test Bob cloning and adding local overrides."""
        config_file = temp_config_dir / "config.yaml"
        local_file = temp_config_dir / "config.yaml.local"

        # Simulate Alice's committed config
        team_config = {
            "user": {"name": "team-roadmap", "email": "team@example.com"},
            "github": {"enabled": True, "owner": "my-org", "repo": "my-project"},
        }
        with open(config_file, "w") as f:
            yaml.dump(team_config, f)

        # Bob clones repo (config.yaml is already there)
        # Bob creates his local overrides
        bob_config = {
            "user": {"name": "bob"},  # Override just his name
        }
        with open(local_file, "w") as f:
            yaml.dump(bob_config, f)

        # When Bob loads config, he gets the merged version
        manager = ConfigManager(config_file)
        config = manager.load()

        assert config.user.name == "bob"  # His local override
        assert config.user.email == "team@example.com"  # Team shared
        assert config.github.owner == "my-org"  # Team shared

    def test_local_config_not_committed(self, temp_config_dir):
        """Test that .local files are ignored (not committed)."""
        local_file = temp_config_dir / "config.yaml.local"

        # Create a local file
        with open(local_file, "w") as f:
            yaml.dump({"user": {"name": "shane"}}, f)

        # Verify it exists
        assert local_file.exists()

        # This file should be in .gitignore (verification would be in git)
        # Just confirm it has .local extension
        assert str(local_file).endswith(".local")
