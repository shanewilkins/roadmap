"""Phase 9 contracts for scoped immutable configuration."""

from dataclasses import FrozenInstanceError

import pytest
import yaml

from roadmap.adapters.outbound.persistence.configuration import (
    ConfigurationError,
    ConfigurationFiles,
)


def _store(tmp_path) -> ConfigurationFiles:
    store = ConfigurationFiles(
        tmp_path / "workspace/.roadmap/config.yaml",
        tmp_path / "user/config.yaml",
    )
    store.initialize("alice")
    return store


def test_resolve_returns_one_immutable_typed_snapshot(tmp_path) -> None:
    snapshot = _store(tmp_path).resolve()

    assert snapshot.project.workspace_schema_version == 1
    assert snapshot.user.name == "alice"
    with pytest.raises(FrozenInstanceError):
        snapshot.user.table_width = 80  # type: ignore[misc]


def test_invalid_existing_configuration_fails_before_mutation(tmp_path) -> None:
    store = _store(tmp_path)
    store.user_path.write_text(
        "schema_version: 1\ndisplay:\n  table_width: tiny\n", encoding="utf-8"
    )
    before = store.user_path.read_bytes()

    with pytest.raises(ConfigurationError, match="table_width"):
        store.set("behavior.show_tips", False, "user")

    assert store.user_path.read_bytes() == before


@pytest.mark.parametrize(
    ("key", "value", "message"),
    [
        ("display.table_width", 10, "must be >= 20"),
        ("behavior.show_tips", "false", "must be a boolean"),
        ("output.columns", ["id", 42], "must be a list"),
    ],
)
def test_typed_value_validation_precedes_write(tmp_path, key, value, message) -> None:
    store = _store(tmp_path)
    before = store.user_path.read_bytes()

    with pytest.raises(ConfigurationError, match=message):
        store.set(key, value, "user")

    assert store.user_path.read_bytes() == before


def test_future_configuration_schema_is_rejected(tmp_path) -> None:
    store = _store(tmp_path)
    store.project_path.write_text("schema_version: 9\n", encoding="utf-8")

    with pytest.raises(ConfigurationError, match="unsupported"):
        store.resolve()


def test_unknown_provider_and_wrong_scope_keys_are_rejected(tmp_path) -> None:
    store = _store(tmp_path)
    store.project_path.write_text(
        "schema_version: 1\nworkspace_schema_version: 1\ngithub:\n  repo: nope\n",
        encoding="utf-8",
    )

    with pytest.raises(ConfigurationError, match="github"):
        store.resolve()


def test_user_preferences_never_enter_canonical_project_config(tmp_path) -> None:
    store = _store(tmp_path)
    store.set("display.table_width", 120, "user")
    store.set("behavior.default_project_id", "project-1", "project")

    project = yaml.safe_load(store.project_path.read_text())
    user = yaml.safe_load(store.user_path.read_text())

    assert project["behavior"]["default_project_id"] == "project-1"
    assert "display" not in project
    assert user["display"]["table_width"] == 120
