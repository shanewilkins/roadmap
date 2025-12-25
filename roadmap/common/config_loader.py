"""Configuration loader and manager.

Handles loading and merging user-level and project-level configurations
with support for YAML files and sensible defaults.
"""

from pathlib import Path
from typing import Any

import yaml
from structlog import get_logger

from roadmap.common.config_models import RoadmapConfig

logger = get_logger()


class ConfigLoader:
    """Loads and manages roadmap configuration."""

    # Default configuration
    DEFAULT_CONFIG = RoadmapConfig()

    @classmethod
    def get_user_config_path(cls) -> Path:
        """Get the user-level config file path.

        Returns:
            Path to ~/.roadmap/config.yaml
        """
        home = Path.home()
        return home / ".roadmap" / "config.yaml"

    @classmethod
    def get_project_config_path(cls, project_root: Path | None = None) -> Path:
        """Get the project-level config file path.

        Args:
            project_root: Project root directory (defaults to cwd)

        Returns:
            Path to .roadmap/config.yaml in project
        """
        if project_root is None:
            project_root = Path.cwd()
        return project_root / ".roadmap" / "config.yaml"

    @classmethod
    def load_user_config(cls) -> RoadmapConfig | None:
        """Load user-level configuration.

        Returns:
            RoadmapConfig from user config file, or None if not found
        """
        path = cls.get_user_config_path()
        return cls._load_config_file(path)

    @classmethod
    def load_project_config(
        cls, project_root: Path | None = None
    ) -> RoadmapConfig | None:
        """Load project-level configuration.

        Args:
            project_root: Project root directory (defaults to cwd)

        Returns:
            RoadmapConfig from project config file, or None if not found
        """
        path = cls.get_project_config_path(project_root)
        return cls._load_config_file(path)

    @classmethod
    def _load_config_file(cls, path: Path) -> RoadmapConfig | None:
        """Load a configuration file.

        Args:
            path: Path to config file

        Returns:
            RoadmapConfig if file exists and is valid, None otherwise
        """
        if not path.exists():
            return None

        try:
            with open(path, encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}

            # Validate and create config from data
            config = RoadmapConfig(**data)
            logger.info("loaded_config", path=str(path))
            return config
        except Exception as e:
            logger.warning(
                "failed_to_load_config",
                path=str(path),
                error=str(e),
            )
            return None

    @classmethod
    def load_config(cls, project_root: Path | None = None) -> RoadmapConfig:
        """Load and merge all configurations.

        Precedence: defaults < user config < project config

        Args:
            project_root: Project root directory (defaults to cwd)

        Returns:
            Merged RoadmapConfig with all layers applied
        """
        # Start with defaults
        config = cls.DEFAULT_CONFIG

        # Merge user config
        user_config = cls.load_user_config()
        if user_config:
            config = config.merge(user_config)

        # Merge project config
        project_config = cls.load_project_config(project_root)
        if project_config:
            config = config.merge(project_config)

        return config

    @classmethod
    def save_user_config(cls, config: RoadmapConfig) -> bool:
        """Save user-level configuration.

        Args:
            config: Configuration to save

        Returns:
            True if successful, False otherwise
        """
        path = cls.get_user_config_path()
        return cls._save_config_file(path, config)

    @classmethod
    def save_project_config(
        cls, config: RoadmapConfig, project_root: Path | None = None
    ) -> bool:
        """Save project-level configuration.

        Args:
            config: Configuration to save
            project_root: Project root directory (defaults to cwd)

        Returns:
            True if successful, False otherwise
        """
        path = cls.get_project_config_path(project_root)
        return cls._save_config_file(path, config)

    @classmethod
    def _save_config_file(cls, path: Path, config: RoadmapConfig) -> bool:
        """Save a configuration file.

        Args:
            path: Path to config file
            config: Configuration to save

        Returns:
            True if successful, False otherwise
        """
        try:
            # Create directory if needed
            path.parent.mkdir(parents=True, exist_ok=True)

            # Convert config to dict and save as YAML
            data = config.model_dump(exclude_none=True)
            with open(path, "w", encoding="utf-8") as f:
                yaml.dump(data, f, default_flow_style=False, sort_keys=False)

            logger.info("saved_config", path=str(path))
            return True
        except Exception as e:
            logger.error(
                "failed_to_save_config",
                path=str(path),
                error=str(e),
            )
            return False

    @classmethod
    def get_config_value(cls, key_path: str, project_root: Path | None = None) -> Any:
        """Get a configuration value by path (e.g., 'export.directory').

        Args:
            key_path: Dot-separated path to config value
            project_root: Project root directory (defaults to cwd)

        Returns:
            Configuration value, or None if not found
        """
        config = cls.load_config(project_root)
        keys = key_path.split(".")
        value = config

        for key in keys:
            if hasattr(value, key):
                value = getattr(value, key)
            elif isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return None

        return value

    @classmethod
    def set_config_value(
        cls,
        key_path: str,
        value: Any,
        project_level: bool = False,
        project_root: Path | None = None,
    ) -> bool:
        """Set a configuration value by path (e.g., 'export.directory').

        Args:
            key_path: Dot-separated path to config value
            value: Value to set
            project_level: If True, save to project config; else user config
            project_root: Project root directory (defaults to cwd)

        Returns:
            True if successful, False otherwise
        """
        # Load existing config
        if project_level:
            config = cls.load_project_config(project_root) or RoadmapConfig()
        else:
            config = cls.load_user_config() or RoadmapConfig()

        # Set value in config
        keys = key_path.split(".")
        target = config
        for key in keys[:-1]:
            if not hasattr(target, key):
                setattr(target, key, {})
            target = getattr(target, key)

        setattr(target, keys[-1], value)

        # Save config
        if project_level:
            return cls.save_project_config(config, project_root)
        else:
            return cls.save_user_config(config)
