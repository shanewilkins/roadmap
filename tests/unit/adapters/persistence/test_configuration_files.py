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
        snapshot.user.table_width = 80  # type: ignore[misc, ty:invalid-assignment]


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


@pytest.mark.parametrize(
    "body,message",
    [
        ("not: [valid", "cannot read"),
        ("- not-a-mapping", "must be a mapping"),
        ("schema_version: true", "unsupported"),
        ("schema_version: -1", "unsupported"),
        ("behavior: scalar", "must be a mapping"),
        ("behavior:\n  show_tips: nope", "must be a boolean"),
        ("identity:\n  name: 42", "must be text"),
        ("output:\n  format: [json]", "must be text"),
        ("output:\n  columns: id", "must be a list"),
        ("display:\n  table_width: tiny", "must be >= 20"),
        ("identity:\n  token: private", "unknown or incorrectly scoped"),
    ],
)
def test_untrusted_user_configuration_fails_without_rewriting(tmp_path, body, message):
    store = _store(tmp_path)
    store.user_path.write_text(body)
    before = store.user_path.read_bytes()
    with pytest.raises(ConfigurationError, match=message):
        store.resolve()
    with pytest.raises(ConfigurationError):
        store.explain("identity.name")
    assert store.user_path.read_bytes() == before


@pytest.mark.parametrize(
    "body",
    [
        "workspace_schema_version: -1",
        "workspace_schema_version: true",
        "workspace_schema_version: later",
        "behavior:\n  default_project_id: 42",
        "identity:\n  name: wrong-scope",
    ],
)
def test_invalid_project_policy_is_rejected_without_rewriting(tmp_path, body):
    store = _store(tmp_path)
    store.project_path.write_text(body)
    before = store.project_path.read_bytes()
    with pytest.raises(ConfigurationError):
        store.resolve()
    assert store.project_path.read_bytes() == before


@pytest.mark.parametrize(
    "key,value",
    [
        ("identity.name", 42),
        ("output.columns", "id"),
        ("display.table_width", True),
        ("behavior.show_tips", "true"),
        ("unknown.key", "value"),
    ],
)
def test_bad_set_values_and_unknown_keys_preserve_both_scopes(tmp_path, key, value):
    store = _store(tmp_path)
    before = {p: p.read_bytes() for p in (store.project_path, store.user_path)}
    with pytest.raises(ConfigurationError):
        store.set(key, value, "user")
    assert {p: p.read_bytes() for p in before} == before


def test_configuration_read_denial_and_failed_replacement_preserve_bytes(
    tmp_path, monkeypatch
):
    import os
    from pathlib import Path

    store = _store(tmp_path)
    before = {p: p.read_bytes() for p in (store.project_path, store.user_path)}
    original = Path.read_text

    def read(path, *args, **kwargs):
        if path == store.user_path:
            raise PermissionError("injected config read denial")
        return original(path, *args, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(Path, "read_text", read)
        with pytest.raises(ConfigurationError, match="cannot read"):
            store.resolve()

    def replace(*_args, **_kwargs):
        raise OSError("injected config replacement denial")

    monkeypatch.setattr(os, "replace", replace)
    with pytest.raises(OSError, match="replacement denial"):
        store.set("identity.name", "bob", "user")
    assert {p: p.read_bytes() for p in before} == before


def test_missing_default_and_explicit_null_boolean_provenance(tmp_path):
    store = ConfigurationFiles(
        tmp_path / "missing-project.yaml", tmp_path / "user.yaml"
    )
    assert store.explain("output.format") == {
        "key": "output.format",
        "scope": "user",
        "source": "default",
        "value": "rich",
    }
    store.user_path.write_text(
        "behavior:\n  show_tips: null\nidentity:\n  name: null\n"
    )
    assert store.explain("behavior.show_tips")["source"] == "default"
    assert store.explain("behavior.show_tips")["value"] is True
    assert store.explain("identity.name")["source"] == "user"
    assert store.explain("identity.name")["value"] is None
