"""Versioned project policy and external user-preference configuration."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import yaml

from roadmap.application.configuration import (
    ProjectSettings,
    ResolvedConfiguration,
    UserSettings,
)

from .canonical import _atomic_write

type ConfigurationScope = Literal["project", "user"]

PROJECT_KEYS = {
    "behavior.default_project_id",
    "behavior.include_closed_in_critical_path",
}
USER_KEYS = {
    "identity.name",
    "identity.email",
    "display.default_milestone",
    "display.table_width",
    "behavior.auto_branch_on_start",
    "behavior.confirm_destructive",
    "behavior.show_tips",
    "output.format",
    "output.columns",
    "output.sort_by",
    "export.directory",
    "export.format",
    "export.include_metadata",
    "export.auto_gitignore",
}


class ConfigurationError(ValueError):
    """Configuration is invalid for its declared schema or scope."""


def _read(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as error:
        raise ConfigurationError(
            f"cannot read configuration {path}: {error}"
        ) from error
    if not isinstance(loaded, dict):
        raise ConfigurationError(f"configuration {path} must be a mapping")
    version = loaded.get("schema_version", 0)
    if not isinstance(version, int) or version < 0 or version > 1:
        raise ConfigurationError(
            f"unsupported configuration schema_version {version!r} in {path}"
        )
    return dict(loaded)


def _nested(data: dict[str, Any], section: str) -> dict[str, Any]:
    value = data.get(section, {})
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ConfigurationError(f"configuration section {section} must be a mapping")
    return value


def _validate_scope(data: dict[str, Any], allowed: set[str], fixed: set[str]) -> None:
    sections = {key.split(".", 1)[0] for key in allowed}
    unknown = set(data) - sections - fixed
    for section in sections & data.keys():
        values = _nested(data, section)
        declared = {key.split(".", 1)[1] for key in allowed if key.startswith(section)}
        unknown.update(f"{section}.{key}" for key in set(values) - declared)
    if unknown:
        raise ConfigurationError(
            "unknown or incorrectly scoped configuration keys: "
            + ", ".join(sorted(unknown))
        )


def _bool(section: dict[str, Any], key: str, default: bool) -> bool:
    value = section.get(key)
    if value is None:
        return default
    if not isinstance(value, bool):
        raise ConfigurationError(f"configuration key {key} must be a boolean")
    return value


def _validate_value(key: str, value: Any) -> None:
    boolean_keys = {
        "behavior.auto_branch_on_start",
        "behavior.confirm_destructive",
        "behavior.show_tips",
        "behavior.include_closed_in_critical_path",
        "export.include_metadata",
        "export.auto_gitignore",
    }
    if key in boolean_keys and not isinstance(value, bool):
        raise ConfigurationError(f"configuration key {key} must be a boolean")
    if key == "display.table_width" and (
        not isinstance(value, int) or isinstance(value, bool) or value < 20
    ):
        raise ConfigurationError("configuration key display.table_width must be >= 20")
    if key == "output.columns" and (
        not isinstance(value, list) or any(not isinstance(item, str) for item in value)
    ):
        raise ConfigurationError("configuration key output.columns must be a list")
    if key not in boolean_keys | {"display.table_width", "output.columns"} and not (
        value is None or isinstance(value, str)
    ):
        raise ConfigurationError(f"configuration key {key} must be text or null")


class ConfigurationFiles:
    """Load once into immutable settings; mutate only through scoped CLI actions."""

    def __init__(self, project_path: Path, user_path: Path):
        self.project_path = project_path
        self.user_path = user_path

    def resolve(self) -> ResolvedConfiguration:
        project = _read(self.project_path)
        user = _read(self.user_path)
        _validate_scope(
            project, PROJECT_KEYS, {"schema_version", "workspace_schema_version"}
        )
        _validate_scope(user, USER_KEYS, {"schema_version"})
        project_behavior = _nested(project, "behavior")
        identity = _nested(user, "identity")
        display = _nested(user, "display")
        user_behavior = _nested(user, "behavior")
        output = _nested(user, "output")
        export = _nested(user, "export")
        workspace_version = project.get("workspace_schema_version", 0)
        if (
            not isinstance(workspace_version, int)
            or isinstance(workspace_version, bool)
            or workspace_version < 0
        ):
            raise ConfigurationError(
                "configuration key workspace_schema_version must be a non-negative integer"
            )
        table_width = display.get("table_width", 100)
        if not isinstance(table_width, int) or table_width < 20:
            raise ConfigurationError(
                "configuration key display.table_width must be >= 20"
            )
        columns = output.get("columns", [])
        if not isinstance(columns, list) or any(
            not isinstance(item, str) for item in columns
        ):
            raise ConfigurationError("configuration key output.columns must be a list")
        return ResolvedConfiguration(
            ProjectSettings(
                workspace_schema_version=workspace_version,
                default_project_id=project_behavior.get("default_project_id"),
                include_closed_in_critical_path=_bool(
                    project_behavior,
                    "include_closed_in_critical_path",
                    False,
                ),
            ),
            UserSettings(
                name=identity.get("name"),
                email=identity.get("email"),
                default_milestone=display.get("default_milestone"),
                table_width=table_width,
                auto_branch_on_start=_bool(
                    user_behavior,
                    "auto_branch_on_start",
                    False,
                ),
                confirm_destructive=_bool(
                    user_behavior,
                    "confirm_destructive",
                    True,
                ),
                show_tips=_bool(user_behavior, "show_tips", True),
                output_format=str(output.get("format", "rich")),
                output_columns=tuple(columns),
                output_sort_by=str(output.get("sort_by", "")),
                export_directory=str(export.get("directory", ".roadmap/exports")),
                export_format=str(export.get("format", "json")),
                export_include_metadata=_bool(export, "include_metadata", True),
                export_auto_gitignore=_bool(export, "auto_gitignore", True),
            ),
        )

    def view(self, scope: ConfigurationScope) -> dict[str, Any]:
        return _read(self.project_path if scope == "project" else self.user_path)

    def get(self, key: str) -> Any:
        scope = (
            "project" if key in PROJECT_KEYS else "user" if key in USER_KEYS else None
        )
        if scope is None:
            raise ConfigurationError(f"unknown configuration key: {key}")
        value: Any = self.view(scope)
        for part in key.split("."):
            if not isinstance(value, dict) or part not in value:
                return None
            value = value[part]
        return value

    def set(self, key: str, value: Any, scope: ConfigurationScope) -> None:
        allowed = PROJECT_KEYS if scope == "project" else USER_KEYS
        if key not in allowed:
            owner = (
                "project"
                if key in PROJECT_KEYS
                else "user"
                if key in USER_KEYS
                else None
            )
            if owner:
                raise ConfigurationError(f"configuration key {key} is {owner}-scoped")
            raise ConfigurationError(f"unknown configuration key: {key}")
        self.resolve()
        _validate_value(key, value)
        path = self.project_path if scope == "project" else self.user_path
        data = _read(path)
        data["schema_version"] = 1
        if scope == "project":
            data["workspace_schema_version"] = 1
        target = data
        parts = key.split(".")
        for part in parts[:-1]:
            child = target.setdefault(part, {})
            if not isinstance(child, dict):
                raise ConfigurationError(
                    f"configuration section {part} must be a mapping"
                )
            target = child
        target[parts[-1]] = value
        _atomic_write(path, yaml.safe_dump(data, sort_keys=False).encode("utf-8"))
        self.resolve()

    def reset(self, scope: ConfigurationScope) -> None:
        if scope == "project":
            content = {
                "schema_version": 1,
                "workspace_schema_version": 1,
                "behavior": {
                    "default_project_id": None,
                    "include_closed_in_critical_path": False,
                },
            }
            _atomic_write(
                self.project_path, yaml.safe_dump(content, sort_keys=False).encode()
            )
        else:
            self.user_path.unlink(missing_ok=True)

    def initialize(self, user_name: str | None = None) -> None:
        if not self.project_path.exists():
            self.reset("project")
        if user_name and not self.user_path.exists():
            self.set("identity.name", user_name, "user")
