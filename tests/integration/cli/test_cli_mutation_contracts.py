"""CLI mutations prove selection and data safety against real storage."""

from datetime import UTC, datetime

import pytest

from roadmap.adapters.outbound.persistence.documents import DocumentRepository
from roadmap.bootstrap import cli
from roadmap.domain.aggregates import Issue, Milestone, Project
from roadmap.domain.types import (
    EntityId,
    IssueRelations,
    IssueStatus,
    MilestoneRelation,
    MilestoneStatus,
    Name,
    ProjectStatus,
    RetentionState,
    Title,
)
from tests.fixtures.cli_workspace import NOW, canonical_bytes, run, seed


def persistent_bytes(core):
    """Include cache, config, backups and journals; lock-owner metadata is ephemeral."""
    return {
        p.relative_to(core.roadmap_dir).as_posix(): p.read_bytes()
        for p in core.roadmap_dir.rglob("*")
        if p.is_file() and p.name != "canonical-write.lock"
    }


def entity(kind, identity, *, closed=False, archived=False):
    retention = RetentionState.ARCHIVED if archived else RetentionState.VISIBLE
    if kind == "issue":
        return Issue(
            EntityId(identity),
            NOW,
            NOW,
            title=Title(identity),
            status=IssueStatus.CLOSED if closed else IssueStatus.TODO,
            retention=retention,
        )
    if kind == "milestone":
        return Milestone(
            EntityId(identity),
            NOW,
            NOW,
            name=Name(identity),
            status=MilestoneStatus.CLOSED if closed else MilestoneStatus.OPEN,
            retention=retention,
        )
    return Project(
        EntityId(identity),
        NOW,
        NOW,
        name=Name(identity),
        status=ProjectStatus.COMPLETED if closed else ProjectStatus.ACTIVE,
        retention=retention,
    )


def load(core, kind, identity):
    envelope = DocumentRepository(core.roadmap_dir).load(kind, EntityId(identity))
    return None if envelope is None else envelope.aggregate


@pytest.mark.parametrize("kind", ["issue", "milestone", "project"])
@pytest.mark.parametrize("action", ["archive", "restore"])
@pytest.mark.parametrize("selection", ["one", "batch"])
@pytest.mark.parametrize("mode", ["preview", "decline", "apply"])
def test_retention_selection_confirmation_and_preview(
    workspace, cli_runner, kind, action, selection, mode
):
    restoring = action == "restore"
    target = entity(kind, "target", closed=True, archived=restoring)
    peer = entity(kind, "peer", closed=True, archived=restoring)
    survivor = entity(kind, "survivor")
    seed(workspace, target, peer, survivor)
    before = persistent_bytes(workspace)
    args = (
        [kind, action, "target"]
        if selection == "one"
        else [kind, action, "--all" if restoring else "--all-closed"]
    )
    if mode == "preview":
        args.append("--dry-run")
    run(
        cli_runner,
        *args,
        input="n\n" if mode == "decline" else "y\n",
        code=1 if mode == "decline" else 0,
    )
    if mode != "apply":
        assert persistent_bytes(workspace) == before
        return
    expected = RetentionState.VISIBLE if restoring else RetentionState.ARCHIVED
    assert load(workspace, kind, "target").retention is expected
    assert load(workspace, kind, "peer").retention is (
        expected if selection == "batch" else peer.retention
    )
    assert load(workspace, kind, "survivor") == survivor
    after = canonical_bytes(workspace)
    changed = {
        p.stem
        for p, content in after.items()
        if before[p.relative_to(workspace.roadmap_dir).as_posix()] != content
    }
    assert changed == ({"target", "peer"} if selection == "batch" else {"target"})


