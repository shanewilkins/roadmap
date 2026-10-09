"""Selected workspace paths govern storage even from an unrelated directory."""

import json
from pathlib import Path

import pytest

from roadmap.bootstrap.core import create_core
from tests.fixtures.cli_workspace import canonical_bytes, run


def _selection(target, mode):
    if mode == "relative":
        return str(Path("..") / target.parent.name / target.name)
    if mode == "home":
        return str(Path("~") / target.parent.name / target.name)
    return str(target)


@pytest.mark.parametrize("mode", ["absolute", "relative", "home"])
def test_selected_workspace_names_project_from_selected_root(
    workspace, cli_runner, tmp_path, monkeypatch, mode
):
    caller = tmp_path / "unrelated caller"
    caller.mkdir()
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.chdir(caller)
    target = tmp_path / "Selected project" / "custom planning"
    selected = _selection(target, mode)
    before = canonical_bytes(workspace)
    preview = run(cli_runner, "--workspace", selected, "init", "--dry-run")
    assert "Would ensure project: Selected project" in preview.stdout
    assert not target.parent.exists()
    run(cli_runner, "--workspace", selected, "init")
    core = create_core(target.parent, target.name)
    assert [str(project.name) for project in core.planning.all_projects()] == [
        "Selected project"
    ]
    assert canonical_bytes(workspace) == before
    assert not (caller / ".roadmap").exists()


@pytest.mark.parametrize("mode", ["absolute", "relative", "home"])
def test_selected_custom_workspace_keeps_all_entity_operations_in_selected_storage(
    workspace, cli_runner, tmp_path, monkeypatch, mode
):
    caller = tmp_path / "unrelated caller"
    caller.mkdir()
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.chdir(caller)
    target = tmp_path / "Selected project" / "custom planning"
    selected = _selection(target, mode)
    before = canonical_bytes(workspace)

    def invoke(*arguments):
        return run(cli_runner, "--workspace", selected, *arguments)

    invoke("init", "--skip-project")
    ids = {}
    for kind in ["project", "milestone", "issue"]:
        ids[kind] = invoke(
            kind, "create", "--title", f"Selected-{kind}", "--print-id"
        ).stdout.strip()
        assert (target / f"{kind}s" / f"{ids[kind]}.md").is_file()
    invoke("milestone", "update", ids["milestone"], "--project", ids["project"])
    invoke("issue", "update", ids["issue"], "--milestone", ids["milestone"])
    invoke("issue", "close", ids["issue"], "--reason", "Verified selected workspace")
    invoke("issue", "archive", ids["issue"], "--yes")
    invoke("issue", "restore", ids["issue"], "--yes")
    record = json.loads(invoke("data", "export", "--format", "json").stdout)["issues"][
        0
    ]
    assert record["id"] == ids["issue"]
    assert record["status"] == "closed"
    assert record["milestone_id"] == ids["milestone"]
    health = json.loads(invoke("health", "scan", "--format", "json").stdout)
    assert health["findings"] == []
    assert (target / "db/projection.db").is_file()
    assert canonical_bytes(workspace) == before
    assert not (caller / ".roadmap").exists()


def test_nested_directory_discovers_nearest_default_workspace(
    workspace, cli_runner, tmp_path, monkeypatch
):
    nested = tmp_path / "nested directory" / "deeper"
    nested.mkdir(parents=True)
    monkeypatch.chdir(nested)
    identity = run(
        cli_runner, "issue", "create", "--title", "From nested directory", "--print-id"
    ).stdout.strip()
    assert (workspace.roadmap_dir / "issues" / f"{identity}.md").is_file()
    assert not (nested / ".roadmap").exists()

    parent_before = canonical_bytes(workspace)
    closer = tmp_path / "nested directory" / ".roadmap"
    run(cli_runner, "--workspace", str(closer), "init", "--skip-project")
    nearer_id = run(
        cli_runner, "issue", "create", "--title", "Nearest wins", "--print-id"
    ).stdout.strip()
    assert (closer / "issues" / f"{nearer_id}.md").is_file()
    assert canonical_bytes(workspace) == parent_before
    assert not (nested / ".roadmap").exists()
