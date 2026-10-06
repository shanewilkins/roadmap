"""Distinguishing fixtures prove actual CLI selections and output contracts."""

import csv
import io
import json
from datetime import UTC, datetime

import pytest
import yaml

from roadmap.bootstrap import cli
from roadmap.domain.aggregates import Issue, Milestone, Project
from roadmap.domain.types import (
    EntityId,
    IssueRelations,
    IssueStatus,
    IssueType,
    MilestoneRelation,
    Name,
    Priority,
    ProjectStatus,
    RetentionState,
    Timestamp,
    Title,
)
from tests.fixtures.cli_workspace import NOW, run, seed
from tests.integration.cli.test_cli_mutation_contracts import persistent_bytes

PAST = Timestamp(datetime(2000, 1, 1, tzinfo=UTC))
FUTURE = Timestamp(datetime(2100, 1, 1, tzinfo=UTC))
VISIBLE_IDS = ["a", "b", "c", "d", "f"]


def build_query_workspace(workspace, cli_runner):
    run(cli_runner, "config", "set", "identity.name", "alice")
    seed(
        workspace,
        Project(
            EntityId("p-z"),
            NOW,
            NOW,
            name=Name("Zulu"),
            status=ProjectStatus.ACTIVE,
            priority=Priority.HIGH,
            owner="alice",
            target_end_at=PAST,
        ),
        Project(
            EntityId("p-a"),
            NOW,
            NOW,
            name=Name("Alpha"),
            status=ProjectStatus.ON_HOLD,
            priority=Priority.LOW,
            owner="bob",
        ),
        Project(
            EntityId("p-b"),
            NOW,
            NOW,
            name=Name("Beta"),
            status=ProjectStatus.ACTIVE,
            priority=Priority.HIGH,
            owner="alice",
            target_end_at=FUTURE,
        ),
        Milestone(
            EntityId("m-old"),
            NOW,
            NOW,
            name=Name("Old"),
            due_at=PAST,
            relation=MilestoneRelation(EntityId("p-z")),
        ),
        Milestone(
            EntityId("m-new"),
            NOW,
            NOW,
            name=Name("New"),
            due_at=FUTURE,
            relation=MilestoneRelation(EntityId("p-a")),
        ),
        Issue(
            EntityId("a"),
            NOW,
            NOW,
            title=Title("Café alpha"),
            issue_type=IssueType.BUG,
            priority=Priority.HIGH,
            assignee="alice",
            due_at=PAST,
            relations=IssueRelations(milestone_id=EntityId("m-old")),
        ),
        Issue(
            EntityId("b"),
            NOW,
            NOW,
            title=Title("Beta"),
            issue_type=IssueType.OTHER,
            priority=Priority.LOW,
            assignee="bob",
            status=IssueStatus.IN_PROGRESS,
            due_at=FUTURE,
            content="needle body",
        ),
        Issue(
            EntityId("c"),
            NOW,
            NOW,
            title=Title("Gamma"),
            issue_type=IssueType.BUG,
            priority=Priority.HIGH,
            assignee="alice",
            status=IssueStatus.BLOCKED,
            relations=IssueRelations(milestone_id=EntityId("m-new")),
        ),
        Issue(
            EntityId("d"),
            NOW,
            NOW,
            title=Title("Delta"),
            status=IssueStatus.CLOSED,
            relations=IssueRelations(milestone_id=EntityId("m-old")),
        ),
        Issue(
            EntityId("e"),
            NOW,
            NOW,
            title=Title("Archived"),
            status=IssueStatus.CLOSED,
            retention=RetentionState.ARCHIVED,
            assignee="bob",
            priority=Priority.LOW,
        ),
        Issue(
            EntityId("f"),
            NOW,
            NOW,
            title=Title("Feature"),
            issue_type=IssueType.FEATURE,
            headline="needle headline",
        ),
    )
    return workspace