@pytest.mark.parametrize("kind", ["issue", "milestone", "project"])
@pytest.mark.parametrize("action", ["archive", "restore"])
@pytest.mark.parametrize("selection", ["absent", "conflicting", "missing"])
def test_bad_retention_selectors_never_write(
    workspace, cli_runner, kind, action, selection
):
    seed(workspace, entity(kind, "target", closed=True, archived=action == "restore"))
    before = persistent_bytes(workspace)
    args = [kind, action]
    if selection == "conflicting":
        args += ["target", "--all" if action == "restore" else "--all-closed"]
    elif selection == "missing":
        args += ["absent-id"]
    run(cli_runner, *args, "--dry-run", code=1 if selection == "missing" else 2)
    assert persistent_bytes(workspace) == before


@pytest.mark.parametrize("kind", ["issue", "milestone", "project"])
@pytest.mark.parametrize("mode", ["decline", "yes", "guard"])
def test_delete_consent_does_not_bypass_archive_guard(
    workspace, cli_runner, kind, mode
):
    target = entity(kind, "target", archived=mode != "guard")
    survivor = entity(kind, "survivor")
    seed(workspace, target, survivor)
    before = persistent_bytes(workspace)
    run(
        cli_runner,
        kind,
        "delete",
        "target",
        *([] if mode == "decline" else ["--yes"]),
        input="n\n",
        code=0 if mode == "yes" else 1,
    )
    assert load(workspace, kind, "survivor") == survivor
    if mode == "yes":
        assert load(workspace, kind, "target") is None
        assert set(canonical_bytes(workspace)) == {
            workspace.roadmap_dir / f"{kind}s/survivor.md"
        }
    else:
        assert persistent_bytes(workspace) == before


@pytest.mark.parametrize("kind", ["project", "milestone"])
@pytest.mark.parametrize("force", [False, True])
def test_close_override_is_bounded_to_selected_parent(
    workspace, cli_runner, kind, force
):
    parent = entity(kind, "target")
    child = (
        Milestone(
            EntityId("child"),
            NOW,
            NOW,
            name=Name("child"),
            relation=MilestoneRelation(parent.id),
        )
        if kind == "project"
        else Issue(
            EntityId("child"),
            NOW,
            NOW,
            title=Title("child"),
            relations=IssueRelations(milestone_id=parent.id),
        )
    )
    seed(workspace, parent, child)
    before = persistent_bytes(workspace)
    run(
        cli_runner,
        kind,
        "close",
        "target",
        *(["--force"] if force else []),
        input="y\n",
        code=0 if force else 1,
    )
    if not force:
        assert persistent_bytes(workspace) == before
    else:
        assert load(workspace, kind, "target").status.value in {"closed", "completed"}
        child_kind = "milestone" if kind == "project" else "issue"
        assert load(workspace, child_kind, "child") == child
        child_path = f"{child_kind}s/child.md"
        assert persistent_bytes(workspace)[child_path] == before[child_path]


@pytest.mark.parametrize("action", ["start", "close"])
@pytest.mark.parametrize("date", ["2026-10-06", "2026-10-06 12:30", "invalid-date"])
def test_issue_dates_persist_exact_utc_or_refuse_without_writes(
    workspace, cli_runner, action, date
):
    seed(workspace, entity("issue", "target"), entity("issue", "survivor"))
    before = persistent_bytes(workspace)
    args = ["issue", action, "target", "--date", date]
    if action == "close":
        args += ["--record-time", "--reason", "finished"]
    run(cli_runner, *args, code=1 if date == "invalid-date" else 0)
    if date == "invalid-date":
        assert persistent_bytes(workspace) == before
    else:
        issue = load(workspace, "issue", "target")
        actual = issue.actual_start_at if action == "start" else issue.actual_end_at
        assert actual.value == datetime.fromisoformat(date).replace(tzinfo=UTC)
        assert (
            persistent_bytes(workspace)["issues/survivor.md"]
            == before["issues/survivor.md"]
        )


def test_close_date_requires_time_recording_before_mutation(workspace, cli_runner):
    seed(workspace, entity("issue", "target"))
    before = persistent_bytes(workspace)
    run(cli_runner, "issue", "close", "target", "--date", "2026-10-05", code=2)
    assert persistent_bytes(workspace) == before


