"""Data models for roadmap CLI.

DEPRECATED: This module is maintained for backward compatibility.
New code should import from roadmap.domain instead.

- Issue, IssueType, Priority, Status -> roadmap.domain.issue
- Milestone, MilestoneStatus -> roadmap.domain.milestone
- Project, ProjectStatus -> roadmap.domain.project
"""

from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, Field

# Re-export domain models for backward compatibility
from roadmap.domain import (
    Issue,
    IssueType,
    Milestone,
    MilestoneStatus,
    Priority,
    Project,
    ProjectStatus,
    RiskLevel,
    Status,
)

# Import configuration utilities
try:
    from .file_utils import ensure_directory_exists  # type: ignore
    from .security import create_secure_file, validate_path  # type: ignore
except ImportError:
    # Fallback for when security module is not available
    def validate_path(path):  # type: ignore
        pass

    def create_secure_file(path, mode="w", **kwargs):  # type: ignore
        return open(path, mode, **kwargs)

    def ensure_directory_exists(path):  # type: ignore
        pass


class Comment(BaseModel):
    """Comment data model for issues."""

    id: int  # GitHub comment ID
    issue_id: str  # Local issue ID or GitHub issue number
    author: str  # GitHub username
    body: str  # Comment content (markdown)
    created_at: datetime
    updated_at: datetime
    github_url: str | None = None  # GitHub comment URL

    def __str__(self) -> str:
        """String representation."""
        return (
            f"Comment by {self.author} on {self.created_at.strftime('%Y-%m-%d %H:%M')}"
        )


class RoadmapConfig(BaseModel):
    """Configuration model for roadmap."""

    github: dict = Field(default_factory=dict)
    defaults: dict = Field(
        default_factory=lambda: {
            "auto_branch": False,
            "branch_name_template": "feature/{id}-{slug}",
        }
    )
    milestones: dict = Field(default_factory=dict)
    sync: dict = Field(default_factory=dict)
    display: dict = Field(default_factory=dict)

    @classmethod
    def load_from_file(cls, config_path: Path) -> "RoadmapConfig":
        """Load configuration from YAML file."""
        import yaml

        if not config_path.exists():
            return cls()

        # Validate the configuration file path for security
        validate_path(str(config_path))

        with open(config_path) as f:
            data = yaml.safe_load(f) or {}

        return cls(**data)

    def save_to_file(self, config_path: Path) -> None:
        """Save configuration to YAML file."""
        import yaml

        ensure_directory_exists(config_path.parent)
        with create_secure_file(str(config_path), "w") as f:
            yaml.dump(self.model_dump(), f, default_flow_style=False)


__all__ = [
    "Issue",
    "IssueType",
    "Milestone",
    "MilestoneStatus",
    "Priority",
    "Project",
    "ProjectStatus",
    "RiskLevel",
    "Status",
    "Comment",
    "RoadmapConfig",
]