def issue_table_fragment(stdout):
    """Inspect table selection only; the legacy prose prefix is an open defect.

    This deliberately does NOT establish whole-stdout JSON validity. The
    step-two evidence records that separate machine-output contract failure.
    """
    start = stdout.index("{")
    payload, end = json.JSONDecoder().raw_decode(stdout[start:])
    assert not stdout[start + end :].strip()
    return payload


@pytest.fixture
def query_workspace(workspace, cli_runner):
    return build_query_workspace(workspace, cli_runner)


@pytest.mark.parametrize(
    "flags,expected",
    [
        ([], VISIBLE_IDS),
        (["--scope", "all"], ["a", "b", "c", "d", "e", "f"]),
        (["--scope", "closed"], ["d"]),
        (["--scope", "archived"], ["e"]),
        (["--open"], ["a", "b", "c", "f"]),
        (["--blocked"], ["c"]),
        (["--status", "in-progress"], ["b"]),
        (["--priority", "high"], ["a", "c"]),
        (["--issue-type", "bug"], ["a", "c"]),
        (["--overdue"], ["a"]),
        (["--search", "CAFÉ"], ["a"]),
        (["--search", "needle"], ["b", "f"]),
        (["--backlog"], ["b", "f"]),
        (["backlog"], ["b", "f"]),
        (["--unassigned"], ["b", "f"]),
        (["--milestone", "m-old"], ["a", "d"]),
        (["--next-milestone"], ["a", "d"]),
        (["--assignee", "alice"], ["a", "c"]),
        (["--my-issues"], ["a", "c"]),
        (["--my-issues", "--priority", "high", "--overdue", "--search", "CAFÉ"], ["a"]),
    ],
)
def test_issue_query_flags_select_exact_records_without_writes(
    query_workspace, cli_runner, flags, expected
):
    before = persistent_bytes(query_workspace)
    payload = issue_table_fragment(
        run(cli_runner, "issue", "list", *flags, "--format", "json").stdout
    )
    assert [row[0] for row in payload["rows"]] == expected
    assert payload["metadata"]["returned"] == len(expected)
    assert persistent_bytes(query_workspace) == before


@pytest.mark.parametrize(
    "flags",
    [
        ["--my-issues", "--assignee", "alice"],
        ["--milestone", "m-old", "--backlog"],
        ["--next-milestone", "--backlog"],
        ["--next-milestone", "--milestone", "m-old"],
    ],
)
def test_conflicting_issue_selectors_refuse_without_writes(
    query_workspace, cli_runner, flags
):
    before = persistent_bytes(query_workspace)
    result = cli_runner.invoke(cli, ["issue", "list", *flags, "--format", "json"])
    assert result.exit_code == 1
    assert result.stdout == ""
    assert "Cannot combine" in result.stderr
    assert persistent_bytes(query_workspace) == before


@pytest.mark.parametrize(
    "flags,expected",
    [
        ([], ["p-a", "p-b", "p-z"]),
        (["--owner", "alice"], ["p-b", "p-z"]),
        (["--priority", "low"], ["p-a"]),
        (["--status", "on-hold"], ["p-a"]),
        (["--overdue"], ["p-z"]),
        (
            [
                "--owner",
                "alice",
                "--priority",
                "high",
                "--status",
                "active",
                "--overdue",
            ],
            ["p-z"],
        ),
        (["--filter", "owner=alice,priority=high"], ["p-b", "p-z"]),
        (["--owner", "alice", "--filter", "name=Beta"], ["p-b"]),
        (["--owner", "nobody"], []),
    ],
)
def test_project_query_filters_and_intersections_are_exact(
    query_workspace, cli_runner, flags, expected
):
    before = persistent_bytes(query_workspace)
    payload = json.loads(
        run(cli_runner, "project", "list", *flags, "--format", "json").stdout
    )
    assert [row[0] for row in payload["rows"]] == expected
    assert persistent_bytes(query_workspace) == before


