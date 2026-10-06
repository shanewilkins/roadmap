"""Deletion and relationship guarantees against real canonical storage."""

from __future__ import annotations

import errno
import os
import sqlite3
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path

import pytest

from roadmap.adapters.outbound.persistence.canonical import (
    CanonicalIssueUnitOfWorkFactory,
    CanonicalUnitOfWork,
)
from roadmap.adapters.outbound.persistence.documents import DocumentRepository
from roadmap.adapters.outbound.persistence.projection import SQLiteProjection
from roadmap.application.failures import ApplicationFailure
from roadmap.application.use_cases import IssueMutations, Planning
from roadmap.domain.aggregates import Issue, Milestone, Project
from roadmap.domain.types import (
    EntityId,
    IssueRelations,
    IssueStatus,
    MilestoneRelation,
    Name,
    ProjectStatus,
    RetentionState,
    Timestamp,
    Title,
)

NOW = Timestamp(datetime(2026, 10, 6, tzinfo=UTC))


class Clock:
    def now(self):
        return NOW


class Identity:
    def current_identity(self):
        return "alice"


class Assignees:
    def canonical_assignee(self, assignee):
        return assignee


class Workspace:
    def __init__(self, root):
        self.root = root / ".roadmap"
        self.documents = DocumentRepository(self.root)
        self.projection = SQLiteProjection(
            self.root / "db/projection.db", self.documents
        )
        units = CanonicalIssueUnitOfWorkFactory(self.documents, self.projection)
        self.planning = Planning(units, Clock())
        self.issues = IssueMutations(units, Identity(), Assignees(), Clock())

    def seed(self, *values):
        with CanonicalUnitOfWork(self.documents, self.projection) as unit:
            for value in values:
                if isinstance(value, Project):
                    unit.save_project(value)
                elif isinstance(value, Milestone):
                    unit.save_milestone(value)
                else:
                    unit.save_issue(value)
            unit.commit()

    def bytes(self):
        return {
            str(p.relative_to(self.root)): p.read_bytes()
            for p in self.root.rglob("*.md")
        }

    def projected(self):
        with closing(sqlite3.connect(self.projection.path)) as connection:
            return connection.execute(
                "SELECT kind, entity_id, retention, attributes FROM documents ORDER BY kind, entity_id"
            ).fetchall()


@pytest.fixture
def workspace(tmp_path):
    return Workspace(tmp_path)


def project(identity="project", **updates):
    return Project(EntityId(identity), NOW, NOW, name=Name(identity), **updates)


def issue(identity, **updates):
    return Issue(EntityId(identity), NOW, NOW, title=Title(identity), **updates)


@pytest.mark.parametrize("guard", ["visible", "referenced", "missing"])
def test_project_purge_guards_preserve_documents_and_projection(workspace, guard):
    value = project(
        retention=RetentionState.ARCHIVED
        if guard != "visible"
        else RetentionState.VISIBLE
    )
    milestone = Milestone(
        EntityId("milestone"),
        NOW,
        NOW,
        name=Name("milestone"),
        relation=MilestoneRelation(value.id)
        if guard == "referenced"
        else MilestoneRelation(),
    )
    workspace.seed(value, milestone)
    before, rows = workspace.bytes(), workspace.projected()
    message = {
        "visible": "must be archived",
        "referenced": "referenced by milestone",
        "missing": "was not found",
    }[guard]
    with pytest.raises(ApplicationFailure, match=message):
        workspace.planning.purge_project(
            EntityId("absent") if guard == "missing" else value.id
        )
    assert workspace.bytes() == before
    assert workspace.projected() == rows


def test_unreferenced_archived_project_purge_updates_both_stores(workspace):
    value = project(retention=RetentionState.ARCHIVED)
    survivor = project("survivor")
    workspace.seed(value, survivor)
    survivor_path = workspace.root / "projects/survivor.md"
    before = survivor_path.read_bytes()
    assert workspace.planning.purge_project(value.id) == value
    assert workspace.documents.load("project", value.id) is None
    assert [(row[0], row[1]) for row in workspace.projected()] == [
        ("project", "survivor")
    ]
    assert survivor_path.read_bytes() == before
    assert workspace.projection.inspect_state() == "current"


@pytest.mark.parametrize("dry_run", [True, False])
def test_project_retention_batch_selects_only_complete_visible_projects(
    workspace, dry_run
):
    completed = project("completed", status=ProjectStatus.COMPLETED)
    active = project("active")
    archived = project(
        "archived", status=ProjectStatus.COMPLETED, retention=RetentionState.ARCHIVED
    )
    workspace.seed(completed, active, archived)
    before, rows = workspace.bytes(), workspace.projected()
    result = workspace.planning.archive_project(
        None, all_closed=True, dry_run=dry_run, force=False
    )
    assert [value.id for value in result.aggregates] == [completed.id]
    if dry_run:
        assert workspace.bytes() == before
        assert workspace.projected() == rows
    else:
        assert (
            workspace.documents.load("project", completed.id).aggregate.retention
            is RetentionState.ARCHIVED
        )
        restored = workspace.planning.restore_project(
            None, restore_all=True, dry_run=False
        )
        assert {value.id for value in restored.aggregates} == {
            completed.id,
            archived.id,
        }
        assert all(row[2] == "visible" for row in workspace.projected())


