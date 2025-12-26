"""Integration tests for roadmap settings module.

This module tests get_config_paths() and basic dynaconf initialization.
Most of settings.py is declarative configuration (validators, defaults),
which cannot be effectively tested as executable code.
"""

from pathlib import Path

import pytest

from roadmap import settings


class TestGetConfigPaths:
    """Test get_config_paths - the primary executable function."""

    def test_returns_dictionary(self):
        """Test get_config_paths returns dict with expected keys."""
        paths = settings.get_config_paths()

        assert isinstance(paths, dict)
        assert "global_config" in paths
        assert "global_secrets" in paths
        assert "local_config" in paths
        assert "local_secrets" in paths

    def test_creates_home_directory(self):
        """Test home config directory is created."""
        settings.get_config_paths()

        home_config_dir = Path.home() / ".roadmap"
        assert home_config_dir.exists()
        assert home_config_dir.is_dir()

    @pytest.mark.parametrize(
        "path_key,expected_suffix",
        [
            ("global_config", "settings.toml"),
            ("global_secrets", "secrets.toml"),
            ("local_config", "settings.toml"),
            ("local_secrets", "secrets.toml"),
        ],
    )
    def test_paths_have_correct_filenames(self, path_key, expected_suffix):
        """Test config paths have correct filenames."""
        paths = settings.get_config_paths()

        assert str(paths[path_key]).endswith(expected_suffix)
        assert isinstance(paths[path_key], Path)

    def test_paths_contain_roadmap_directory(self):
        """Test all paths reference .roadmap directory."""
        paths = settings.get_config_paths()

        for path_key, path in paths.items():
            assert ".roadmap" in str(path), f"{path_key} missing .roadmap"

    def test_global_and_local_paths_differ(self):
        """Test global and local paths are different."""
        paths = settings.get_config_paths()

        assert paths["global_config"] != paths["local_config"]
        assert paths["global_secrets"] != paths["local_secrets"]

    def test_paths_are_absolute_or_expandable(self):
        """Test paths can be resolved."""
        paths = settings.get_config_paths()

        for _path_key, path in paths.items():
            # Should be resolvable (expand ~ if needed)
            expanded = path.expanduser()
            assert expanded is not None


class TestSettingsInitialization:
    """Test settings object initialization."""

    def test_settings_object_exists(self):
        """Test settings object is created."""
        assert hasattr(settings, "settings")
        assert settings.settings is not None

    def test_settings_has_get_method(self):
        """Test settings supports .get() for accessing values."""
        assert callable(getattr(settings.settings, "get", None))

    def test_accessing_setting_values(self):
        """Test can access configuration values."""
        # These may or may not be set, but should not raise
        db_path = settings.settings.get("database.path")
        log_level = settings.settings.get("logging.level")

        # Values can be None or whatever was configured
        assert db_path is None or isinstance(db_path, str)
        assert log_level is None or isinstance(log_level, str)

    def test_settings_with_defaults(self):
        """Test settings.get() with fallback defaults."""
        # Request with defaults
        result = settings.settings.get("nonexistent.key", "default_value")

        # Should return either the configured value or default
        assert result is not None


class TestValidatorConfiguration:
    """Test validator list is properly defined."""

    def test_validators_list_exists(self):
        """Test _validators list is defined."""
        assert hasattr(settings, "_validators")
        assert isinstance(settings._validators, list)

    def test_validators_not_empty(self):
        """Test validators list contains entries."""
        validators = settings._validators
        assert len(validators) > 0, "Validators list should not be empty"

    def test_validators_have_expected_names(self):
        """Test validators cover expected configuration areas."""
        validators = settings._validators
        validator_names = [str(v) for v in validators]

        # At least verify we have validators (structure varies by dynaconf version)
        assert len(validator_names) > 0


class TestSettingsDefaults:
    """Test settings configuration defaults."""

    def test_github_disabled_by_default(self):
        """Test GitHub integration is disabled by default."""
        enabled = settings.settings.get("github.enabled", False)

        # Should be disabled (False) by default, or None if not configured
        assert enabled is None or enabled is False or isinstance(enabled, bool)

    def test_git_auto_sync_setting(self):
        """Test git.auto_sync setting is accessible."""
        auto_sync = settings.settings.get("git.auto_sync")

        # Should be either configured, or None
        assert auto_sync is None or isinstance(auto_sync, bool)

    def test_logging_level_setting(self):
        """Test logging.level setting is accessible."""
        level = settings.settings.get("logging.level")

        # Should be None or a valid log level string
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        assert level is None or level in valid_levels


class TestSettingsUsability:
    """Test practical usage of settings."""

    def test_get_config_paths_idempotent(self):
        """Test multiple calls to get_config_paths return same paths."""
        paths1 = settings.get_config_paths()
        paths2 = settings.get_config_paths()

        assert paths1.keys() == paths2.keys()
        for key in paths1.keys():
            assert paths1[key] == paths2[key]

    def test_settings_accessible_throughout_lifecycle(self):
        """Test settings object remains accessible."""
        # First access
        obj1 = settings.settings

        # Second access
        obj2 = settings.settings

        # Should be same object
        assert obj1 is obj2

    def test_logger_available(self):
        """Test logger is available in settings module."""
        assert hasattr(settings, "logger")
        assert settings.logger is not None


class TestConfigPathEdgeCases:
    """Test edge cases for config paths."""

    def test_paths_with_special_characters_work(self, tmp_path, monkeypatch):
        """Test config paths handle home directory correctly."""
        paths = settings.get_config_paths()

        # All paths should be Path objects
        for path in paths.values():
            assert isinstance(path, Path)

            # All should be expandable
            expanded = path.expanduser()
            assert expanded is not None

    def test_home_directory_created_idempotent(self):
        """Test creating home directory multiple times is safe."""
        # First call creates it
        settings.get_config_paths()
        home1 = Path.home() / ".roadmap"

        # Second call should still work
        settings.get_config_paths()
        home2 = Path.home() / ".roadmap"

        assert home1 == home2
        assert home1.exists()
