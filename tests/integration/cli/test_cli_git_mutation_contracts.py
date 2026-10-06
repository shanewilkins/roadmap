"""Real local Git state and canonical outcomes for CLI branch flags."""

import subprocess
from pathlib import Path

import pytest

from roadmap.bootstrap import cli
from tests.fixtures.cli_workspace import canonical_bytes, run, seed
from tests.integration.cli.test_cli_mutation_contracts import entity, load


def git(*args):
    return subprocess.run(
        ["git", *args], check=True, capture_output=True, text=True, timeout=15
    ).stdout.strip()


@pytest.fixture
def local_git(workspace, monkeypatch):
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", "/dev/null")
    seed(workspace, entity("issue", "target"), entity("issue", "survivor"))
    git("init", "--initial-branch=main")
    git("config", "user.name", "Roadmap test")
    git("config", "user.email", "roadmap-test@example.invalid")
    git("config", "commit.gpgsign", "false")
    git("config", "core.hooksPath", "/dev/null")
    Path(".gitignore").write_text(".roadmap/db/\nhome/\n", encoding="utf-8")
    Path("notes.txt").write_text("original notes\n", encoding="utf-8")
    git("add", ".")
    git("commit", "-m", "Test fixture")
    return workspace


@pytest.mark.parametrize("checkout", [False, True])
@pytest.mark.parametrize("dirty,force", [(False, False), (True, False), (True, True)])
def test_git_branch_checkout_and_dirty_override_are_bounded(
    local_git, cli_runner, checkout, dirty, force
):
    if dirty:
        Path("notes.txt").write_text("uncommitted notes\n", encoding="utf-8")
    notes = Path("notes.txt").read_bytes()
    before = canonical_bytes(local_git)
    branches = git("branch", "--format=%(refname:short)")
    args = ["git", "branch", "target", "--checkout" if checkout else "--no-checkout"]
    if force:
        args.append("--force")
    run(cli_runner, *args, code=1 if dirty and not force else 0)
    assert Path("notes.txt").read_bytes() == notes
    if dirty and not force:
        assert git("branch", "--format=%(refname:short)") == branches
        assert git("branch", "--show-current") == "main"
        assert canonical_bytes(local_git) == before
    else:
        linked = load(local_git, "issue", "target").git_branches
        assert len(linked) == 1
        assert linked[0] in git("branch", "--format=%(refname:short)").splitlines()
        assert git("branch", "--show-current") == (linked[0] if checkout else "main")
        survivor = local_git.roadmap_dir / "issues/survivor.md"
        assert canonical_bytes(local_git)[survivor] == before[survivor]


@pytest.mark.parametrize("action", ["create", "start"])
def test_optional_git_failure_reports_committed_entity_without_retrying(
    local_git, cli_runner, action
):
    git("branch", "occupied")
    before = canonical_bytes(local_git)
    args = (
        ["issue", "create", "--title", "Created despite Git failure", "--print-id"]
        if action == "create"
        else ["issue", "start", "target"]
    )
    result = cli_runner.invoke(
        cli, [*args, "--git-branch", "--branch-name", "occupied", "--force"]
    )
    assert result.exit_code == 1
    assert "occupied" in result.stderr
    assert git("branch", "--show-current") == "main"
    assert git("branch", "--format=%(refname:short)").splitlines() == [
        "main",
        "occupied",
    ]
    if action == "create":
        identity = result.stdout.strip()
        created = load(local_git, "issue", identity)
        assert str(created.title) == "Created despite Git failure"
        assert len(canonical_bytes(local_git)) == len(before) + 1
    else:
        assert load(local_git, "issue", "target").status.value == "in-progress"
    survivor = local_git.roadmap_dir / "issues/survivor.md"
    assert canonical_bytes(local_git)[survivor] == before[survivor]


@pytest.mark.parametrize("name", ["../unsafe", "bad..name", "name;echo unsafe"])
def test_unsafe_git_branch_name_never_creates_a_branch(local_git, cli_runner, name):
    branches = git("branch", "--format=%(refname:short)")
    # Starting the issue commits before optional branch validation. That split
    # outcome is deliberate; the invalid branch must never reach Git creation.
    result = cli_runner.invoke(
        cli,
        ["issue", "start", "target", "--git-branch", "--branch-name", name, "--force"],
    )
    assert result.exit_code == 1
    assert git("branch", "--format=%(refname:short)") == branches
    assert git("branch", "--show-current") == "main"
    assert load(local_git, "issue", "target").git_branches == ()
