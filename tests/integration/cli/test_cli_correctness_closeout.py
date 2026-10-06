"""Regression journeys for the CLI correctness pass, using real storage."""

import csv
import io
import json
from dataclasses import replace

import pytest

from roadmap.adapters.outbound.persistence.canonical import CanonicalUnitOfWork
from roadmap.adapters.outbound.persistence.documents import DocumentRepository
from roadmap.bootstrap import cli
from roadmap.domain.types import (
    EntityId,
    IssueRelations,
    MilestoneRelation,
    Name,
)
from tests.fixtures.cli_workspace import run, seed
from tests.integration.cli.test_cli_mutation_contracts import (
    entity,
    load,
    persistent_bytes,
)
from tests.integration.cli.test_cli_query_output_contracts import (
    build_query_workspace,
)


@pytest.fixture
def query_workspace(workspace, cli_runner):
    return build_query_workspace(workspace, cli_runner)


@pytest.mark.parametrize("kind", ["issue", "milestone", "project"])
@pytest.mark.parametrize("action", ["archive", "restore"])
def test_preview_refuses_pending_recovery_without_any_persistent_write(
    workspace, cli_runner, kind, action
):
    target = entity(kind, "target", closed=True, archived=action == "restore")
    seed(workspace, target)
    repository = DocumentRepository(workspace.roadmap_dir)

    def crash(stage, _path):
        if stage == "after_journal":
            raise SystemExit("interrupted")

    with (
        pytest.raises(SystemExit),
        CanonicalUnitOfWork(repository, failure_injector=crash) as unit,
    ):
        changed = replace(target, content="Recovered payload")
        getattr(unit, f"save_{kind}")(changed)
        unit.commit()
    before = persistent_bytes(workspace)
    result = cli_runner.invoke(cli, [kind, action, "target", "--dry-run"])
    assert result.exit_code == 1
    assert "recovery is pending" in result.stderr
    assert persistent_bytes(workspace) == before
    assert load(workspace, kind, "target").content != "Recovered payload"
    # Actual mutation retains automatic crash recovery.
    with CanonicalUnitOfWork(repository):
        pass
    assert load(workspace, kind, "target").content == "Recovered payload"


@pytest.mark.parametrize(
    "kind,status", [("milestone", "closed"), ("project", "completed")]
)
def test_status_update_cannot_bypass_close_guard(workspace, cli_runner, kind, status):
    parent = entity(kind, "parent")
    child = (
        replace(entity("issue", "child"), relations=IssueRelations(parent.id))
        if kind == "milestone"
        else replace(
            entity("milestone", "child"), relation=MilestoneRelation(parent.id)
        )
    )
    seed(workspace, parent, child)
    before = persistent_bytes(workspace)
    result = cli_runner.invoke(cli, [kind, "update", "parent", "--status", status])
    assert result.exit_code == 1
    assert "open" in result.stderr
    assert persistent_bytes(workspace) == before
    run(
        cli_runner,
        kind,
        "close",
        "parent",
        "--force",
        *(["--yes"] if kind == "project" else []),
    )
    assert load(workspace, kind, "parent").status.value == status
    assert (
        load(workspace, "issue" if kind == "milestone" else "milestone", "child")
        == child
    )


@pytest.mark.parametrize("command", ["create", "start"])
@pytest.mark.parametrize(
    "flag",
    [["--branch-name", "ignored"], ["--checkout"], ["--no-checkout"], ["--force"]],
)
def test_branch_only_options_refuse_before_canonical_write(
    workspace, cli_runner, command, flag
):
    seed(workspace, entity("issue", "target"))
    before = persistent_bytes(workspace)
    args = [
        "issue",
        command,
        *(["--title", "new"] if command == "create" else ["target"]),
        *flag,
    ]
    result = cli_runner.invoke(cli, args)
    assert result.exit_code == 2
    assert "requires --git-branch" in result.stderr
    assert persistent_bytes(workspace) == before