@pytest.mark.parametrize(
    "command,column,ascending",
    [
        ("project", "name", ["Alpha", "Beta", "Zulu"]),
        ("milestone", "name", ["New", "Old"]),
    ],
)
@pytest.mark.parametrize("direction", ["asc", "desc"])
def test_single_column_sort_order_is_exact(
    query_workspace, cli_runner, command, column, ascending, direction
):
    before = persistent_bytes(query_workspace)
    payload = json.loads(
        run(
            cli_runner,
            command,
            "list",
            "--format",
            "json",
            "--columns",
            column,
            "--sort-by",
            f"{column}:{direction}",
        ).stdout
    )
    assert payload["rows"] == [
        [name] for name in (ascending if direction == "asc" else ascending[::-1])
    ]
    assert payload["metadata"]["selected_columns"] == [column]
    assert persistent_bytes(query_workspace) == before


@pytest.mark.parametrize(
    "flags,expected",
    [
        ([], ["New", "Old"]),
        (["--overdue"], ["Old"]),
        (["--filter", "name=New"], ["New"]),
        (["--filter", "due_date=2100-01-01"], ["New"]),
        (["--overdue", "--filter", "name=Old"], ["Old"]),
    ],
)
def test_milestone_filters_are_exact(query_workspace, cli_runner, flags, expected):
    payload = json.loads(
        run(cli_runner, "milestone", "list", *flags, "--format", "json").stdout
    )
    assert [row[0] for row in payload["rows"]] == expected


@pytest.mark.parametrize(
    "command,columns,expected",
    [
        ("project", "name,id", [["Alpha", "p-a"], ["Beta", "p-b"], ["Zulu", "p-z"]]),
        ("milestone", "name,status", [["New", "open"], ["Old", "open"]]),
    ],
)
@pytest.mark.parametrize("format_name", ["json", "csv"])
def test_selected_columns_have_exact_order_and_values(
    query_workspace, cli_runner, command, columns, expected, format_name
):
    before = persistent_bytes(query_workspace)
    result = run(
        cli_runner, command, "list", "--columns", columns, "--format", format_name
    )
    if format_name == "json":
        payload = json.loads(result.stdout)
        assert payload["metadata"]["selected_columns"] == columns.split(",")
        assert payload["rows"] == expected
    else:
        reader = csv.DictReader(io.StringIO(result.stdout))
        rows = list(reader)
        assert reader.fieldnames is not None
        assert [s.lower() for s in reader.fieldnames] == columns.split(",")
        assert [list(row.values()) for row in rows] == expected
    assert result.stderr == ""
    assert persistent_bytes(query_workspace) == before


@pytest.mark.parametrize("command", ["issue", "milestone", "project"])
@pytest.mark.parametrize(
    "flags",
    [
        ["--columns", "unknown"],
        ["--sort-by", "unknown"],
        ["--sort-by", "name:sideways"],
        ["--filter", "unknown=value"],
        ["--format", "unsupported"],
    ],
)
def test_bad_output_options_refuse_without_state_changes(
    query_workspace, cli_runner, command, flags
):
    before = persistent_bytes(query_workspace)
    result = cli_runner.invoke(cli, [command, "list", *flags])
    assert result.exit_code != 0
    assert result.stderr
    assert persistent_bytes(query_workspace) == before


@pytest.mark.parametrize(
    "filter_value,expected",
    [
        (None, ["a", "b", "c", "d", "e", "f"]),
        ("status=open", ["a", "b", "c", "f"]),
        ("priority=high", ["a", "c"]),
        ("issue_type=bug", ["a", "c"]),
        ("assignee=bob", ["b", "e"]),
        ("retention=archived", ["e"]),
        ("retention=closed", ["d"]),
    ],
)
@pytest.mark.parametrize("format_name", ["json", "csv"])
def test_export_filters_and_formats_have_exact_record_sets(
    query_workspace, cli_runner, filter_value, expected, format_name
):
    before = persistent_bytes(query_workspace)
    flags = ["--filter", filter_value] if filter_value else []
    result = run(cli_runner, "data", "export", *flags, "--format", format_name)
    records = (
        json.loads(result.stdout)["issues"]
        if format_name == "json"
        else list(csv.DictReader(io.StringIO(result.stdout)))
    )
    assert [r["id"] for r in records] == expected
    assert result.stderr == ""
    assert persistent_bytes(query_workspace) == before


