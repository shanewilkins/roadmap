"""Terminal/JSON gap reconciliation over canonical real-storage records."""

import json

from roadmap.bootstrap import cli
from roadmap.domain.aggregates import Issue
from roadmap.domain.types import EntityId, IssueStatus, Title
from tests.fixtures.cli_workspace import NOW, run, seed
from tests.integration.cli.test_cli_requirement_governance import transition
from tests.integration.cli.test_cli_requirements import (
    canonical,
    command,
    create,
    enable,
)


def test_gap_terminal_and_json_share_counts_ids_and_write_nothing(
    workspace, cli_runner
):
    enable(cli_runner)
    requirement = transition(cli_runner, create(cli_runner), "accepted")
    orphan = Issue(EntityId("orphan"), NOW, NOW, title=Title("Orphan"))
    maintenance = Issue(
        EntityId("maintenance"),
        NOW,
        NOW,
        title=Title("Maintenance"),
        labels=("maintenance",),
        content="Keep CI runners supported.",
    )
    blocked = Issue(
        EntityId("blocked"),
        NOW,
        NOW,
        title=Title("Blocked implementation"),
        status=IssueStatus.BLOCKED,
    )
    seed(workspace, orphan, maintenance, blocked)
    command(
        cli_runner,
        "link",
        requirement["id"],
        "--relation",
        "implemented-by",
        "--target",
        "blocked",
    )
    before = canonical(workspace)
    payload = json.loads(
        run(cli_runner, "requirement", "gaps", "--format", "json").stdout
    )
    terminal = run(cli_runner, "requirement", "gaps").stdout
    assert payload["kind"] == "roadmap.requirement-gaps"
    assert payload["counts"]["unjustified_work"] == 1
    assert payload["counts"]["blocked_requirements"] == 1
    assert payload["categories"]["unjustified_work"][0]["entity_id"] == "orphan"
    assert (
        payload["categories"]["blocked_requirements"][0]["entity_id"]
        == requirement["id"]
    )
    assert "Work without requirement or maintenance rationale: 1" in terminal
    assert "Blocked requirements: 1" in terminal
    release_group = next(
        group
        for group in payload["groups"]
        if (group["dimension"], group["value"]) == ("release", "unassigned")
    )
    assert release_group["counts"]["unjustified_work"] == 1
    assert "Coverage groups:" in terminal
    assert "release=unassigned:" in terminal
    assert "unjustified_work (1): orphan" in terminal
    assert canonical(workspace) == before


def test_gaps_require_explicit_requirements_adoption(workspace, cli_runner):
    before = canonical(workspace)
    failed = cli_runner.invoke(cli, ["requirement", "gaps"])
    assert failed.exit_code == 1
    assert canonical(workspace) == before