@pytest.mark.parametrize(
    "flags", [[], ["--assignee", "alice"], ["--search", "no-match"]]
)
def test_issue_json_is_whole_stream_even_when_empty(query_workspace, cli_runner, flags):
    result = run(cli_runner, "issue", "list", *flags, "--format", "json")
    data = json.loads(result.stdout)
    assert data["rows"] or flags == ["--search", "no-match"]


@pytest.mark.parametrize("text", ["[red]Marked[/red]", "x" * 240, 'Café, "quoted"'])
@pytest.mark.parametrize("format_name", ["json", "csv"])
def test_machine_output_preserves_arbitrary_cell_text(
    workspace, cli_runner, text, format_name
):
    seed(workspace, replace(entity("project", "p"), name=Name(text)))
    result = run(
        cli_runner, "project", "list", "--format", format_name, "--columns", "name"
    )
    value = (
        json.loads(result.stdout)["rows"][0][0]
        if format_name == "json"
        else list(csv.reader(io.StringIO(result.stdout)))[1][0]
    )
    assert value == text


def test_mixed_direction_sort_preserves_primary_groups(query_workspace, cli_runner):
    result = run(
        cli_runner,
        "project",
        "list",
        "--format",
        "json",
        "--sort-by",
        "owner:asc,name:desc",
        "--columns",
        "name",
    )
    assert [row[0] for row in json.loads(result.stdout)["rows"]] == [
        "Zulu",
        "Beta",
        "Alpha",
    ]


@pytest.mark.parametrize("selector", [[], ["--search", "no-match"]])
@pytest.mark.parametrize(
    "options",
    [["--columns", "unknown"], ["--sort-by", "title:bad"], ["--filter", "title!=foo"]],
)
def test_invalid_output_options_fail_independent_of_result_count(
    query_workspace, cli_runner, selector, options
):
    before = persistent_bytes(query_workspace)
    result = cli_runner.invoke(
        cli, ["issue", "list", *selector, *options, "--format", "json"]
    )
    assert result.exit_code == 2
    assert not result.stdout
    assert persistent_bytes(query_workspace) == before


@pytest.mark.parametrize(
    "value", ["status=invalid", "priority=invalid", "issue_type=invalid"]
)
def test_export_rejects_invalid_enum_filters(workspace, cli_runner, value):
    before = persistent_bytes(workspace)
    result = cli_runner.invoke(
        cli, ["data", "export", "--filter", value, "--format", "json"]
    )
    assert result.exit_code == 1
    assert "Invalid" in result.stderr
    assert persistent_bytes(workspace) == before


@pytest.mark.parametrize("kind", ["issue", "project", "milestone"])
def test_empty_csv_retains_headers(workspace, cli_runner, kind):
    result = run(cli_runner, kind, "list", "--format", "csv")
    rows = list(csv.reader(io.StringIO(result.stdout)))
    assert len(rows) == 1 and rows[0]
    assert rows[0][0] == ("Name" if kind == "milestone" else "ID")


@pytest.mark.parametrize("format_name", ["plain", "json", "csv"])
def test_empty_critical_path_honors_destination_and_overwrite_guard(
    workspace, cli_runner, tmp_path, format_name
):
    path = tmp_path / "report"
    run(
        cli_runner,
        "analysis",
        "critical-path",
        "--format",
        format_name,
        "--output",
        str(path),
    )
    original = path.read_bytes()
    assert original
    if format_name == "json":
        assert json.loads(original)["critical_path"] == []
    result = cli_runner.invoke(
        cli,
        ["analysis", "critical-path", "--format", format_name, "--output", str(path)],
    )
    assert result.exit_code == 1
    assert path.read_bytes() == original


