"""Small workflow improvements must stay safe, discoverable, and scriptable."""

import json
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from roadmap.application.contracts import IssueMutationResult
from roadmap.bootstrap.core import find_existing_core
from roadmap.domain.aggregates import Issue, Milestone, Project
from roadmap.domain.types import EntityId, Name, Title
from tests.fixtures.ansi import clean_cli_output
from tests.fixtures.cli_workspace import NOW, canonical_bytes, run, seed


def test_id_only_creation_round_trips_into_lookup(workspace, cli_runner):
    run(cli_runner, "config", "set", "identity.name", "alice")
    result = run(
        cli_runner, "issue", "create", "--title", "Script-created", "--print-id"
    )
    identity = result.stdout.strip()
    assert result.stdout == identity + "\n"
    assert result.stderr == ""
    assert (
        workspace.issue_queries.view(EntityId(identity)).issue.title == "Script-created"
    )
    detail = run(cli_runner, "issue", "view", identity)
    assert "Script-created" in clean_cli_output(detail.output)


def test_id_only_creation_routes_stale_projection_warning_to_stderr(
    workspace, cli_runner, monkeypatch
):
    value = Issue(EntityId("issue-warning"), NOW, NOW, title=Title("Saved"))
    monkeypatch.setattr(
        workspace.issue_mutations,
        "create",
        lambda _command: IssueMutationResult(value, True),
    )
    result = run(
        cli_runner,
        "issue",
        "create",
        "--title",
        "Saved",
        "--print-id",
        obj={"core": workspace},
    )
    assert result.stdout == "issue-warning\n"
    assert "canonical Markdown was saved" in result.stderr


@pytest.mark.parametrize("failure", [False, True])
def test_id_only_branch_notification_and_failure_preserve_created_issue(
    workspace, cli_runner, monkeypatch, failure
):
    def create_branch(*_args, **_kwargs):
        if failure:
            raise ValueError("branch unavailable")
        return SimpleNamespace(branch="issue/demo")

    monkeypatch.setattr(workspace.local_git, "create_issue_branch", create_branch)
    result = run(
        cli_runner,
        "issue",
        "create",
        "--title",
        "Branch-linked",
        "--print-id",
        "--git-branch",
        code=int(failure),
        obj={"core": workspace},
    )
    identity = EntityId(result.stdout.strip())
    assert workspace.issue_queries.view(identity).issue.title == "Branch-linked"
    assert (
        "branch unavailable" in result.stderr
        if failure
        else "Created branch: issue/demo" in result.stderr
    )


@pytest.mark.parametrize("kind", ["issue", "project", "milestone"])
def test_ambiguous_prefix_lists_candidates_without_mutation(
    workspace, cli_runner, kind
):
    constructor = {
        "issue": lambda identity, label: Issue(
            EntityId(identity), NOW, NOW, title=Title(label)
        ),
        "project": lambda identity, label: Project(
            EntityId(identity), NOW, NOW, name=Name(label)
        ),
        "milestone": lambda identity, label: Milestone(
            EntityId(identity), NOW, NOW, name=Name(label)
        ),
    }[kind]
    seed(
        workspace,
        constructor("same-a", "First choice"),
        constructor("same-b", "Second choice"),
    )
    before = canonical_bytes(workspace)
    result = run(cli_runner, kind, "view", "same-", code=1)
    output = clean_cli_output(result.output)
    assert "same-a: First choice" in output
    assert "same-b: Second choice" in output
    assert "use a complete ID" in output
    assert canonical_bytes(workspace) == before
    run(cli_runner, kind, "view", "same-a")


@pytest.mark.parametrize("kind", ["project", "milestone"])
def test_duplicate_names_are_ambiguous_and_exact_ids_still_work(
    workspace, cli_runner, kind
):
    constructor = Project if kind == "project" else Milestone
    seed(
        workspace,
        constructor(EntityId("a"), NOW, NOW, name=Name("Shared name")),
        constructor(EntityId("b"), NOW, NOW, name=Name("Shared name")),
    )
    result = run(cli_runner, kind, "view", "Shared name", code=1)
    output = clean_cli_output(result.output)
    assert (
        "Ambiguous" in output
        and "a: Shared name" in output
        and "b: Shared name" in output
    )
    run(cli_runner, kind, "view", "a")