@pytest.mark.parametrize(
    "filter_value",
    ["invalid", "unknown=value", "status=", "=open", "retention=invalid"],
)
def test_invalid_export_filter_refuses_without_writes(
    query_workspace, cli_runner, filter_value
):
    before = persistent_bytes(query_workspace)
    result = cli_runner.invoke(
        cli, ["data", "export", "--filter", filter_value, "--format", "json"]
    )
    assert result.exit_code == 2
    assert result.stdout == ""
    assert persistent_bytes(query_workspace) == before


@pytest.mark.parametrize("command", ["project", "milestone"])
@pytest.mark.parametrize("format_name", ["rich", "plain", "json", "csv", "markdown"])
def test_list_formats_retain_records_for_simple_values(
    query_workspace, cli_runner, command, format_name
):
    before = persistent_bytes(query_workspace)
    result = run(cli_runner, command, "list", "--format", format_name)
    expected = ["Alpha", "Beta", "Zulu"] if command == "project" else ["New", "Old"]
    if format_name == "json":
        payload = json.loads(result.stdout)
        name_index = 1 if command == "project" else 0
        assert [row[name_index] for row in payload["rows"]] == expected
    elif format_name == "csv":
        assert [
            row["Name"] for row in csv.DictReader(io.StringIO(result.stdout))
        ] == expected
    else:
        for name in expected:
            assert name in result.stdout
    assert result.stderr == ""
    assert persistent_bytes(query_workspace) == before


@pytest.mark.parametrize("command", ["project", "milestone"])
def test_empty_json_list_retains_schema_and_zero_counts(workspace, cli_runner, command):
    before = persistent_bytes(workspace)
    payload = json.loads(run(cli_runner, command, "list", "--format", "json").stdout)
    assert payload["columns"]
    assert payload["rows"] == []
    assert payload["metadata"]["total"] == payload["metadata"]["returned"] == 0
    assert persistent_bytes(workspace) == before


@pytest.mark.parametrize("format_name", ["json", "csv"])
def test_export_preserves_quotes_unicode_and_newlines(
    workspace, cli_runner, format_name
):
    title = 'Café [review] "quoted", pipe |'
    content = "first line\nsecond line ☕"
    seed(
        workspace,
        Issue(
            EntityId("special"),
            NOW,
            NOW,
            title=Title(title),
            content=content,
            labels=("comma,label", "unicode-☕"),
        ),
    )
    before = persistent_bytes(workspace)
    result = run(cli_runner, "data", "export", "--format", format_name)
    row = (
        json.loads(result.stdout)["issues"][0]
        if format_name == "json"
        else next(csv.DictReader(io.StringIO(result.stdout)))
    )
    assert row["title"] == title
    if format_name == "json":
        assert row["content"].strip() == content
        assert row["labels"] == ["comma,label", "unicode-☕"]
    else:
        assert json.loads(row["labels"]) == ["comma,label", "unicode-☕"]
    assert persistent_bytes(workspace) == before


@pytest.mark.parametrize("filter_value", [None, "assignee=nobody"])
def test_empty_export_keeps_versioned_json_schema(workspace, cli_runner, filter_value):
    args = ["--filter", filter_value] if filter_value else []
    result = run(cli_runner, "data", "export", "--format", "json", *args)
    payload = json.loads(result.stdout)
    assert payload == {
        "schema_version": 1,
        "kind": "roadmap.issue-export",
        "issues": [],
    }