def test_issue_clear_labels_and_due_date_update_preserves_other_fields(
    workspace, cli_runner
):
    seed(workspace, entity("milestone", "m"))
    result = run(
        cli_runner,
        "issue",
        "create",
        "--title",
        "target",
        "--assignee",
        "alice",
        "--milestone",
        "m",
        "--estimate",
        "4",
        "--labels",
        "keep",
        "--labels",
        "remove",
        "--due-date",
        "2100-01-01",
        "--print-id",
    )
    identity = result.stdout.strip()
    created = load(workspace, "issue", identity)
    assert created.due_at is not None
    run(
        cli_runner,
        "issue",
        "update",
        identity,
        "--clear-assignee",
        "--clear-milestone",
        "--clear-estimate",
        "--clear-due-date",
        "--add-label",
        "new",
        "--add-label",
        "new",
        "--remove-label",
        "remove",
    )
    changed = load(workspace, "issue", identity)
    assert (
        changed.assignee,
        changed.relations.milestone_id,
        changed.estimated_hours,
        changed.due_at,
    ) == (None, None, None, None)
    assert changed.labels == ("keep", "new")
    assert changed.title == created.title and changed.status == created.status
    run(cli_runner, "issue", "update", identity, "--due-date", "2101-02-03")
    assert (
        load(workspace, "issue", identity).due_at.value.date().isoformat()
        == "2101-02-03"
    )
    inspected = json.loads(
        run(cli_runner, "issue", "view", identity, "--format", "json").stdout
    )
    assert inspected["schema_version"] == 1
    assert inspected["record"]["issue"]["history"][-1]["action"] == "updated"


@pytest.mark.parametrize(
    "flags",
    [
        ["--assignee", "alice", "--clear-assignee"],
        ["--milestone", "m", "--clear-milestone"],
        ["--estimate", "2", "--clear-estimate"],
        ["--due-date", "2100-01-01", "--clear-due-date"],
        ["--add-label", "same", "--remove-label", "same"],
        ["--add-label", ""],
        ["--due-date", "invalid"],
    ],
)
def test_issue_update_conflicts_and_invalid_values_preserve_all_bytes(
    workspace, cli_runner, flags
):
    seed(workspace, entity("issue", "target"), entity("milestone", "m"))
    before = persistent_bytes(workspace)
    result = cli_runner.invoke(cli, ["issue", "update", "target", *flags])
    assert result.exit_code != 0
    assert persistent_bytes(workspace) == before


def test_project_and_milestone_new_fields_print_ids_and_inspection(
    workspace, cli_runner
):
    project_id = run(
        cli_runner,
        "project",
        "create",
        "--title",
        "Project",
        "--owner",
        "alice",
        "--priority",
        "high",
        "--print-id",
    ).stdout.strip()
    assert load(workspace, "project", project_id).owner == "alice"
    run(
        cli_runner,
        "project",
        "update",
        project_id,
        "--owner",
        "bob",
        "--priority",
        "low",
    )
    assert load(workspace, "project", project_id).owner == "bob"
    run(cli_runner, "project", "update", project_id, "--clear-owner")
    assert load(workspace, "project", project_id).owner is None
    milestone_id = run(
        cli_runner,
        "milestone",
        "create",
        "--title",
        "Milestone",
        "--due-date",
        "2100-01-01",
        "--print-id",
    ).stdout.strip()
    assert load(workspace, "milestone", milestone_id).relation.project_id == EntityId(
        project_id
    )
    run(
        cli_runner,
        "milestone",
        "update",
        milestone_id,
        "--clear-project",
        "--clear-due-date",
    )
    assert load(workspace, "milestone", milestone_id).relation.project_id is None
    assert load(workspace, "milestone", milestone_id).due_at is None
    assert load(workspace, "project", project_id).relations.milestone_ids == ()
    for kind, identity in [("project", project_id), ("milestone", milestone_id)]:
        data = json.loads(
            run(cli_runner, kind, "view", identity, "--format", "json").stdout
        )
        assert data["kind"] == f"roadmap.{kind}" and data["schema_version"] == 1


