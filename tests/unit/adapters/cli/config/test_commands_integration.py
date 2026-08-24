"""Phase 9 CLI contracts for declared configuration scopes."""

from types import SimpleNamespace

import pytest
import yaml

from roadmap.adapters.cli.config.commands import _parse_config_value, config
from roadmap.adapters.outbound.persistence.configuration import ConfigurationFiles


@pytest.fixture
def configured(tmp_path):
    project = tmp_path / "workspace/.roadmap/config.yaml"
    user = tmp_path / "user/config.yaml"
    store = ConfigurationFiles(project, user)
    store.initialize("alice")
    return store, {"core": SimpleNamespace(configuration=store)}


def test_view_keeps_project_and_user_scopes_separate(cli_runner, configured) -> None:
    _store, obj = configured

    project = cli_runner.invoke(config, ["view", "--level", "project"], obj=obj)
    user = cli_runner.invoke(config, ["view", "--level", "user"], obj=obj)

    assert project.exit_code == 0
    assert "workspace_schema_version: 1" in project.output
    assert "identity" not in project.output
    assert user.exit_code == 0
    assert "name: alice" in user.output
    assert "workspace_schema_version" not in user.output


def test_set_and_get_declared_keys(cli_runner, configured) -> None:
    store, obj = configured

    result = cli_runner.invoke(
        config,
        ["set", "behavior.default_project_id", "project-1", "--project"],
        obj=obj,
    )
    fetched = cli_runner.invoke(config, ["get", "behavior.default_project_id"], obj=obj)

    assert result.exit_code == 0
    assert fetched.exit_code == 0
    assert "project-1" in fetched.output
    assert store.resolve().project.default_project_id == "project-1"


@pytest.mark.parametrize(
    "arguments,message",
    [
        (
            ["set", "behavior.default_project_id", "project-1"],
            "project-scoped",
        ),
        (["set", "display.table_width", "120", "--project"], "user-scoped"),
        (["set", "github.token", "secret"], "unknown configuration key"),
    ],
)
def test_set_rejects_wrong_scope_unknown_keys_and_secrets(
    cli_runner, configured, arguments, message
) -> None:
    _store, obj = configured

    result = cli_runner.invoke(config, arguments, obj=obj)

    assert result.exit_code == 1
    assert message in result.output


def test_reset_user_does_not_touch_project_policy(cli_runner, configured) -> None:
    store, obj = configured
    store.set("behavior.default_project_id", "project-1", "project")

    result = cli_runner.invoke(config, ["reset"], input="y\n", obj=obj)

    assert result.exit_code == 0
    assert store.resolve().project.default_project_id == "project-1"
    assert not store.user_path.exists()


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("true", True),
        ("false", False),
        ("42", 42),
        ("3.5", 3.5),
        ("[id, title]", ["id", "title"]),
        ("plain", "plain"),
    ],
)
def test_parse_config_value(raw, expected) -> None:
    assert _parse_config_value(raw) == expected


def test_project_file_contains_no_user_provider_path_or_secret_data(configured) -> None:
    store, _obj = configured

    project = yaml.safe_load(store.project_path.read_text())

    assert set(project) == {"schema_version", "workspace_schema_version", "behavior"}