@pytest.mark.parametrize(
    "command,formats",
    [
        (["data", "export"], ["json", "csv", "markdown"]),
        (["status"], ["rich", "plain", "json", "csv", "markdown"]),
    ],
)
def test_file_destination_matches_stdout_and_refuses_overwrite(
    query_workspace, cli_runner, tmp_path, command, formats
):
    before = persistent_bytes(query_workspace)
    for format_name in formats:
        path = tmp_path / f"{command[0]}-{format_name}.out"
        output = run(
            cli_runner, *command, "--format", format_name, "--output", str(path)
        )
        assert output.stdout == "" and output.stderr
        stored = path.read_bytes()
        comparison = "plain" if format_name == "rich" else format_name
        direct = run(cli_runner, *command, "--format", comparison)
        assert stored == direct.stdout_bytes
        result = cli_runner.invoke(
            cli, [*command, "--format", format_name, "--output", str(path)]
        )
        assert result.exit_code == 1
        assert result.stdout == ""
        assert "overwrite" in result.stderr.lower()
        assert path.read_bytes() == stored
    assert persistent_bytes(query_workspace) == before


@pytest.mark.parametrize("command", [["data", "export"], ["status"]])
@pytest.mark.parametrize("destination", ["missing-parent", "directory"])
def test_invalid_report_destination_preserves_workspace(
    query_workspace, cli_runner, tmp_path, command, destination
):
    before = persistent_bytes(query_workspace)
    path = (
        tmp_path / "not-created" / "report.json"
        if destination == "missing-parent"
        else tmp_path
    )
    result = cli_runner.invoke(
        cli, [*command, "--format", "json", "--output", str(path)]
    )
    assert result.exit_code != 0
    assert result.stdout == ""
    assert persistent_bytes(query_workspace) == before
    assert not (tmp_path / "not-created").exists()


def test_status_counts_match_canonical_lifecycle(query_workspace, cli_runner):
    payload = json.loads(run(cli_runner, "status", "--format", "json").stdout)
    entity_rows = {row[0]: row[1:] for row in payload["tables"]["entities"]["rows"]}
    assert entity_rows == {
        "Projects": [3, 0, 0, 3],
        "Milestones": [2, 0, 0, 2],
        "Issues": [4, 1, 1, 6],
        "Total": [9, 1, 1, 11],
    }
    counts = dict(payload["tables"]["issue_status"]["rows"])
    assert counts == {
        "todo": 2,
        "in-progress": 1,
        "blocked": 1,
        "review": 0,
        "closed": 1,
        "archived": 1,
        "Total": 6,
    }


@pytest.mark.parametrize(
    "flags,expected",
    [
        ([], {"broken-issue", "broken-mile"}),
        (["--filter-entity", "issue"], {"broken-issue"}),
        (["--filter-entity", "milestone"], {"broken-mile"}),
        (
            ["--filter-entity", "issue", "--filter-entity", "milestone"],
            {"broken-issue", "broken-mile"},
        ),
        (["--filter-severity", "info"], set()),
        (
            ["--filter-severity", "error", "--filter-severity", "critical"],
            {"broken-issue", "broken-mile"},
        ),
        (["--no-dependencies"], set()),
    ],
)
@pytest.mark.parametrize("format_name", ["json", "csv"])
def test_health_filters_repeated_values_and_exit_status_are_exact(
    workspace, cli_runner, flags, expected, format_name
):
    seed(
        workspace,
        Issue(
            EntityId("broken-issue"),
            NOW,
            NOW,
            title=Title("Broken issue"),
            relations=IssueRelations(milestone_id=EntityId("missing-mile")),
        ),
        Milestone(
            EntityId("broken-mile"),
            NOW,
            NOW,
            name=Name("Broken mile"),
            relation=MilestoneRelation(EntityId("missing-project")),
        ),
    )
    before = persistent_bytes(workspace)
    result = run(
        cli_runner,
        "health",
        "scan",
        *flags,
        "--format",
        format_name,
        code=2 if expected else 0,
    )
    if format_name == "json":
        payload = json.loads(result.stdout)
        rows = payload["findings"]
        assert payload["exit_code"] == result.exit_code
        assert payload["summary"]["error"] == len(expected)
    else:
        rows = list(csv.DictReader(io.StringIO(result.stdout)))
    assert {row["entity_id"] for row in rows} == expected
    assert {row["finding_id"] for row in rows} <= {"canonical.broken-reference"}
    assert result.stderr == ""
    assert persistent_bytes(workspace) == before