@pytest.mark.parametrize(
    "kind,flags",
    [
        ("project", ["--owner", "alice", "--clear-owner"]),
        ("milestone", ["--project", "p", "--clear-project"]),
        ("milestone", ["--due-date", "2100-01-01", "--clear-due-date"]),
    ],
)
def test_planning_clear_conflicts_refuse_without_writes(
    workspace, cli_runner, kind, flags
):
    seed(workspace, entity("project", "p"), entity("milestone", "m"))
    before = persistent_bytes(workspace)
    result = cli_runner.invoke(
        cli, [kind, "update", "p" if kind == "project" else "m", *flags]
    )
    assert result.exit_code == 1
    assert persistent_bytes(workspace) == before


def test_explicit_workspace_wins_and_invalid_selection_never_falls_back(
    workspace, cli_runner, tmp_path
):
    other = tmp_path / "other" / "planning"
    run(cli_runner, "--workspace", str(other), "init", "--skip-project")
    selected_id = run(
        cli_runner,
        "--workspace",
        str(other),
        "project",
        "create",
        "--title",
        "Other",
        "--print-id",
    ).stdout.strip()
    assert (
        json.loads(
            run(
                cli_runner,
                "--workspace",
                str(other),
                "project",
                "view",
                selected_id,
                "--format",
                "json",
            ).stdout
        )["record"]["project"]["name"]
        == "Other"
    )
    assert (
        json.loads(run(cli_runner, "project", "list", "--format", "json").stdout)[
            "rows"
        ]
        == []
    )
    before = persistent_bytes(workspace)
    missing = tmp_path / "missing"
    result = cli_runner.invoke(cli, ["--workspace", str(missing), "project", "list"])
    assert result.exit_code == 1
    assert not missing.exists()
    assert persistent_bytes(workspace) == before
    for flag in ["--help", "--version"]:
        assert (
            cli_runner.invoke(cli, ["--workspace", str(missing), flag]).exit_code == 0
        )
    result = cli_runner.invoke(
        cli, ["--workspace", str(other), "init", "--name", "conflict", "--skip-project"]
    )
    assert result.exit_code == 2
    assert "conflicts" in result.stderr
    assert not (tmp_path / "conflict").exists()
    assert "planning/db/*.db" in (other.parent / ".gitignore").read_text()


def test_explicit_workspace_preview_creates_nothing(workspace, cli_runner, tmp_path):
    destination = tmp_path / "uncreated" / "planning"
    run(
        cli_runner,
        "--workspace",
        str(destination),
        "init",
        "--skip-project",
        "--dry-run",
    )
    assert not destination.parent.exists()


@pytest.mark.parametrize("kind", ["issue", "project", "milestone"])
@pytest.mark.parametrize("action", ["archive", "restore"])
def test_verbose_preview_is_stderr_only_and_preserves_bytes(
    workspace, cli_runner, kind, action
):
    seed(workspace, entity(kind, "target", closed=True, archived=action == "restore"))
    before = persistent_bytes(workspace)
    normal = run(cli_runner, kind, action, "target", "--dry-run")
    verbose = run(
        cli_runner, "--debug", kind, action, "target", "--dry-run", "--verbose"
    )
    assert verbose.stdout == normal.stdout
    assert "Validated 1" in verbose.stderr and "preview only" in verbose.stderr
    assert "Traceback" not in verbose.stderr
    assert persistent_bytes(workspace) == before


@pytest.mark.parametrize("kind", ["issue", "project", "milestone"])
def test_yes_is_consent_and_does_not_override_archive_lifecycle(
    workspace, cli_runner, kind
):
    seed(workspace, entity(kind, "target"), entity(kind, "peer"))
    before = persistent_bytes(workspace)
    refused = cli_runner.invoke(cli, [kind, "archive", "target", "--yes"])
    assert refused.exit_code == 1
    assert persistent_bytes(workspace) == before
    run(cli_runner, kind, "archive", "target", "--force", "--yes")
    assert load(workspace, kind, "target").retention.value == "archived"
    assert load(workspace, kind, "peer").retention.value == "visible"
    run(cli_runner, kind, "restore", "target", "--yes")
    assert load(workspace, kind, "target").retention.value == "visible"


