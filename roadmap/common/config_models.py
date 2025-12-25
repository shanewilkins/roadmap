"""Configuration models and schemas for roadmap CLI.

Provides Pydantic models for user-level and project-level configuration
with validation and sensible defaults.
"""

from pydantic import BaseModel, Field


class OutputConfig(BaseModel):
    """Output formatting preferences."""

    format: str = Field(
        default="rich",
        description="Default output format (rich, plain, json, csv, markdown, html)",
    )
    columns: list[str] = Field(
        default_factory=list,
        description="Default columns to display (empty = all)",
    )
    sort_by: str = Field(
        default="",
        description="Default sort specification (e.g., 'status:asc')",
    )

    class Config:
        """Pydantic config."""

        extra = "allow"


class ExportConfig(BaseModel):
    """Export settings and behavior."""

    directory: str = Field(
        default=".roadmap/exports",
        description="Directory for exported files (relative to project root)",
    )
    format: str = Field(
        default="json",
        description="Default export format (json, csv, markdown)",
    )
    include_metadata: bool = Field(
        default=True,
        description="Include metadata in exports",
    )
    auto_gitignore: bool = Field(
        default=True,
        description="Automatically add exports directory to .gitignore",
    )

    class Config:
        """Pydantic config."""

        extra = "allow"


class BehaviorConfig(BaseModel):
    """Application behavior preferences."""

    auto_branch_on_start: bool = Field(
        default=False,
        description="Automatically create git branch when starting work on issue",
    )
    confirm_destructive: bool = Field(
        default=True,
        description="Prompt before delete/archive operations",
    )
    show_tips: bool = Field(
        default=True,
        description="Show helpful tips in output",
    )
    include_closed_in_critical_path: bool = Field(
        default=False,
        description="Include closed issues in critical path analysis by default",
    )

    class Config:
        """Pydantic config."""

        extra = "allow"


class GitConfig(BaseModel):
    """Git integration settings."""

    auto_commit: bool = Field(
        default=False,
        description="Automatically commit changes after operations",
    )
    commit_template: str = Field(
        default="roadmap: {operation} {entity_id}",
        description="Template for auto-generated commit messages",
    )

    class Config:
        """Pydantic config."""

        extra = "allow"


class RoadmapConfig(BaseModel):
    """Complete roadmap configuration schema."""

    output: OutputConfig = Field(default_factory=OutputConfig)
    export: ExportConfig = Field(default_factory=ExportConfig)
    behavior: BehaviorConfig = Field(default_factory=BehaviorConfig)
    git: GitConfig = Field(default_factory=GitConfig)

    class Config:
        """Pydantic config."""

        extra = "allow"

    def merge(self, other: "RoadmapConfig") -> "RoadmapConfig":
        """Merge another config into this one (other takes precedence).

        Args:
            other: Config to merge (takes precedence)

        Returns:
            New RoadmapConfig with merged values
        """
        if other is None:
            return self

        return RoadmapConfig(
            output=OutputConfig(
                **{
                    **self.output.model_dump(),
                    **other.output.model_dump(exclude_unset=True),
                }
            ),
            export=ExportConfig(
                **{
                    **self.export.model_dump(),
                    **other.export.model_dump(exclude_unset=True),
                }
            ),
            behavior=BehaviorConfig(
                **{
                    **self.behavior.model_dump(),
                    **other.behavior.model_dump(exclude_unset=True),
                }
            ),
            git=GitConfig(
                **{
                    **self.git.model_dump(),
                    **other.git.model_dump(exclude_unset=True),
                }
            ),
        )