@pytest.mark.parametrize(
    "key,scope,value",
    [
        ("output.format", "user", "rich"),
        ("display.table_width", "user", 100),
        ("behavior.confirm_destructive", "user", True),
        ("behavior.default_project_id", "project", None),
    ],
)
def test_configuration_explanation_reports_effective_default(
    workspace, cli_runner, key, scope, value
):
    result = run(cli_runner, "config", "explain", key, "--format", "json")
    assert json.loads(result.stdout) == {
        "key": key,
        "scope": scope,
        "source": "default" if key != "behavior.default_project_id" else "project",
        "value": value,
    }
    plain = run(cli_runner, "config", "explain", key)
    assert f"Scope: {scope}" in clean_cli_output(plain.output)


@pytest.mark.parametrize(
    "key,value,scope,expected",
    [
        ("behavior.show_tips", "false", "user", False),
        ("output.columns", "[id, title]", "user", ["id", "title"]),
        ("behavior.default_project_id", "project-a", "project", "project-a"),
        ("identity.name", "alice", "user", "alice"),
    ],
)
def test_configuration_explanation_tracks_owner_and_configured_value(
    workspace, cli_runner, key, value, scope, expected
):
    before_project = workspace.configuration.project_path.read_bytes()
    run(
        cli_runner,
        "config",
        "set",
        key,
        value,
        *(["--project"] if scope == "project" else []),
    )
    result = run(cli_runner, "config", "explain", key, "--format", "json")
    assert json.loads(result.stdout) == {
        "key": key,
        "scope": scope,
        "source": scope,
        "value": expected,
    }
    if scope == "user":
        assert workspace.configuration.project_path.read_bytes() == before_project
    assert str(Path.home()) not in result.stdout


def test_unknown_and_wrong_scope_configuration_commands_do_not_write(
    workspace, cli_runner
):
    before = workspace.configuration.project_path.read_bytes()
    run(cli_runner, "config", "explain", "unknown.key", code=1)
    run(cli_runner, "config", "set", "identity.name", "alice", "--project", code=1)
    run(cli_runner, "config", "get", "identity.name", code=1)
    run(cli_runner, "config", "get", "unknown.key", code=1)
    assert workspace.configuration.project_path.read_bytes() == before


def test_scoped_configuration_get_view_and_reset(workspace, cli_runner):
    run(cli_runner, "config", "set", "identity.name", "alice")
    assert "alice" in clean_cli_output(
        run(cli_runner, "config", "get", "identity.name").output
    )
    assert "alice" in clean_cli_output(run(cli_runner, "config", "view").output)
    run(cli_runner, "config", "view", "--project")
    run(cli_runner, "config", "reset", input="n\n", code=1)
    assert workspace.configuration.get("identity.name") == "alice"
    before = workspace.configuration.project_path.read_bytes()
    run(cli_runner, "config", "reset", input="y\n")
    assert workspace.configuration.project_path.read_bytes() == before
    assert workspace.configuration.explain("identity.name")["source"] == "default"


def test_nearest_workspace_discovery_and_missing_workspace(tmp_path, workspace):
    child = tmp_path / "nested/deep"
    child.mkdir(parents=True)
    found = find_existing_core(child)
    assert found is not None
    assert found.roadmap_dir == workspace.roadmap_dir
    outside = tmp_path / "home"
    # Parent discovery correctly finds this workspace; a sibling of the temp
    # workspace has no initialized ancestor.
    found = find_existing_core(outside)
    assert found is not None
    assert found.roadmap_dir == workspace.roadmap_dir
    assert find_existing_core(Path("/")) is None


@pytest.mark.parametrize("shell", ["bash", "zsh", "fish"])
def test_completion_source_works_without_a_workspace(tmp_path, shell):
    executable = Path(sys.executable).with_name("roadmap")
    assert executable.is_file()
    result = subprocess.run(
        [executable],
        cwd=tmp_path,
        env={**os.environ, "_ROADMAP_COMPLETE": f"{shell}_source"},
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert result.returncode == 0, result.stderr
    assert "roadmap" in result.stdout
    assert not tuple(tmp_path.iterdir())


def test_completion_suggests_choice_values_without_initializing(tmp_path):
    executable = Path(sys.executable).with_name("roadmap")
    assert executable.is_file()
    result = subprocess.run(
        [executable],
        cwd=tmp_path,
        env={
            **os.environ,
            "_ROADMAP_COMPLETE": "bash_complete",
            "COMP_WORDS": "roadmap issue create --priority h",
            "COMP_CWORD": "4",
        },
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert result.returncode == 0, result.stderr
    assert "plain,high" in result.stdout
    assert not tuple(tmp_path.iterdir())
