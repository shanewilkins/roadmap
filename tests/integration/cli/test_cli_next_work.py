"""Real-storage read-only next-work and shared terminal/JSON policy."""

import json

import pytest

from roadmap.adapters.outbound.system import SystemClock
from roadmap.domain.aggregates import Issue
from roadmap.domain.types import EntityId, IssueStatus, IssueType, Priority, Title
from tests.fixtures.cli_workspace import NOW, run, seed
from tests.integration.cli.test_cli_requirement_governance import transition
from tests.integration.cli.test_cli_requirements import (
    canonical,
    command,
    create,
    enable,
)

AT = "2026-10-23T13:00:00-05:00"


def test_issue_only_next_work_is_read_only_and_reconciles_formats(
    workspace, cli_runner
):
    critical = Issue(
        EntityId("critical"),
        NOW,
        NOW,
        title=Title("Critical tooling bug"),
        priority=Priority.CRITICAL,
        issue_type=IssueType.BUG,
        labels=("maintenance",),
        content="Restore broken build tooling.",
    )
    orphan = Issue(EntityId("orphan"), NOW, NOW, title=Title("Unjustified"))
    current = Issue(
        EntityId("current"),
        NOW,
        NOW,
        title=Title("Current maintenance"),
        status=IssueStatus.IN_PROGRESS,
        labels=("maintenance",),
        content="Upgrade CI.",
    )
    seed(workspace, orphan, current, critical)
    before = canonical(workspace)
    raw = run(cli_runner, "next-work", "--at", AT, "--format", "json").stdout
    payload = json.loads(raw)
    assert raw == run(cli_runner, "next-work", "--at", AT, "--format", "json").stdout
    assert payload["schema_version"] == 1
    assert payload["policy"] == "roadmap.next-work:v1"
    assert payload["as_of"] == "2026-10-23T18:00:00+00:00"
    assert [item["entity_id"] for item in payload["recommended"]] == ["critical"]
    assert [item["entity_id"] for item in payload["current_work"]] == ["current"]
    assert [item["entity_id"] for item in payload["blocked"]] == ["orphan"]
    terminal = run(cli_runner, "next-work", "--at", AT).stdout
    for section in ("recommended", "current_work", "blocked"):
        for item in payload[section]:
            assert item["entity_id"] in terminal
            for reason in (*item["reasons"], *item["blockers"]):
                assert reason in terminal
    assert canonical(workspace) == before
    assert not (workspace.roadmap_dir / "requirements").exists()


def test_governed_issue_recommendations_and_post_ranking_limit(workspace, cli_runner):
    enable(cli_runner)
    owner = transition(cli_runner, create(cli_runner), "accepted")
    work = Issue(EntityId("work"), NOW, NOW, title=Title("Implement intent"))
    maintenance = Issue(
        EntityId("maintenance"),
        NOW,
        NOW,
        title=Title("Maintenance"),
        priority=Priority.LOW,
        labels=("maintenance",),
        content="Refresh CI.",
    )
    seed(workspace, work, maintenance)
    command(
        cli_runner,
        "link",
        owner["id"],
        "--relation",
        "implemented-by",
        "--target",
        "work",
    )
    before = canonical(workspace)
    report = json.loads(
        run(
            cli_runner, "next-work", "--at", AT, "--format", "json", "--limit", "1"
        ).stdout
    )
    assert report["recommended_total"] == 2
    assert [item["entity_id"] for item in report["recommended"]] == ["work"]
    assert report["recommended"][0]["requirement_ids"] == [owner["id"]]
    assert report["blocked"][0]["action"] == "verify-requirement"
    assert canonical(workspace) == before


@pytest.mark.parametrize(
    "arguments",
    [
        ("--at", "garbage"),
        ("--at", "2026-10-23"),
        ("--at", "2026-10-23T13:00:00"),
        ("--limit", "0"),
        ("--limit", "-1"),
    ],
)
def test_invalid_next_work_input_is_explicit_and_does_not_write(
    workspace, cli_runner, arguments
):
    before = canonical(workspace)
    failed = run(cli_runner, "next-work", *arguments, code=2)
    assert "Invalid value" in failed.stderr
    assert canonical(workspace) == before


def test_clock_default_and_missing_projection_preserve_canonical_result(
    workspace, cli_runner, monkeypatch
):
    work = Issue(
        EntityId("maintenance"),
        NOW,
        NOW,
        title=Title("Maintenance"),
        labels=("maintenance",),
        content="Keep dependencies supported.",
    )
    seed(workspace, work)
    monkeypatch.setattr(SystemClock, "now", lambda self: NOW)
    before = canonical(workspace)
    first = json.loads(run(cli_runner, "next-work", "--format", "json").stdout)
    assert first["as_of"] == NOW.value.isoformat()
    (workspace.roadmap_dir / "db" / "projection.db").unlink()
    second = json.loads(run(cli_runner, "next-work", "--format", "json").stdout)
    assert first == second
    assert canonical(workspace) == before


def test_application_rejects_invalid_limit_without_mutation(workspace):
    before = canonical(workspace)
    from roadmap.application.failures import ApplicationFailure

    with pytest.raises(ApplicationFailure, match="limit must be positive"):
        workspace.requirements.next_work(limit=0)
    assert canonical(workspace) == before
