"""Read-only views and explicit repair must retain their data-safety contracts."""

import csv
import io
import json

import pytest

from roadmap.application.contracts import HealthFinding, HealthReport, HealthSeverity
from roadmap.domain.aggregates import Issue, Milestone, Project
from roadmap.domain.types import (
    EntityId,
    IssueRelations,
    IssueStatus,
    MilestoneRelation,
    Name,
    Timestamp,
    Title,
)
from tests.fixtures.ansi import clean_cli_output, strip_ansi
from tests.fixtures.cli_workspace import NOW, canonical_bytes, run, seed


def test_health_offers_preview_and_only_confirmed_repair_writes(workspace, cli_runner):
    seed(
        workspace,
        Issue(EntityId("issue-a"), NOW, NOW, title=Title("Canonical survives")),
    )
    before = canonical_bytes(workspace)
    database = workspace.roadmap_dir / "db/projection.db"
    database.unlink()
    result = run(cli_runner, "health", code=1)
    assert "roadmap health fix --fix-type projection --dry-run" in clean_cli_output(
        result.output
    )
    assert not database.exists()
    assert (
        json.loads(run(cli_runner, "health", "--format", "json", code=1).stdout)[
            "findings"
        ][0]["safe_action"]
        == "projection"
    )
    preview = run(
        cli_runner, "health", "fix", "--fix-type", "projection", "--dry-run", code=1
    )
    assert "Repair preview" in clean_cli_output(preview.output)
    assert not database.exists()
    run(cli_runner, "health", "fix", "--fix-type", "projection", input="n\n", code=1)
    assert not database.exists()
    applied = run(cli_runner, "health", "fix", "--fix-type", "projection", input="y\n")
    assert "Repair applied" in clean_cli_output(applied.output)
    assert database.exists()
    assert canonical_bytes(workspace) == before
    assert (
        json.loads(run(cli_runner, "health", "--format", "json").stdout)["status"]
        == "healthy"
    )


def test_health_filters_preserve_exit_status_and_machine_schema(workspace, cli_runner):
    value = Issue(
        EntityId("issue-a"),
        NOW,
        NOW,
        title=Title("Broken reference"),
        relations=IssueRelations(milestone_id=EntityId("missing")),
    )
    seed(workspace, value)
    before = canonical_bytes(workspace)
    arguments = (
        "health",
        "scan",
        "--filter-entity",
        "issue",
        "--filter-severity",
        "error",
    )
    payload = json.loads(run(cli_runner, *arguments, "--output", "json", code=2).stdout)
    assert payload["exit_code"] == 2
    assert {f["finding_id"] for f in payload["findings"]} == {
        "canonical.broken-reference"
    }
    rows = list(
        csv.DictReader(
            io.StringIO(run(cli_runner, *arguments, "--output", "csv", code=2).stdout)
        )
    )
    assert rows[0]["entity_id"] == "issue-a"
    assert rows[0]["severity"] == "error"
    summary = run(cli_runner, *arguments, "--summary-only", code=2)
    assert "error=1" in clean_cli_output(summary.output)
    without = json.loads(
        run(cli_runner, *arguments, "--no-dependencies", "--output", "json").stdout
    )
    assert without["findings"] == [] and without["exit_code"] == 0
    run(cli_runner, "health", "db-integrity", "--json", code=2)
    run(
        cli_runner,
        "health",
        "fix",
        "--fix-type",
        "orphaned_issues",
        "--dry-run",
        code=1,
    )
    assert canonical_bytes(workspace) == before


def test_recovery_hint_is_preview_only_and_unknown_action_is_not_suggested(
    workspace, cli_runner, monkeypatch
):
    report = HealthReport(
        (
            HealthFinding(
                "transaction.interrupted",
                HealthSeverity.ERROR,
                "workspace",
                "Pending journal",
                safe_action="recovery",
            ),
            HealthFinding(
                "custom",
                HealthSeverity.WARNING,
                "workspace",
                "Needs review",
                safe_action="delete-everything",
            ),
        )
    )
    monkeypatch.setattr(workspace.health, "scan", lambda: report)
    result = run(cli_runner, "health", code=2, obj={"core": workspace})
    output = clean_cli_output(result.output)
    assert "roadmap health fix --fix-type recovery --dry-run" in output
    assert "delete-everything" not in output