@pytest.mark.parametrize(
    "option,value,attribute,expected",
    [
        ("--title", "Renamed", "title", "Renamed"),
        ("--priority", "high", "priority", "high"),
        ("--status", "in-progress", "status", "in-progress"),
        ("--assignee", "alice", "assignee", "alice"),
        ("--description", "Updated body", "content", "Updated body"),
        ("--estimate", "1.5", "estimated_hours", 1.5),
    ],
)
def test_issue_field_options_persist_without_touching_other_entities(
    workspace, cli_runner, option, value, attribute, expected
):
    seed(workspace, entity("issue", "target"), entity("issue", "survivor"))
    before = persistent_bytes(workspace)
    run(cli_runner, "issue", "update", "target", option, value)
    actual = getattr(load(workspace, "issue", "target"), attribute)
    assert getattr(actual, "value", actual) == expected
    assert (
        persistent_bytes(workspace)["issues/survivor.md"]
        == before["issues/survivor.md"]
    )


@pytest.mark.parametrize(
    "arguments",
    [
        [],
        ["--estimate", "-1"],
        ["--estimate", "0"],
        ["--status", "unknown"],
        ["--milestone", "missing"],
        ["--title", ""],
    ],
)
def test_invalid_issue_update_preserves_all_persistent_state(
    workspace, cli_runner, arguments
):
    seed(workspace, entity("issue", "target"))
    before = persistent_bytes(workspace)
    result = cli_runner.invoke(cli, ["issue", "update", "target", *arguments])
    assert result.exit_code != 0
    assert persistent_bytes(workspace) == before


def test_issue_milestone_reassignment_changes_only_selected_relationship(
    workspace, cli_runner
):
    old, new = entity("milestone", "old"), entity("milestone", "new")
    issue = Issue(
        EntityId("target"),
        NOW,
        NOW,
        title=Title("target"),
        relations=IssueRelations(milestone_id=old.id),
    )
    seed(workspace, old, new, issue, entity("issue", "survivor"))
    before = persistent_bytes(workspace)
    run(cli_runner, "issue", "update", "target", "--milestone", "new")
    assert load(workspace, "issue", "target").relations.milestone_id == new.id
    assert workspace.planning.milestone("old").issue_count == 0
    assert workspace.planning.milestone("new").issue_count == 1
    for path in ("milestones/old.md", "milestones/new.md", "issues/survivor.md"):
        assert persistent_bytes(workspace)[path] == before[path]


def test_issue_creation_flags_and_reciprocal_dependencies(workspace, cli_runner):
    seed(
        workspace,
        entity("milestone", "milestone"),
        entity("issue", "prerequisite"),
        entity("issue", "dependent"),
        entity("issue", "survivor"),
    )
    before = persistent_bytes(workspace)
    result = run(
        cli_runner,
        "issue",
        "create",
        "--print-id",
        "--title",
        "Created",
        "--type",
        "bug",
        "--priority",
        "high",
        "--assignee",
        "alice",
        "--milestone",
        "milestone",
        "--labels",
        "first",
        "--labels",
        "second",
        "--estimate",
        "2.5",
        "--content",
        "Body",
        "--depends-on",
        "prerequisite",
        "--blocks",
        "dependent",
    )
    identity = result.stdout.strip()
    issue = load(workspace, "issue", identity)
    assert str(issue.title) == "Created"
    assert (issue.issue_type.value, issue.priority.value, issue.assignee) == (
        "bug",
        "high",
        "alice",
    )
    assert set(issue.labels) == {"first", "second"}
    assert issue.estimated_hours == 2.5 and issue.content.strip() == "Body"
    assert issue.relations.milestone_id == EntityId("milestone")
    assert issue.relations.depends_on == (EntityId("prerequisite"),)
    assert issue.relations.blocks == (EntityId("dependent"),)
    assert (
        EntityId(identity) in load(workspace, "issue", "prerequisite").relations.blocks
    )
    assert (
        EntityId(identity) in load(workspace, "issue", "dependent").relations.depends_on
    )
    assert (
        persistent_bytes(workspace)["issues/survivor.md"]
        == before["issues/survivor.md"]
    )