def test_project_close_yes_does_not_override_open_children(workspace, cli_runner):
    parent = entity("project", "p")
    seed(
        workspace,
        parent,
        replace(entity("milestone", "m"), relation=MilestoneRelation(parent.id)),
    )
    before = persistent_bytes(workspace)
    result = cli_runner.invoke(cli, ["project", "close", "p", "--yes"])
    assert result.exit_code == 1 and "open milestone" in result.stderr
    assert persistent_bytes(workspace) == before


@pytest.mark.parametrize("format_name", ["plain", "json", "csv"])
def test_health_format_destination_and_legacy_boundary(
    workspace, cli_runner, tmp_path, format_name
):
    seed(workspace, entity("issue", "target"))
    path = tmp_path / "health-report"
    direct = run(cli_runner, "health", "scan", "--format", format_name)
    saved = run(
        cli_runner, "health", "scan", "--format", format_name, "--output", str(path)
    )
    assert not saved.stdout and path.read_bytes() == direct.stdout_bytes
    legacy = run(cli_runner, "health", "scan", "--output", format_name)
    assert legacy.stdout == direct.stdout and "Deprecated" in legacy.stderr
    result = cli_runner.invoke(
        cli, ["health", "scan", "--format", format_name, "--output", str(path)]
    )
    assert result.exit_code == 1 and path.read_bytes() == direct.stdout_bytes


@pytest.mark.parametrize(
    "flags",
    [
        [],
        ["--fix-type", "all"],
        ["--fix-type", "data_integrity"],
        ["--fix-type", "orphaned_issues"],
    ],
)
def test_health_repair_requires_explicit_bounded_target(workspace, cli_runner, flags):
    before = persistent_bytes(workspace)
    result = cli_runner.invoke(cli, ["health", "fix", *flags, "--yes"])
    assert result.exit_code == 2
    assert persistent_bytes(workspace) == before


@pytest.mark.parametrize(
    "command",
    [
        ["cleanup", "--dry-run"],
        ["migrate", "--dry-run", "--format", "json"],
        ["health", "fix", "--fix-type", "projection", "--dry-run", "--format", "json"],
    ],
)
def test_other_verbose_operations_preserve_stdout_and_preview_bytes(
    workspace, cli_runner, command
):
    seed(workspace, entity("issue", "target"))
    before = persistent_bytes(workspace)
    ordinary = run(cli_runner, *command)
    verbose = run(cli_runner, *command, "--verbose")
    assert ordinary.stdout == verbose.stdout
    assert verbose.stderr and "Traceback" not in verbose.stderr
    assert persistent_bytes(workspace) == before


@pytest.mark.parametrize(
    "command",
    [
        ["issue", "list", "--format", "json", "--verbose"],
        ["init", "--skip-project", "--non-interactive", "--dry-run"],
        ["cleanup", "--backups-only", "--dry-run"],
        ["health", "scan", "--details", "--format", "json"],
    ],
)
def test_compatibility_options_warn_on_stderr_without_writes(
    workspace, cli_runner, command
):
    seed(workspace, entity("issue", "target"))
    before = persistent_bytes(workspace)
    result = run(cli_runner, *command)
    assert "Deprecated" in result.stderr
    if "json" in command:
        json.loads(result.stdout)
    assert persistent_bytes(workspace) == before


def test_analysis_alias_conflicts_are_rejected(workspace, cli_runner):
    before = persistent_bytes(workspace)
    result = cli_runner.invoke(
        cli, ["analysis", "critical-path", "--format", "json", "--export", "csv"]
    )
    assert result.exit_code == 2
    assert persistent_bytes(workspace) == before


