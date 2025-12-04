"""Configuration management for roadmap."""

import subprocess
from pathlib import Path

import yaml

from .config_schema import GitHubConfig, PathsConfig, RoadmapConfig, UserConfig


class ConfigManager:
    """Manages roadmap configuration files."""

    def __init__(self, config_file: Path):
        """Initialize config manager with config file path."""
        self.config_file = config_file

    def load(self) -> RoadmapConfig:
        """Load configuration from file."""
        if not self.config_file.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_file}")

        with open(self.config_file) as f:
            data = yaml.safe_load(f) or {}

        return RoadmapConfig.from_dict(data)

    def save(self, config: RoadmapConfig) -> None:
        """Save configuration to file."""
        self.config_file.parent.mkdir(parents=True, exist_ok=True)

        with open(self.config_file, "w") as f:
            yaml.dump(config.to_dict(), f, default_flow_style=False, sort_keys=False)

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
    def auto_detect_github_username() -> str | None:
        """Auto-detect GitHub username from git remote."""
        try:
            result = subprocess.run(
                ["git", "config", "user.github"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

        # Try to extract from git remote origin url
        try:
            result = subprocess.run(
                ["git", "config", "remote.origin.url"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                url = result.stdout.strip()
                # Parse github.com:owner/repo.git or https://github.com/owner/repo.git
                if "github.com" in url:
                    parts = url.split("/")[-2:]  # Get last 2 parts
                    if parts and parts[0]:
                        return parts[0]
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

        return None

    @staticmethod
    def create_default_config(
        user_name: str,
        user_email: str | None = None,
        github_owner: str | None = None,
        github_repo: str | None = None,
        github_enabled: bool = False,
    ) -> RoadmapConfig:
        """Create a default configuration."""
        user = UserConfig(name=user_name, email=user_email)
        paths = PathsConfig()
        github = GitHubConfig(
            owner=github_owner, repo=github_repo, enabled=github_enabled
        )

        return RoadmapConfig(user=user, paths=paths, github=github)