@pytest.mark.parametrize("format_name", ["plain", "json", "csv", "markdown", "rich"])
def test_status_formats_and_exclusive_file_output_preserve_entities(
    workspace, cli_runner, tmp_path, format_name
):
    seed(workspace, Issue(EntityId("issue-a"), NOW, NOW, title=Title("Status issue")))
    before = canonical_bytes(workspace)
    result = run(cli_runner, "status", "--format", format_name)
    if format_name == "json":
        assert json.loads(result.stdout)["kind"] == "roadmap.status"
    else:
        assert "Entities" in clean_cli_output(result.output)
    output = tmp_path / "status.out"
    exported = run(
        cli_runner, "status", "--format", format_name, "--output", str(output)
    )
    assert exported.stdout == ""
    assert "Saved status" in exported.stderr
    saved = output.read_bytes()
    run(cli_runner, "status", "--format", format_name, "--output", str(output), code=1)
    assert output.read_bytes() == saved
    assert canonical_bytes(workspace) == before


def test_status_storage_error_is_reported_without_partial_canonical_writes(
    workspace, cli_runner, tmp_path
):
    before = canonical_bytes(workspace)
    run(cli_runner, "status", "--output", str(tmp_path / "missing/status.txt"), code=1)
    assert canonical_bytes(workspace) == before


@pytest.mark.parametrize("format_name", [None, "json", "csv"])
def test_critical_path_export_keeps_dependency_order_and_refuses_overwrite(
    workspace, cli_runner, tmp_path, format_name
):
    predecessor = Issue(
        EntityId("a"),
        NOW,
        NOW,
        title=Title("Prerequisite"),
        estimated_hours=2,
        relations=IssueRelations(blocks=(EntityId("b"),)),
    )
    dependent = Issue(
        EntityId("b"),
        NOW,
        NOW,
        title=Title("Dependent"),
        estimated_hours=3,
        relations=IssueRelations(depends_on=(predecessor.id,)),
    )
    seed(workspace, predecessor, dependent)
    before = canonical_bytes(workspace)
    arguments = (
        "analysis",
        "critical-path",
        *(["--export", format_name] if format_name else []),
    )
    result = run(cli_runner, *arguments)
    if format_name == "json":
        payload = json.loads(result.stdout)
        assert [node["issue_id"] for node in payload["critical_path"]] == ["a", "b"]
        assert payload["summary"]["total_duration"] == 5
    elif format_name == "csv":
        assert [
            row["issue_id"] for row in csv.DictReader(io.StringIO(result.stdout))
        ] == ["a", "b"]
    else:
        assert "5.0 hours" in clean_cli_output(result.output)
    output = tmp_path / "critical-path.out"
    assert run(cli_runner, *arguments, "--output", str(output)).stdout == ""
    saved = output.read_bytes()
    run(cli_runner, *arguments, "--output", str(output), code=1)
    assert output.read_bytes() == saved
    run(
        cli_runner, *arguments, "--output", str(tmp_path / "missing/export.txt"), code=1
    )
    assert canonical_bytes(workspace) == before


def test_empty_analysis_and_daily_identity_failure_are_read_only(workspace, cli_runner):
    before = canonical_bytes(workspace)
    assert "No active issues" in clean_cli_output(
        run(cli_runner, "analysis", "critical-path").output
    )
    run(cli_runner, "today", code=1)
    assert canonical_bytes(workspace) == before