@pytest.mark.parametrize("format_name", ["plain", "json", "csv"])
def test_summary_only_keeps_counts_exit_status_and_omits_details(
    query_workspace, cli_runner, format_name
):
    seed(
        query_workspace,
        replace(entity("issue", "bad"), relations=IssueRelations(EntityId("missing"))),
    )
    before = persistent_bytes(query_workspace)
    result = run(
        cli_runner, "health", "scan", "--format", format_name, "--summary-only", code=2
    )
    if format_name == "json":
        payload = json.loads(result.stdout)
        assert payload["findings"] == [] and payload["summary"]["error"] == 1
    elif format_name == "csv":
        assert len(list(csv.reader(io.StringIO(result.stdout)))) == 1
    else:
        assert (
            "error=1" in result.stdout
            and "canonical.broken-reference" not in result.stdout
        )
    assert persistent_bytes(query_workspace) == before


def test_plain_issue_inspection_preserves_literal_content_and_history(
    workspace, cli_runner
):
    result = run(
        cli_runner,
        "issue",
        "create",
        "--title",
        "[red]Literal[/red]",
        "--content",
        "x" * 240 + "\n[bold]second[/bold]",
        "--print-id",
    )
    identity = result.stdout.strip()
    output = run(cli_runner, "issue", "view", identity, "--format", "plain").stdout
    assert "[red]Literal[/red]" in output and "x" * 240 in output
    assert "[bold]second[/bold]" in output and "created" in output
    assert "\x1b[" not in output


def test_config_scope_conflict_is_not_silently_overridden(workspace, cli_runner):
    before = persistent_bytes(workspace)
    result = cli_runner.invoke(cli, ["config", "view", "--project", "--level", "user"])
    assert result.exit_code == 2 and "conflicts" in result.stderr
    assert persistent_bytes(workspace) == before


@pytest.mark.parametrize("kind", ["file", "unsupported", "denied"])
def test_explicit_workspace_invalid_or_unreadable_paths_fail_loudly(
    workspace, cli_runner, tmp_path, monkeypatch, kind
):
    from pathlib import Path

    path = tmp_path / "invalid"
    if kind == "file":
        path.write_text("not a workspace")
    else:
        path.mkdir()
        (path / "config.yaml").write_text("schema_version: 999\n")
    if kind == "denied":
        original = Path.stat

        def denied(value, *args, **kwargs):
            if value == path:
                raise PermissionError("denied explicitly selected workspace")
            return original(value, *args, **kwargs)

        monkeypatch.setattr(Path, "stat", denied)
    before = persistent_bytes(workspace)
    result = cli_runner.invoke(cli, ["--workspace", str(path), "project", "list"])
    assert result.exit_code == 1 and result.stderr
    assert persistent_bytes(workspace) == before


@pytest.mark.parametrize(
    "method,percent", [("count_based", "50.0%"), ("effort_weighted", "90.0%")]
)
def test_preferred_progress_command_matches_legacy_without_mutation(
    workspace, cli_runner, method, percent
):
    mile = entity("milestone", "weighted")
    seed(
        workspace,
        mile,
        replace(
            entity("issue", "open"),
            estimated_hours=1,
            relations=IssueRelations(mile.id),
        ),
        replace(
            entity("issue", "closed", closed=True),
            estimated_hours=9,
            relations=IssueRelations(mile.id),
        ),
    )
    before = persistent_bytes(workspace)
    preferred = run(cli_runner, "milestone", "progress", "weighted", "--method", method)
    legacy = run(cli_runner, "milestone", "recalculate", "weighted", "--method", method)
    assert preferred.stdout == legacy.stdout and percent in preferred.stdout
    assert not preferred.stderr and "Deprecated" in legacy.stderr
    assert persistent_bytes(workspace) == before