@pytest.mark.parametrize(
    "arguments",
    [
        ["--depends-on", "missing"],
        ["--blocks", "missing"],
        ["--depends-on", "peer", "--blocks", "peer"],
        ["--milestone", "missing"],
        ["--estimate", "-1"],
    ],
)
def test_invalid_creation_never_leaves_entity_or_partial_reciprocal_link(
    workspace, cli_runner, arguments
):
    seed(workspace, entity("issue", "peer"))
    before = persistent_bytes(workspace)
    result = cli_runner.invoke(
        cli, ["issue", "create", "--title", "Rejected", *arguments]
    )
    assert result.exit_code != 0
    assert persistent_bytes(workspace) == before


@pytest.mark.parametrize("force", [False, True])
@pytest.mark.parametrize("kind", ["issue", "milestone", "project"])
def test_legacy_archive_force_overrides_lifecycle_guard_but_does_not_cascade(
    workspace, cli_runner, kind, force
):
    seed(workspace, entity(kind, "target"), entity(kind, "survivor"))
    before = persistent_bytes(workspace)
    run(
        cli_runner,
        kind,
        "archive",
        "target",
        *(["--force"] if force else []),
        input="y\n",
        code=0 if force else 1,
    )
    if force:
        assert load(workspace, kind, "target").retention is RetentionState.ARCHIVED
        assert (
            persistent_bytes(workspace)[f"{kind}s/survivor.md"]
            == before[f"{kind}s/survivor.md"]
        )
    else:
        assert persistent_bytes(workspace) == before


@pytest.mark.parametrize("status", ["todo", "in-progress", "closed"])
@pytest.mark.parametrize("preview", [False, True])
def test_restore_status_flag_selects_real_transition_without_touching_peer(
    workspace, cli_runner, status, preview
):
    seed(
        workspace,
        entity("issue", "target", closed=True, archived=True),
        entity("issue", "survivor", archived=True),
    )
    before = persistent_bytes(workspace)
    run(
        cli_runner,
        "issue",
        "restore",
        "target",
        "--status",
        status,
        *(["--dry-run"] if preview else ["--force"]),
    )
    if preview:
        assert persistent_bytes(workspace) == before
    else:
        issue = load(workspace, "issue", "target")
        assert issue.status.value == status
        assert issue.retention is RetentionState.VISIBLE
        assert (
            persistent_bytes(workspace)["issues/survivor.md"]
            == before["issues/survivor.md"]
        )


def test_project_update_fields_persist_only_on_target(workspace, cli_runner):
    seed(workspace, entity("project", "target"), entity("project", "survivor"))
    before = persistent_bytes(workspace)
    run(
        cli_runner,
        "project",
        "update",
        "target",
        "--name",
        "Renamed",
        "--description",
        "Updated",
        "--repository",
        "https://example.invalid/repo",
        "--status",
        "inactive",
    )
    value = load(workspace, "project", "target")
    assert str(value.name) == "Renamed" and value.content.strip() == "Updated"
    assert value.repository_url == "https://example.invalid/repo"
    assert value.status is ProjectStatus.ON_HOLD
    assert (
        persistent_bytes(workspace)["projects/survivor.md"]
        == before["projects/survivor.md"]
    )


