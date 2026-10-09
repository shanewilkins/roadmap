"""GH #3755/#3689: isolated identity, assignment and daily-work journeys."""

import json
import subprocess
from pathlib import Path

import pytest

from roadmap.bootstrap import cli
from tests.fixtures.ansi import clean_cli_output


def run(runner, *arguments, code=0):
    result = runner.invoke(cli, list(arguments))
    assert result.exit_code == code, clean_cli_output(result.output)
    return result


def detail(runner, identity):
    return json.loads(
        run(runner, "issue", "view", identity, "--format", "json").stdout
    )["record"]["issue"]


@pytest.fixture
def isolated_identity(tmp_path, monkeypatch, cli_runner):
    monkeypatch.chdir(tmp_path)
    personal = tmp_path / "personal"
    monkeypatch.setattr(Path, "home", lambda: personal)
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", "/dev/null")
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    subprocess.run(
        ["git", "init", str(tmp_path)], capture_output=True, check=True, timeout=15
    )
    run(cli_runner, "init", "--skip-project")
    return tmp_path


def test_missing_identity_is_actionable_and_preserves_unassigned_capture(
    isolated_identity, cli_runner
):
    missing = run(cli_runner, "today", code=1)
    assert "roadmap config set identity.name" in clean_cli_output(missing.stderr)
    assert "git config user.name" in clean_cli_output(missing.stderr)
    assert "opentelemetry" not in clean_cli_output(missing.output)
    identity = run(
        cli_runner, "issue", "create", "--title", "Unassigned", "--print-id"
    ).stdout.strip()
    assert detail(cli_runner, identity)["assignee"] is None


@pytest.mark.parametrize(
    "configured,git_name,expected",
    [
        ("alice", "Bob Smith", "alice"),
        (" alice ", "Bob Smith", "alice"),
        (None, " Bob Smith ", "Bob Smith"),
        ("   ", " Bob Smith ", "Bob Smith"),
    ],
)
def test_configured_and_git_identity_agree_with_today_and_assignments(
    isolated_identity, cli_runner, configured, git_name, expected
):
    subprocess.run(
        ["git", "config", "user.name", git_name],
        capture_output=True,
        check=True,
        timeout=15,
    )
    if configured is not None:
        run(cli_runner, "config", "set", "identity.name", json.dumps(configured))
    milestone = run(
        cli_runner, "milestone", "create", "--title", "Onboarding", "--print-id"
    ).stdout.strip()
    identities = []
    for title, options in [
        ("Auto assigned", []),
        ("Explicit assigned", ["--assignee", f" {expected} "]),
    ]:
        identity = run(
            cli_runner,
            "issue",
            "create",
            "--title",
            title,
            "--priority",
            "high",
            "--milestone",
            milestone,
            "--print-id",
            *options,
        ).stdout.strip()
        assert detail(cli_runner, identity)["assignee"] == expected
        identities.append(identity)
    today = run(cli_runner, "today")
    for identity in identities:
        assert identity in clean_cli_output(today.stdout)
    assert "opentelemetry" not in clean_cli_output(today.output)


def test_assignment_edit_clear_and_invalid_writes(isolated_identity, cli_runner):
    identity = run(
        cli_runner,
        "issue",
        "create",
        "--title",
        "Assignment",
        "--assignee",
        " Alice Smith ",
        "--print-id",
    ).stdout.strip()
    assert detail(cli_runner, identity)["assignee"] == "Alice Smith"
    run(cli_runner, "issue", "update", identity, "--assignee", " Bob Smith ")
    assert detail(cli_runner, identity)["assignee"] == "Bob Smith"
    before = {p: p.read_bytes() for p in (isolated_identity / ".roadmap").rglob("*.md")}
    for blank in ("", "   "):
        run(
            cli_runner,
            "issue",
            "create",
            "--title",
            "Invalid",
            "--assignee",
            blank,
            code=1,
        )
        run(cli_runner, "issue", "update", identity, "--assignee", blank, code=1)
        assert before == {
            p: p.read_bytes() for p in (isolated_identity / ".roadmap").rglob("*.md")
        }
    run(cli_runner, "issue", "update", identity, "--clear-assignee")
    assert detail(cli_runner, identity)["assignee"] is None