def test_comment_and_dependency_journey_retains_reciprocal_links_and_reply_parent(
    workspace, cli_runner
):
    first = Issue(EntityId("a"), NOW, NOW, title=Title("First"))
    second = Issue(EntityId("b"), NOW, NOW, title=Title("Second"))
    third = Issue(EntityId("c"), NOW, NOW, title=Title("Third"))
    seed(workspace, first, second, third)
    assert "No comments yet" in clean_cli_output(
        run(cli_runner, "issue", "comment", "list", "a").output
    )
    run(cli_runner, "issue", "comment", "add", "a", "Top-level", "--author", "alice")
    run(
        cli_runner,
        "issue",
        "comment",
        "add",
        "a",
        "Reply",
        "--author",
        "bob",
        "--reply-to",
        "1",
    )
    comments = json.loads(
        run(cli_runner, "issue", "comment", "list", "a", "--format", "json").stdout
    )
    assert [(c["id"], c["in_reply_to"], c["author"]) for c in comments] == [
        (1, None, "alice"),
        (2, 1, "bob"),
    ]
    assert "  #2 @bob" in strip_ansi(
        run(cli_runner, "issue", "comment", "list", "a").output
    )
    run(cli_runner, "issue", "deps", "add", "b", "a")
    assert workspace.issue_queries.view(first.id).issue.relations.blocks == (second.id,)
    before = canonical_bytes(workspace)
    run(cli_runner, "issue", "deps", "add", "a", "b", code=1)
    run(
        cli_runner,
        "issue",
        "comment",
        "add",
        "a",
        "Orphan reply",
        "--reply-to",
        "999",
        code=1,
    )
    assert canonical_bytes(workspace) == before
    run(cli_runner, "issue", "deps", "update", "b", "a", "c")
    assert workspace.issue_queries.view(first.id).issue.relations.blocks == ()
    assert workspace.issue_queries.view(third.id).issue.relations.blocks == (second.id,)
    run(cli_runner, "issue", "deps", "remove", "b", "c")
    assert workspace.issue_queries.view(second.id).issue.relations.depends_on == ()
    assert workspace.issue_queries.view(third.id).issue.relations.blocks == ()


def test_planning_views_filters_and_daily_summary_match_canonical_scope(
    workspace, cli_runner
):
    from datetime import timedelta

    run(cli_runner, "config", "set", "identity.name", "alice")
    project = Project(
        EntityId("project-a"),
        NOW,
        NOW,
        name=Name("Project"),
        repository_url="https://example.com/repo",
        content="Project notes",
    )
    milestone = Milestone(
        EntityId("milestone-a"),
        NOW,
        NOW,
        name=Name("Milestone"),
        relation=MilestoneRelation(project.id),
        due_at=Timestamp(NOW.value + timedelta(days=2)),
        content="Milestone notes",
    )
    current = Issue(
        EntityId("active"),
        NOW,
        NOW,
        title=Title("Assigned task"),
        status=IssueStatus.IN_PROGRESS,
        assignee="alice",
        estimated_hours=4,
        relations=IssueRelations(milestone_id=milestone.id),
    )
    closed = Issue(
        EntityId("closed"),
        NOW,
        NOW,
        title=Title("Closed task"),
        status=IssueStatus.CLOSED,
        relations=IssueRelations(milestone_id=milestone.id),
    )
    seed(workspace, project, milestone, current, closed)
    before = canonical_bytes(workspace)
    assert "Project notes" in clean_cli_output(
        run(cli_runner, "project", "view", str(project.id)).output
    )
    detail = clean_cli_output(
        run(cli_runner, "milestone", "view", str(milestone.id), "--only-open").output
    )
    assert "Assigned task" in detail and "Closed task" not in detail
    empty = clean_cli_output(
        run(
            cli_runner, "milestone", "view", str(milestone.id), "--status", "blocked"
        ).output
    )
    assert "Assigned task" not in empty
    board = clean_cli_output(
        run(cli_runner, "milestone", "kanban", str(milestone.id)).output
    )
    assert "Assigned task" in board and "Closed task" in board
    today = clean_cli_output(run(cli_runner, "today").output)
    assert (
        "Daily Summary - alice" in today
        and "Assigned task" in today
        and "Closed task" not in today
    )
    assert canonical_bytes(workspace) == before
