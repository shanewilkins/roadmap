"""Committed Git authority and CLI preview in isolated repositories."""

import json
import subprocess
from unittest.mock import patch

import pytest

from roadmap.bootstrap import cli
from tests.fixtures.ansi import clean_cli_output


def run(runner, *arguments):
    result = runner.invoke(cli, list(arguments))
    assert result.exit_code == 0, result.output
    return result.stdout


def git(path, *arguments):
    return subprocess.run(
        ["git", "-C", str(path), *arguments],
        check=True,
        capture_output=True,
        text=True,
        timeout=15,
    ).stdout.strip()


@pytest.fixture
def committed_workspace(tmp_path, monkeypatch, cli_runner):
    monkeypatch.chdir(tmp_path)
    run(cli_runner, "init", "--skip-project")
    identity = run(
        cli_runner, "issue", "create", "--title", "Reported hang", "--print-id"
    ).strip()
    run(
        cli_runner,
        "issue",
        "update",
        identity,
        "--add-label",
        "github-publish:owner/repo#3756",
        "--add-label",
        "github-close:not-planned",
    )
    run(cli_runner, "issue", "close", identity, "--reason", "Not reproducible on 0.3.1")
    git(tmp_path, "init")
    git(tmp_path, "add", ".roadmap")
    git(
        tmp_path,
        "-c",
        "user.name=Test",
        "-c",
        "user.email=test@example.org",
        "commit",
        "-m",
        "Record triage closure",
    )
    return tmp_path, identity, git(tmp_path, "rev-parse", "HEAD")


def test_preview_uses_committed_closure_despite_uncommitted_reopen(
    committed_workspace, cli_runner
):
    path, identity, revision = committed_workspace
    run(cli_runner, "issue", "update", identity, "--status", "todo")
    with patch(
        "roadmap.adapters.outbound.github.GhClosurePublisher.publish",
        side_effect=AssertionError("preview must not publish"),
    ):
        payload = json.loads(
            run(cli_runner, "github", "publish-closures", "--repo", "owner/repo")
        )
    [publication] = payload["publications"]
    assert publication["result"] == "preview"
    assert revision in publication["evidence_url"]
    assert "Not reproducible" in publication["comment"]
    # Committing the reopened state removes the closure from the next plan.
    git(path, "add", ".roadmap")
    git(
        path,
        "-c",
        "user.name=Test",
        "-c",
        "user.email=test@example.org",
        "commit",
        "-m",
        "Reopen triage",
    )
    assert (
        json.loads(
            run(cli_runner, "github", "publish-closures", "--repo", "owner/repo")
        )["publications"]
        == []
    )


def test_uncommitted_closure_is_never_published(committed_workspace, cli_runner):
    path, identity, _revision = committed_workspace
    run(cli_runner, "issue", "update", identity, "--status", "todo")
    git(path, "add", ".roadmap")
    git(
        path,
        "-c",
        "user.name=Test",
        "-c",
        "user.email=test@example.org",
        "commit",
        "-m",
        "Reopen triage",
    )
    run(cli_runner, "issue", "close", identity, "--reason", "Uncommitted closure")
    with patch(
        "roadmap.adapters.outbound.github.GhClosurePublisher.publish",
        side_effect=AssertionError("no eligible closure"),
    ):
        assert (
            json.loads(
                run(
                    cli_runner,
                    "github",
                    "publish-closures",
                    "--repo",
                    "owner/repo",
                    "--apply",
                )
            )["publications"]
            == []
        )


def test_apply_passes_exact_plan_without_local_receipt_writes(
    committed_workspace, cli_runner
):
    path, _identity, _revision = committed_workspace
    before = {item: item.read_bytes() for item in (path / ".roadmap").rglob("*.md")}
    with patch(
        "roadmap.adapters.outbound.github.GhClosurePublisher.publish",
        return_value="already-closed",
    ) as publish:
        payload = json.loads(
            run(
                cli_runner,
                "github",
                "publish-closures",
                "--repo",
                "owner/repo",
                "--apply",
            )
        )
        assert publish.call_count == 1
    assert payload["publications"][0]["result"] == "already-closed"
    assert before == {
        item: item.read_bytes() for item in (path / ".roadmap").rglob("*.md")
    }


def test_missing_git_history_fails_without_publication(
    tmp_path, monkeypatch, cli_runner
):
    monkeypatch.chdir(tmp_path)
    run(cli_runner, "init", "--skip-project")
    git(tmp_path, "init")
    with patch(
        "roadmap.adapters.outbound.github.GhClosurePublisher.publish",
        side_effect=AssertionError("no snapshot"),
    ):
        result = cli_runner.invoke(
            cli, ["github", "publish-closures", "--repo", "owner/repo", "--apply"]
        )
    assert result.exit_code != 0
    assert "Git HEAD" in clean_cli_output(result.output)


def test_github_namespace_help(cli_runner):
    result = cli_runner.invoke(cli, ["github", "--help"])
    assert result.exit_code == 0
    assert "publish-closures" in clean_cli_output(result.output)