@pytest.mark.parametrize(
    "flags,expected",
    [
        ([], {"Café alpha", "Delta"}),
        (["--only-open"], {"Café alpha"}),
        (["--status", "todo", "--status", "closed"], {"Café alpha", "Delta"}),
        (["--status", "todo", "--priority", "high"], {"Café alpha"}),
    ],
)
def test_milestone_view_repeated_filters_match_issue_selection(
    query_workspace, cli_runner, flags, expected
):
    before = persistent_bytes(query_workspace)
    result = run(cli_runner, "milestone", "view", "m-old", *flags)
    found = {
        title
        for title in ("Café alpha", "Beta", "Gamma", "Delta", "Archived", "Feature")
        if title in result.stdout
    }
    assert found == expected
    assert persistent_bytes(query_workspace) == before


@pytest.fixture
def path_workspace(workspace):
    seed(
        workspace,
        Milestone(EntityId("chain"), NOW, NOW, name=Name("chain")),
        Milestone(EntityId("other"), NOW, NOW, name=Name("other")),
        Issue(
            EntityId("a"),
            NOW,
            NOW,
            title=Title("First"),
            estimated_hours=2,
            relations=IssueRelations(
                milestone_id=EntityId("chain"), blocks=(EntityId("b"),)
            ),
        ),
        Issue(
            EntityId("b"),
            NOW,
            NOW,
            title=Title("Second"),
            estimated_hours=3,
            relations=IssueRelations(
                milestone_id=EntityId("chain"),
                depends_on=(EntityId("a"),),
                blocks=(EntityId("c"),),
            ),
        ),
        Issue(
            EntityId("c"),
            NOW,
            NOW,
            title=Title("Closed"),
            estimated_hours=10,
            status=IssueStatus.CLOSED,
            relations=IssueRelations(
                milestone_id=EntityId("chain"), depends_on=(EntityId("b"),)
            ),
        ),
        Issue(
            EntityId("z"),
            NOW,
            NOW,
            title=Title("Other"),
            estimated_hours=20,
            relations=IssueRelations(milestone_id=EntityId("other")),
        ),
    )
    return workspace


@pytest.mark.parametrize(
    "milestone,include_closed,expected,duration",
    [
        ("chain", False, ["a", "b"], 5),
        ("chain", True, ["a", "b", "c"], 15),
        ("other", False, ["z"], 20),
        (None, False, ["z"], 20),
    ],
)
def test_critical_path_scope_and_closed_inclusion_are_exact(
    path_workspace, cli_runner, milestone, include_closed, expected, duration
):
    before = persistent_bytes(path_workspace)
    flags = ["--milestone", milestone] if milestone else []
    if include_closed:
        flags.append("--include-closed")
    payload = json.loads(
        run(cli_runner, "analysis", "critical-path", *flags, "--export", "json").stdout
    )
    assert [n["issue_id"] for n in payload["critical_path"]] == expected
    assert payload["summary"]["total_duration"] == duration
    assert persistent_bytes(path_workspace) == before


