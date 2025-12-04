"""Configuration schema for roadmap projects."""

from dataclasses import asdict, dataclass, field


@dataclass
class UserConfig:
    """User configuration."""

    name: str  # Local username/identifier
    email: str | None = None


@dataclass
class PathsConfig:
    """Path configuration (relative to project root)."""

    roadmap_dir: str = ".roadmap"
    logs_dir: str = ".roadmap/logs"
    db_dir: str = ".roadmap/db"


@dataclass
class GitHubConfig:
    """GitHub integration configuration."""

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
    """Display preferences."""

    default_milestone: str | None = None
    table_width: int = 100


@dataclass
class RoadmapConfig:
    """Complete roadmap configuration."""

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
