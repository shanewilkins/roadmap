"""Configuration management for roadmap."""

import subprocess
from pathlib import Path

import yaml

from .config_schema import PathsConfig, RoadmapConfig, UserConfig


class ConfigManager:
    """Manages roadmap configuration files.

    Supports two-level configuration:
    - config.yaml: Team-level configuration (committed to git)
    - config.yaml.local: User-level overrides (gitignored, local only)

    When both exist, local overrides shared settings.
    """

    def __init__(self, config_file: Path):
        """Initialize config manager with config file path."""
        self.config_file = config_file
        self.local_config_file = Path(str(config_file).replace(".yaml", ".yaml.local"))

    def load(self) -> RoadmapConfig:
        """Load configuration from file(s).

        Loads team config first, then merges local overrides if present.
        """
        config_data: dict = {}

        # Load shared config (team-level)
        if self.config_file.exists():
            with open(self.config_file) as f:
                loaded = yaml.safe_load(f)
                config_data = loaded if isinstance(loaded, dict) else {}

        # Load and merge local config (user-level overrides)
        if self.local_config_file.exists():
            with open(self.local_config_file) as f:
                loaded = yaml.safe_load(f)
                local_data = loaded if isinstance(loaded, dict) else {}
            # Deep merge: local overrides shared
            config_data = self._deep_merge(config_data, local_data)

        return RoadmapConfig.from_dict(config_data)

    def save(self, config: RoadmapConfig, is_local: bool = False) -> None:
        """Save configuration to file.

        Args:
            config: Configuration to save
            is_local: If True, save to .local file (user overrides only)
        """
        target_file = self.local_config_file if is_local else self.config_file
        target_file.parent.mkdir(parents=True, exist_ok=True)

        with open(target_file, "w") as f:
            yaml.dump(config.to_dict(), f, default_flow_style=False, sort_keys=False)

    @staticmethod
    def _deep_merge(base: dict, override: dict) -> dict:
        """Deep merge override dict into base dict.

        Override values take precedence over base values.
        """
        result = base.copy()
        for key, value in override.items():
            if (
                key in result
                and isinstance(result[key], dict)
                and isinstance(value, dict)
            ):
                result[key] = ConfigManager._deep_merge(result[key], value)
            else:
                result[key] = value
        return result

    @staticmethod
    def auto_detect_user() -> str | None:
        """Auto-detect user from git config or environment."""
        try:
            # Try git config user.name
            result = subprocess.run(
                ["git", "config", "user.name"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

        # Try git config user.email
        try:
            result = subprocess.run(
                ["git", "config", "user.email"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0 and result.stdout.strip():
                email = result.stdout.strip()
                # Extract name part before @
                if "@" in email:
                    return email.split("@")[0]
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

        return None

    @staticmethod
    def create_default_config(
        user_name: str,
        user_email: str | None = None,
    ) -> RoadmapConfig:
        """Create a default configuration."""
        user = UserConfig(name=user_name, email=user_email)
        paths = PathsConfig()
        return RoadmapConfig(user=user, paths=paths)