@pytest.mark.parametrize("format_name", ["plain", "json", "csv"])
def test_critical_path_destination_refusal_preserves_existing_file(
    path_workspace, cli_runner, tmp_path, format_name
):
    before = persistent_bytes(path_workspace)
    path = tmp_path / "analysis.out"
    flags = ["--export", format_name] if format_name != "plain" else []
    result = run(
        cli_runner,
        "analysis",
        "critical-path",
        "--milestone",
        "chain",
        *flags,
        "--output",
        str(path),
    )
    assert result.stdout == "" and result.stderr
    stored = path.read_bytes()
    if format_name == "json":
        assert [n["issue_id"] for n in json.loads(stored)["critical_path"]] == [
            "a",
            "b",
        ]
    elif format_name == "csv":
        assert [
            row["issue_id"] for row in csv.DictReader(io.StringIO(stored.decode()))
        ] == ["a", "b"]
    else:
        assert b"First" in stored and b"Second" in stored
    result = cli_runner.invoke(
        cli,
        [
            "analysis",
            "critical-path",
            "--milestone",
            "chain",
            *flags,
            "--output",
            str(path),
        ],
    )
    assert result.exit_code == 1 and result.stdout == ""
    assert path.read_bytes() == stored
    assert persistent_bytes(path_workspace) == before


@pytest.mark.parametrize("level", ["user", "project", "merged"])
def test_config_view_levels_select_exact_scope_without_writes(
    query_workspace, cli_runner, level
):
    before = persistent_bytes(query_workspace)
    user = query_workspace.configuration.user_path.read_bytes()
    result = run(cli_runner, "config", "view", "--level", level)
    actual = yaml.safe_load(result.stdout)
    expected = (
        {
            "project": query_workspace.configuration.view("project"),
            "user": query_workspace.configuration.view("user"),
        }
        if level == "merged"
        else query_workspace.configuration.view(level)
    )
    assert actual == expected
    assert persistent_bytes(query_workspace) == before
    assert query_workspace.configuration.user_path.read_bytes() == user


@pytest.mark.parametrize(
    "command,flags",
    [
        (["project", "list"], ["--format", "json"]),
        (["milestone", "list"], ["--format", "csv"]),
        (["status"], ["--format", "json"]),
        (["config", "explain", "output.format"], ["--format", "json"]),
        (["data", "export"], ["--format", "json"]),
        (["health", "scan"], ["--output", "json"]),
    ],
)
def test_machine_output_is_stable_across_terminal_environment_flags(
    query_workspace, cli_runner, command, flags
):
    before = persistent_bytes(query_workspace)
    baseline = run(cli_runner, *command, *flags).stdout_bytes
    altered = run(
        cli_runner,
        *command,
        *flags,
        env={"NO_COLOR": "1", "COLUMNS": "40", "ROADMAP_OUTPUT": "plain"},
    ).stdout_bytes
    assert altered == baseline
    assert persistent_bytes(query_workspace) == before


def test_today_selects_current_identity_and_next_milestone_only(
    query_workspace, cli_runner
):
    before = persistent_bytes(query_workspace)
    result = run(cli_runner, "today")
    assert "Daily Summary - alice" in result.stdout
    assert "Upcoming Milestone: Old" in result.stdout
    assert "a: Café alpha" in result.stdout
    for other in ("b: Beta", "c: Gamma", "d: Delta", "e: Archived", "f: Feature"):
        assert other not in result.stdout
    assert persistent_bytes(query_workspace) == before


@pytest.mark.parametrize(
    "method,expected", [("count_based", "50.0%"), ("effort_weighted", "90.0%")]
)
def test_derived_progress_methods_have_distinguishable_results(
    workspace, cli_runner, method, expected
):
    seed(
        workspace,
        Milestone(EntityId("weighted"), NOW, NOW, name=Name("weighted")),
        Issue(
            EntityId("open"),
            NOW,
            NOW,
            title=Title("Open"),
            estimated_hours=1,
            relations=IssueRelations(milestone_id=EntityId("weighted")),
        ),
        Issue(
            EntityId("closed"),
            NOW,
            NOW,
            title=Title("Closed"),
            estimated_hours=9,
            status=IssueStatus.CLOSED,
            relations=IssueRelations(milestone_id=EntityId("weighted")),
        ),
    )
    before = persistent_bytes(workspace)
    result = run(cli_runner, "milestone", "recalculate", "weighted", "--method", method)
    assert f"weighted: {expected}" in result.stdout
    assert persistent_bytes(workspace) == before
