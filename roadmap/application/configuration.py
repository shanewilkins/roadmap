"""Immutable resolved configuration supplied by Bootstrap."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ProjectSettings:
    workspace_schema_version: int = 1
    default_project_id: str | None = None
    include_closed_in_critical_path: bool = False


@dataclass(frozen=True, slots=True)
class UserSettings:
    name: str | None = None
    email: str | None = None
    default_milestone: str | None = None
    table_width: int = 100
    auto_branch_on_start: bool = False
    confirm_destructive: bool = True
    show_tips: bool = True
    output_format: str = "rich"
    output_columns: tuple[str, ...] = ()
    output_sort_by: str = ""
    export_directory: str = ".roadmap/exports"
    export_format: str = "json"
    export_include_metadata: bool = True
    export_auto_gitignore: bool = True


@dataclass(frozen=True, slots=True)
class ResolvedConfiguration:
    project: ProjectSettings = ProjectSettings()
    user: UserSettings = UserSettings()
