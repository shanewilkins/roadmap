"""Human output must report scoped workload and give executable next steps."""

import pytest

from roadmap.domain.aggregates import Issue
from roadmap.domain.types import EntityId, IssueStatus, Title
from tests.fixtures.ansi import clean_cli_output
from tests.fixtures.cli_workspace import NOW, canonical_bytes, run, seed
from tests.integration.cli.test_cli_mutation_contracts import persistent_bytes


@pytest.mark.parametrize("selection", [("--assignee", "alice"), ("--my-issues",)])
def test_rich_listing_reports_selected_workload_and_estimate_units(
    workspace, cli_runner, selection
):
    run(cli_runner, "config", "set", "identity.name", "alice")
    seed(
        workspace,
        *(
            Issue(
                EntityId(identity),
                NOW,
                NOW,
                title=Title(identity),
                assignee=assignee,
                estimated_hours=hours,
                status=status,
            )
            for identity, assignee, hours, status in (
                ("minutes", "alice", 0.5, IssueStatus.TODO),
                ("hour", "alice", 1, IssueStatus.TODO),
                ("boundary", "alice", 24, IssueStatus.IN_PROGRESS),
                ("days", "alice", 32, IssueStatus.BLOCKED),
                ("unestimated", "alice", None, IssueStatus.TODO),
                ("excluded", "bob", 800, IssueStatus.TODO),
            )
        ),
    )
    before = persistent_bytes(workspace)
    result = run(cli_runner, "issue", "list", *selection, terminal_width=200)
    output = clean_cli_output(result.output)
    workload_owner = "alice" if selection[0] == "--assignee" else "you"
    for expected in (
        "30m",
        "1.0h",
        "24.0h",
        "4.0d",
        "Not estimated",
        f"Total estimated time for {workload_owner}: 7.2d",
        "todo: 3 issues",
        "in-progress: 1 issues",
        "blocked: 1 issues",
    ):
        assert expected in output
    assert "excluded" not in output
    assert persistent_bytes(workspace) == before


def test_empty_listing_suggests_a_working_create_command(workspace, cli_runner):
    result = run(cli_runner, "issue", "list")
    assert "roadmap issue create --title 'Issue title'" in clean_cli_output(
        result.output
    )
    run(cli_runner, "issue", "create", "--title", "Issue title")
    assert "Issue title" in clean_cli_output(run(cli_runner, "issue", "list").output)


def test_no_upcoming_milestone_explains_empty_selection_without_mutation(
    workspace, cli_runner
):
    before = canonical_bytes(workspace)
    result = run(cli_runner, "issue", "list", "--next-milestone")
    output = clean_cli_output(result.output)
    assert "No upcoming milestones with due dates found" in output
    assert "Create one with" not in output
    assert canonical_bytes(workspace) == before