def test_archive_requires_force_and_close_requires_closed_milestones(workspace):
    value = project()
    milestone = Milestone(
        EntityId("milestone"),
        NOW,
        NOW,
        name=Name("milestone"),
        relation=MilestoneRelation(value.id),
    )
    workspace.seed(value, milestone)
    before = workspace.bytes()
    with pytest.raises(ApplicationFailure, match="open milestone"):
        workspace.planning.close_project(value.id, force=False)
    with pytest.raises(ApplicationFailure):
        workspace.planning.archive_project(
            str(value.id), all_closed=False, dry_run=False, force=False
        )
    assert workspace.bytes() == before
    workspace.planning.archive_project(
        str(value.id), all_closed=False, dry_run=False, force=True
    )
    assert (
        workspace.documents.load("milestone", milestone.id).aggregate.retention
        is RetentionState.VISIBLE
    )


@pytest.mark.parametrize("operation", ["purge", "replace"])
def test_write_failure_rolls_back_real_deletion_or_reciprocal_edit(
    workspace, monkeypatch, operation
):
    value = project(retention=RetentionState.ARCHIVED)
    dependency = issue("old", relations=IssueRelations(blocks=(EntityId("dependent"),)))
    dependent = issue(
        "dependent", relations=IssueRelations(depends_on=(dependency.id,))
    )
    replacement = issue("new")
    workspace.seed(value, dependency, dependent, replacement)
    before, rows = workspace.bytes(), workspace.projected()
    original = os.replace
    replacements = 0

    def fail_canonical_once(source, target):
        nonlocal replacements
        if Path(target).suffix == ".md":
            replacements += 1
            if replacements == 2:
                raise OSError(errno.ENOSPC, "injected storage failure")
        return original(source, target)

    if operation == "purge":
        # Deletion uses unlink rather than replacement; fail after canonical
        # changes so rollback must restore the deleted document.
        def fail_after_apply(stage, _path):
            if stage == "after_replace":
                raise OSError(errno.ENOSPC, "injected storage failure")

        units = CanonicalIssueUnitOfWorkFactory(
            workspace.documents, workspace.projection
        )
        monkeypatch.setattr(
            units,
            "create",
            lambda: CanonicalUnitOfWork(
                workspace.documents,
                workspace.projection,
                failure_injector=fail_after_apply,
            ),
        )
        planning = Planning(units, Clock())

        def action():
            return planning.purge_project(value.id)
    else:
        monkeypatch.setattr(os, "replace", fail_canonical_once)

        def action():
            return workspace.issues.replace_dependency(
                dependent.id, dependency.id, replacement.id
            )

    with pytest.raises(OSError, match="injected storage failure"):
        action()
    assert workspace.bytes() == before
    assert workspace.projected() == rows
    assert not list((workspace.root / "db/transactions").iterdir())


@pytest.mark.parametrize("case", ["missing-old", "same", "cycle", "deduplicate"])
def test_dependency_replacement_guards_and_reciprocity(workspace, case):
    old = issue("old", relations=IssueRelations(blocks=(EntityId("dependent"),)))
    dependent = issue(
        "dependent",
        relations=IssueRelations(
            depends_on=(old.id, EntityId("new")) if case == "deduplicate" else (old.id,)
        ),
    )
    new = issue(
        "new",
        relations=IssueRelations(depends_on=(dependent.id,))
        if case == "cycle"
        else IssueRelations(),
    )
    workspace.seed(old, dependent, new)
    before, rows = workspace.bytes(), workspace.projected()
    if case in {"missing-old", "cycle"}:
        with pytest.raises(ApplicationFailure):
            workspace.issues.replace_dependency(
                dependent.id, new.id if case == "missing-old" else old.id, new.id
            )
        assert workspace.bytes() == before
        assert workspace.projected() == rows
    elif case == "same":
        workspace.issues.replace_dependency(dependent.id, old.id, old.id)
        assert workspace.bytes() == before
        assert workspace.projected() == rows
    else:
        workspace.issues.replace_dependency(dependent.id, old.id, new.id)
        assert workspace.documents.load(
            "issue", dependent.id
        ).aggregate.relations.depends_on == (new.id,)
        assert (
            workspace.documents.load("issue", old.id).aggregate.relations.blocks == ()
        )
        assert workspace.documents.load("issue", new.id).aggregate.relations.blocks == (
            dependent.id,
        )
        assert workspace.projection.inspect_state() == "current"


@pytest.mark.parametrize("selection", ["closed", "orphaned"])
def test_issue_batch_archive_dry_run_and_force_are_bounded(workspace, selection):
    closed = issue("closed", status=IssueStatus.CLOSED)
    active = issue("active")
    linked = issue(
        "linked", relations=IssueRelations(milestone_id=EntityId("milestone"))
    )
    archived = issue("archived", retention=RetentionState.ARCHIVED)
    workspace.seed(closed, active, linked, archived)
    before, rows = workspace.bytes(), workspace.projected()
    options = {"all_closed": selection == "closed", "orphaned": selection == "orphaned"}
    preview = workspace.issues.archive(**options, force=True, dry_run=True)
    expected = {closed.id} if selection == "closed" else {closed.id, active.id}
    assert {value.id for value in preview.issues} == expected
    assert workspace.bytes() == before
    assert workspace.projected() == rows
    if selection == "orphaned":
        with pytest.raises(ApplicationFailure, match="Only closed"):
            workspace.issues.archive(**options)
        assert workspace.bytes() == before
    workspace.issues.archive(**options, force=True)
    assert (
        workspace.documents.load("issue", linked.id).aggregate.retention
        is RetentionState.VISIBLE
    )
    assert workspace.projection.inspect_state() == "current"