@pytest.mark.parametrize("debug", [False, True])
def test_unexpected_command_error_reaches_debug_handler(
    workspace, cli_runner, monkeypatch, debug
):
    from roadmap.application.use_cases.planning import Planning

    def failed(_self):
        raise RuntimeError("[red]unexpected snapshot failure[/red]")

    monkeypatch.setattr(Planning, "all_projects", failed)
    before = persistent_bytes(workspace)
    result = cli_runner.invoke(
        cli, [*(["--debug"] if debug else []), "status", "--format", "json"]
    )
    assert result.exit_code == 1 and not result.stdout
    assert "[red]unexpected snapshot failure[/red]" in result.stderr
    assert ("Traceback" in result.stderr) == debug
    assert persistent_bytes(workspace) == before


def test_init_preview_rejects_unsupported_schema_without_writes(workspace, cli_runner):
    (workspace.roadmap_dir / "config.yaml").write_text("schema_version: 999\n")
    before = persistent_bytes(workspace)
    result = cli_runner.invoke(cli, ["init", "--dry-run", "--force", "--skip-project"])
    assert result.exit_code == 1 and "unsupported" in result.stderr
    assert persistent_bytes(workspace) == before


@pytest.mark.parametrize(
    "command",
    [
        ["status", "--verbose", "--format", "json"],
        ["project", "list", "--verbose", "--format", "json"],
        ["today", "--verbose"],
        ["health", "--verbose", "--format", "json"],
        ["health", "check", "--verbose", "--details", "--format", "json"],
        ["health", "scan", "--verbose", "--group-by", "severity", "--format", "json"],
        [
            "health",
            "db-integrity",
            "--verbose",
            "--details",
            "--show-ids",
            "--limit",
            "1",
            "--json",
        ],
        ["health", "fix", "--fix-type", "projection", "--details", "--dry-run"],
        [
            "init",
            "--interactive",
            "--yes",
            "--template",
            "example",
            "--template-path",
            "missing",
            "--force",
            "--skip-project",
            "--dry-run",
        ],
        ["cleanup", "--check-folders"],
        ["cleanup", "--check-duplicates"],
        ["cleanup", "--check-malformed"],
        ["cleanup", "--force", "--dry-run"],
        ["milestone", "kanban", "m", "--compact", "--no-color"],
    ],
)
def test_remaining_deprecated_flags_warn_without_mutation(
    workspace, cli_runner, command
):
    seed(workspace, entity("milestone", "m"), entity("issue", "i"))
    run(cli_runner, "config", "set", "identity.name", "alice")
    before = persistent_bytes(workspace)
    result = run(cli_runner, *command)
    assert "Deprecated" in result.stderr
    assert persistent_bytes(workspace) == before
    if "json" in command or "--json" in command:
        json.loads(result.stdout)


@pytest.mark.parametrize("kind", ["issue", "milestone", "project"])
@pytest.mark.parametrize("flags", [["target"], ["--all-closed"], ["--dry-run"]])
def test_archive_list_refuses_ignored_selector_or_mutation_flags(
    workspace, cli_runner, kind, flags
):
    seed(workspace, entity(kind, "target", closed=True))
    before = persistent_bytes(workspace)
    result = cli_runner.invoke(cli, [kind, "archive", "--list", *flags])
    assert result.exit_code == 2 and "cannot be combined" in result.stderr
    assert persistent_bytes(workspace) == before


@pytest.mark.parametrize("flags", [["--format", "json"], ["--verbose"], ["--details"]])
def test_health_group_options_do_not_silently_disappear_before_subcommands(
    workspace, cli_runner, flags
):
    seed(workspace, entity("issue", "target"))
    before = persistent_bytes(workspace)
    result = cli_runner.invoke(cli, ["health", *flags, "scan"])
    assert result.exit_code == 2 and "after the subcommand" in result.stderr
    assert persistent_bytes(workspace) == before