def test_milestone_update_fields_and_reassignment_persist_atomically(
    workspace, cli_runner
):
    seed(
        workspace,
        entity("project", "old"),
        entity("project", "new"),
        Milestone(
            EntityId("target"),
            NOW,
            NOW,
            name=Name("target"),
            relation=MilestoneRelation(EntityId("old")),
        ),
        entity("milestone", "survivor"),
    )
    before = persistent_bytes(workspace)
    run(
        cli_runner,
        "milestone",
        "update",
        "target",
        "--name",
        "Renamed",
        "--description",
        "Updated",
        "--due-date",
        "2026-10-20",
        "--project",
        "new",
        "--status",
        "closed",
    )
    value = load(workspace, "milestone", "target")
    assert str(value.name) == "Renamed" and value.content.strip() == "Updated"
    assert value.due_at.value == datetime(2026, 10, 20, tzinfo=UTC)
    assert value.status is MilestoneStatus.CLOSED
    assert value.relation.project_id == EntityId("new")
    assert value.id not in load(workspace, "project", "old").relations.milestone_ids
    assert value.id in load(workspace, "project", "new").relations.milestone_ids
    assert (
        persistent_bytes(workspace)["milestones/survivor.md"]
        == before["milestones/survivor.md"]
    )


@pytest.mark.parametrize(
    "arguments",
    [
        ["--due-date", "invalid"],
        ["--project", "missing"],
        ["--status", "invalid"],
    ],
)
def test_invalid_milestone_update_preserves_state(workspace, cli_runner, arguments):
    seed(workspace, entity("milestone", "target"))
    before = persistent_bytes(workspace)
    result = cli_runner.invoke(cli, ["milestone", "update", "target", *arguments])
    assert result.exit_code != 0
    assert persistent_bytes(workspace) == before


@pytest.mark.parametrize("percentage", ["-1", "0", "35", "100", "101"])
def test_progress_range_and_workflow_effects_are_persisted(
    workspace, cli_runner, percentage
):
    seed(workspace, entity("issue", "target"), entity("issue", "survivor"))
    before = persistent_bytes(workspace)
    invalid = percentage in {"-1", "101"}
    run(cli_runner, "issue", "progress", "target", percentage, code=2 if invalid else 0)
    if invalid:
        assert persistent_bytes(workspace) == before
    else:
        value = load(workspace, "issue", "target")
        assert value.progress_percentage == float(percentage)
        assert (
            value.status.value
            == {"0": "todo", "35": "in-progress", "100": "todo"}[percentage]
        )
        assert (
            persistent_bytes(workspace)["issues/survivor.md"]
            == before["issues/survivor.md"]
        )


def test_block_unblock_reason_is_recorded_and_peer_unchanged(workspace, cli_runner):
    seed(workspace, entity("issue", "target"), entity("issue", "survivor"))
    before = persistent_bytes(workspace)
    run(cli_runner, "issue", "block", "target", "--reason", "Awaiting decision")
    value = load(workspace, "issue", "target")
    assert value.status is IssueStatus.BLOCKED
    assert value.history[-1].reason == "Awaiting decision"
    run(cli_runner, "issue", "unblock", "target", "--reason", "Decision recorded")
    value = load(workspace, "issue", "target")
    assert value.status is IssueStatus.IN_PROGRESS
    assert value.history[-1].reason == "Decision recorded"
    assert (
        persistent_bytes(workspace)["issues/survivor.md"]
        == before["issues/survivor.md"]
    )


@pytest.mark.parametrize("project_scope", [False, True])
def test_config_reset_yes_only_changes_selected_scope(
    workspace, cli_runner, project_scope
):
    run(cli_runner, "config", "set", "identity.name", "alice")
    run(
        cli_runner,
        "config",
        "set",
        "behavior.default_project_id",
        "selected",
        "--project",
    )
    project = workspace.configuration.project_path
    user = workspace.configuration.user_path
    before = {p: p.read_bytes() for p in (project, user)}
    run(
        cli_runner,
        "config",
        "reset",
        "--yes",
        *(["--project"] if project_scope else []),
    )
    selected, survivor = (project, user) if project_scope else (user, project)
    assert survivor.read_bytes() == before[survivor]
    assert (selected.read_bytes() if selected.exists() else None) != before[selected]
    key = "behavior.default_project_id" if project_scope else "identity.name"
    assert workspace.configuration.get(key) is None


