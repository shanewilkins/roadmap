"""Configuration schema for roadmap projects.

SECURITY NOTICE:
- The config.yaml file is LOCAL ONLY and should NOT be committed to version control
- It is added to .gitignore to prevent accidental exposure
- It should contain only local user preferences, NOT secrets
- GitHub tokens and other credentials should be stored in environment variables or .env files
- The config.yaml file should have restrictive permissions (e.g., mode 0600)
"""

from dataclasses import asdict, dataclass, field


@dataclass
class UserConfig:
    """User configuration - LOCAL ONLY, NEVER share or commit this file.

    Contains only non-sensitive user identification for the roadmap.

    SECURITY WARNING:
    - Do NOT store passwords, API keys, or other secrets in this config
    - Do NOT commit config.yaml to version control
    - Use environment variables or .env files for sensitive credentials
    - Keep config.yaml file permissions restrictive (mode 0600)
    """

    name: str  # Local username/identifier
    email: str | None = None


@dataclass
class PathsConfig:
    """Path configuration (LOCAL ONLY - relative to project root).

    These are local paths on the user's machine and should never be shared.
    """

    roadmap_dir: str = ".roadmap"
    logs_dir: str = ".roadmap/logs"
    db_dir: str = ".roadmap/db"


@dataclass
class GitHubConfig:
    """GitHub integration configuration - DOES NOT store credentials.

    Contains only repository metadata and sync preferences.

    SECURITY WARNING:
    - Do NOT store GitHub tokens or PATs (Personal Access Tokens) in this config
    - Use GITHUB_TOKEN environment variable for authentication instead
    - webhook_secret is stored locally but should be kept secure
    - Never commit config.yaml with webhook_secret to version control
    """

    owner: str | None = None
    repo: str | None = None
    enabled: bool = False
    sync_enabled: bool = False
    webhook_secret: str | None = None
    sync_settings: dict = field(
        default_factory=lambda: {
            "bidirectional": True,
            "auto_close": True,
            "sync_labels": True,
            "sync_milestones": True,
        }
    )


@dataclass
class DisplayConfig:
    """Display preferences and UI customization (LOCAL ONLY).

    User-specific display settings for command output and formatting.
    These are local preferences and should never be shared.
    """

    default_milestone: str | None = None
    table_width: int = 100


@dataclass
class RoadmapConfig:
    """Complete roadmap configuration - LOCAL ONLY, NEVER commit to version control.

    This is the root configuration object stored in .roadmap/config.yaml.
    It aggregates user, paths, GitHub, and display settings.

    SECURITY REMINDER:
    - This entire config object is user-specific and must not be shared
    - It is added to .gitignore to prevent accidental commits
    - Secrets (tokens, PATs) must go in environment variables, NOT here
    - Keep the config.yaml file with restrictive permissions (mode 0600)
    """

    user: UserConfig
    paths: PathsConfig = field(default_factory=PathsConfig)
    github: GitHubConfig = field(default_factory=GitHubConfig)
    display: DisplayConfig = field(default_factory=DisplayConfig)

    def to_dict(self):
        """Convert to dictionary for YAML serialization."""
        return asdict(self)

    @staticmethod
    def from_dict(data: dict) -> "RoadmapConfig":
        """Create from dictionary (e.g., from YAML)."""
        user_data = data.get("user", {})
        user = UserConfig(**user_data) if user_data else None

        paths_data = data.get("paths", {})
        paths = PathsConfig(**paths_data)

        github_data = data.get("github", {})
        github = GitHubConfig(**github_data)

        display_data = data.get("display", {})
        display = DisplayConfig(**display_data)

        if not user:
            raise ValueError("User configuration is required")

        return RoadmapConfig(user=user, paths=paths, github=github, display=display)
