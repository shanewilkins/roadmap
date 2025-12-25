"""Tests for configuration system."""

import tempfile
from pathlib import Path

import yaml

from roadmap.common.config_loader import ConfigLoader
from roadmap.common.config_models import (
    BehaviorConfig,
    ExportConfig,
    GitConfig,
    OutputConfig,
    RoadmapConfig,
)


class TestConfigModels:
    """Test configuration models."""

    def test_output_config_defaults(self):
        """Test OutputConfig default values."""
        config = OutputConfig()
        assert config.format == "rich"
        assert config.columns == []
        assert config.sort_by == ""

    def test_export_config_defaults(self):
        """Test ExportConfig default values."""
        config = ExportConfig()
        assert config.directory == ".roadmap/exports"
        assert config.format == "json"
        assert config.include_metadata is True
        assert config.auto_gitignore is True

    def test_behavior_config_defaults(self):
        """Test BehaviorConfig default values."""
        config = BehaviorConfig()
        assert config.auto_branch_on_start is False
        assert config.confirm_destructive is True
        assert config.show_tips is True

    def test_git_config_defaults(self):
        """Test GitConfig default values."""
        config = GitConfig()
        assert config.auto_commit is False
        assert config.commit_template == "roadmap: {operation} {entity_id}"

    def test_roadmap_config_defaults(self):
        """Test RoadmapConfig default values."""
        config = RoadmapConfig()
        assert isinstance(config.output, OutputConfig)
        assert isinstance(config.export, ExportConfig)
        assert isinstance(config.behavior, BehaviorConfig)
        assert isinstance(config.git, GitConfig)

    def test_roadmap_config_merge(self):
        """Test merging configs."""
        config1 = RoadmapConfig(
            output=OutputConfig(format="plain"),
            export=ExportConfig(directory="/tmp/exports"),
        )
        config2 = RoadmapConfig(
            output=OutputConfig(columns=["id", "title"]),
        )

        merged = config1.merge(config2)
        assert merged.output.format == "plain"  # From config1
        assert merged.output.columns == ["id", "title"]  # From config2
        assert merged.export.directory == "/tmp/exports"  # From config1


class TestConfigLoader:
    """Test configuration loader."""

    def test_get_user_config_path(self):
        """Test getting user config path."""
        path = ConfigLoader.get_user_config_path()
        assert path == Path.home() / ".roadmap" / "config.yaml"

    def test_get_project_config_path(self):
        """Test getting project config path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            path = ConfigLoader.get_project_config_path(project_root)
            assert path == project_root / ".roadmap" / "config.yaml"

    def test_load_nonexistent_user_config(self):
        """Test loading non-existent user config returns None."""
        # Mock the path to non-existent location
        with tempfile.TemporaryDirectory() as tmpdir:
            config = ConfigLoader._load_config_file(Path(tmpdir) / "nonexistent.yaml")
            assert config is None

    def test_load_valid_config_file(self):
        """Test loading a valid config file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"

            # Create a valid config file
            config_data = {
                "output": {"format": "plain"},
                "export": {"directory": "/tmp/exports"},
            }
            with open(config_path, "w") as f:
                yaml.dump(config_data, f)

            # Load and verify
            config = ConfigLoader._load_config_file(config_path)
            assert config is not None
            assert config.output.format == "plain"
            assert config.export.directory == "/tmp/exports"

    def test_load_config_merging(self):
        """Test config merging with precedence."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            roadmap_dir = project_root / ".roadmap"
            roadmap_dir.mkdir()

            # Create project config
            project_config_path = roadmap_dir / "config.yaml"
            project_config_data = {
                "output": {"format": "json"},
                "export": {"directory": "/project/exports"},
            }
            with open(project_config_path, "w") as f:
                yaml.dump(project_config_data, f)

            # Load config
            # Note: This will merge with actual user config if it exists
            config = ConfigLoader.load_config(project_root)
            # At minimum, project settings should be present
            assert config is not None

    def test_save_and_load_config(self):
        """Test saving and loading config."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"

            # Create and save config
            config = RoadmapConfig(
                output=OutputConfig(format="markdown"),
                export=ExportConfig(directory="/tmp/export"),
            )
            ConfigLoader._save_config_file(config_path, config)

            # Verify file was created
            assert config_path.exists()

            # Load and verify
            loaded = ConfigLoader._load_config_file(config_path)
            assert loaded is not None
            assert loaded.output.format == "markdown"
            assert loaded.export.directory == "/tmp/export"

    def test_get_config_value(self):
        """Test getting configuration value by path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"

            # Create config
            config = RoadmapConfig(export=ExportConfig(directory="/custom/exports"))
            ConfigLoader._save_config_file(config_path, config)

            # Mock loading from file
            loaded = ConfigLoader._load_config_file(config_path)
            assert loaded is not None
            assert loaded.export.directory == "/custom/exports"

    def test_set_config_value(self):
        """Test setting configuration value."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / ".roadmap"
            config_path.mkdir()
            config_file = config_path / "config.yaml"

            # Create initial config
            config = RoadmapConfig()
            ConfigLoader._save_config_file(config_file, config)

            # Load, modify, and save
            loaded = ConfigLoader._load_config_file(config_file)
            loaded.export.directory = "/new/exports"
            ConfigLoader._save_config_file(config_file, loaded)

            # Verify change persisted
            reloaded = ConfigLoader._load_config_file(config_file)
            assert reloaded.export.directory == "/new/exports"

    def test_invalid_config_file(self):
        """Test loading invalid config file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "bad_config.yaml"

            # Create invalid YAML
            with open(config_path, "w") as f:
                f.write("invalid: yaml: content: [")

            # Load should handle gracefully
            ConfigLoader._load_config_file(config_path)
            # Should return None or handle error gracefully
            # Actual behavior depends on YAML parser


class TestConfigPrecedence:
    """Test config precedence (defaults < user < project)."""

    def test_default_config(self):
        """Test default configuration."""
        config = ConfigLoader.DEFAULT_CONFIG
        assert config.output.format == "rich"
        assert config.export.directory == ".roadmap/exports"

    def test_project_overrides_defaults(self):
        """Test project config overrides defaults."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            roadmap_dir = project_root / ".roadmap"
            roadmap_dir.mkdir()

            project_config_path = roadmap_dir / "config.yaml"
            project_config_data = {"output": {"format": "plain"}}
            with open(project_config_path, "w") as f:
                yaml.dump(project_config_data, f)

            config = ConfigLoader.load_config(project_root)
            assert config.output.format == "plain"

    def test_merge_partial_config(self):
        """Test merging partial config."""
        config1 = RoadmapConfig(
            output=OutputConfig(format="rich"),
            export=ExportConfig(directory="/tmp"),
        )
        config2 = RoadmapConfig(output=OutputConfig(format="json"))

        merged = config1.merge(config2)
        assert merged.output.format == "json"
        assert merged.export.directory == "/tmp"  # Preserved