def test_project_and_milestone_creation_fields_and_exact_parent(workspace, cli_runner):
    seed(workspace, entity("project", "survivor"))
    before = persistent_bytes(workspace)
    run(
        cli_runner,
        "project",
        "create",
        "--title",
        "Created project",
        "--description",
        "Project body",
        "--repository",
        "https://example.invalid/repo",
    )
    project = next(
        p for p in workspace.planning.all_projects() if p.name == "Created project"
    )
    assert project.content.strip() == "Project body"
    assert project.repository_url == "https://example.invalid/repo"
    run(
        cli_runner,
        "milestone",
        "create",
        "--title",
        "phase-1",
        "--description",
        "Phase body",
        "--due-date",
        "2026-10-20",
        "--project",
        str(project.id),
    )
    value = workspace.planning.milestone("phase-1").milestone
    assert value.content.strip() == "Phase body"
    assert value.due_at.value == datetime(2026, 10, 20, tzinfo=UTC)
    assert value.relation.project_id == project.id
    assert (
        value.id in load(workspace, "project", str(project.id)).relations.milestone_ids
    )
    assert (
        persistent_bytes(workspace)["projects/survivor.md"]
        == before["projects/survivor.md"]
    )


@pytest.mark.parametrize("kind", ["issue", "milestone", "project"])
def test_delete_yes_preserves_referenced_archived_entity(workspace, cli_runner, kind):
    parent = entity(kind, "target", archived=True)
    if kind == "project":
        child = Milestone(
            EntityId("child"),
            NOW,
            NOW,
            name=Name("child"),
            relation=MilestoneRelation(parent.id),
        )
    elif kind == "milestone":
        child = Issue(
            EntityId("child"),
            NOW,
            NOW,
            title=Title("child"),
            relations=IssueRelations(milestone_id=parent.id),
        )
    else:
        child = Issue(
            EntityId("child"),
            NOW,
            NOW,
            title=Title("child"),
            relations=IssueRelations(depends_on=(parent.id,)),
        )
    seed(workspace, parent, child)
    before = persistent_bytes(workspace)
    run(cli_runner, kind, "delete", "target", "--yes", code=1)
    assert persistent_bytes(workspace) == before


def test_orphaned_archive_selection_and_list_mode_are_bounded(workspace, cli_runner):
    milestone = entity("milestone", "milestone")
    linked = Issue(
        EntityId("linked"),
        NOW,
        NOW,
        title=Title("linked"),
        status=IssueStatus.CLOSED,
        relations=IssueRelations(milestone_id=milestone.id),
    )
    seed(workspace, milestone, linked, entity("issue", "orphan", closed=True))
    before = persistent_bytes(workspace)
    run(cli_runner, "issue", "archive", "--orphaned", "--dry-run")
    assert persistent_bytes(workspace) == before
    run(cli_runner, "issue", "archive", "--orphaned", input="y\n")
    assert load(workspace, "issue", "orphan").retention is RetentionState.ARCHIVED
    assert persistent_bytes(workspace)["issues/linked.md"] == before["issues/linked.md"]
    before = persistent_bytes(workspace)
    run(cli_runner, "issue", "archive", "--list")
    assert persistent_bytes(workspace) == before


def test_update_reason_and_record_time_are_not_just_accepted_options(
    workspace, cli_runner
):
    seed(workspace, entity("issue", "target"))
    run(
        cli_runner,
        "issue",
        "update",
        "target",
        "--title",
        "Renamed",
        "--reason",
        "Review decision",
    )
    value = load(workspace, "issue", "target")
    assert value.history[-1].reason == "Review decision"
    earliest = datetime.now(UTC)
    run(
        cli_runner, "issue", "close", "target", "--record-time", "--reason", "Completed"
    )
    latest = datetime.now(UTC)
    value = load(workspace, "issue", "target")
    assert earliest <= value.actual_end_at.value <= latest
    assert value.history[-1].reason == "Completed"
