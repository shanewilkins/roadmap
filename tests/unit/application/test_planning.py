"""Phase 8 contracts for the canonical planning product."""

from datetime import UTC, datetime, timedelta

import pytest

from roadmap.application.contracts import (
    MilestoneCreateCommand,
    ProjectCreateCommand,
)
from roadmap.application.failures import ApplicationFailure
from roadmap.application.use_cases import Planning
from roadmap.domain.aggregates import Issue, Milestone, Project
from roadmap.domain.types import (
    EntityId,
    IssueRelations,
    IssueStatus,
    MilestoneRelation,
    Name,
    Priority,
    ProjectRelations,
    ProjectStatus,
    RetentionState,
    Timestamp,
    Title,
)

NOW = Timestamp(datetime(2026, 8, 24, 12, tzinfo=UTC))


def _issue(identity: str, **updates) -> Issue:
    values = {
        "id": EntityId(identity),
        "created": NOW,
        "updated": NOW,
        "title": Title(f"Issue {identity}"),
    }
    values.update(updates)
    return Issue(**values)


def _milestone(identity: str, **updates) -> Milestone:
    values = {
        "id": EntityId(identity),
        "created": NOW,
        "updated": NOW,
        "name": Name(f"Milestone {identity}"),
    }
    values.update(updates)
    return Milestone(**values)


def _project(identity: str, **updates) -> Project:
    values = {
        "id": EntityId(identity),
        "created": NOW,
        "updated": NOW,
        "name": Name(f"Project {identity}"),
    }
    values.update(updates)
    return Project(**values)


class Unit:
    def __init__(self, factory):
        self.factory = factory
        self.projection_stale = factory.projection_stale
        self.saved_issues = {}
        self.saved_milestones = {}
        self.saved_projects = {}
        self.deleted_milestones = set()
        self.deleted_projects = set()

    def __enter__(self):
        return self

    def __exit__(self, _exc_type, _exc, _traceback):
        return None

    def list_issues(self):
        return tuple(self.factory.issues.values())

    def list_milestones(self):
        return tuple(self.factory.milestones.values())

    def list_projects(self):
        return tuple(self.factory.projects.values())

    def load_issue(self, identity):
        return self.factory.issues.get(identity)

    def load_milestone(self, identity):
        return self.factory.milestones.get(identity)

    def load_project(self, identity):
        return self.factory.projects.get(identity)

    def save_issue(self, value):
        self.saved_issues[value.id] = value

    def save_milestone(self, value):
        self.saved_milestones[value.id] = value

    def save_project(self, value):
        self.saved_projects[value.id] = value

    def delete_issue(self, _identity):
        return False

    def delete_milestone(self, identity):
        self.deleted_milestones.add(identity)
        return identity in self.factory.milestones

    def delete_project(self, identity):
        self.deleted_projects.add(identity)
        return identity in self.factory.projects

    def commit(self):
        if self.factory.fail_commit:
            raise OSError("interrupted commit")
        self.factory.issues.update(self.saved_issues)
        self.factory.milestones.update(self.saved_milestones)
        self.factory.projects.update(self.saved_projects)
        for identity in self.deleted_milestones:
            self.factory.milestones.pop(identity, None)
        for identity in self.deleted_projects:
            self.factory.projects.pop(identity, None)
        self.factory.commits += 1

    def rollback(self):
        self.saved_issues.clear()
        self.saved_milestones.clear()
        self.saved_projects.clear()


class Units:
    def __init__(self, *values, projection_stale=False, fail_commit=False):
        self.issues = {item.id: item for item in values if isinstance(item, Issue)}
        self.milestones = {
            item.id: item for item in values if isinstance(item, Milestone)
        }
        self.projects = {item.id: item for item in values if isinstance(item, Project)}
        self.projection_stale = projection_stale
        self.fail_commit = fail_commit
        self.commits = 0

    def create(self):
        return Unit(self)


class Clock:
    def now(self):
        return NOW


def _service(units: Units) -> Planning:
    return Planning(units, Clock())


def test_create_project_and_milestone_records_one_reciprocal_relationship() -> None:
    units = Units(projection_stale=True)
    service = _service(units)

    project_result = service.create_project(ProjectCreateCommand(Name("Roadmap")))
    milestone_result = service.create_milestone(
        MilestoneCreateCommand(Name("0.2"), project_id=project_result.aggregate.id)
    )

    project = units.projects[project_result.aggregate.id]
    milestone = units.milestones[milestone_result.aggregate.id]
    assert len(project.id) == len(milestone.id) == 36
    assert project.relations.milestone_ids == (milestone.id,)
    assert milestone.relation.project_id == project.id
    assert project_result.projection_stale


def test_progress_is_derived_from_current_canonical_issue_state() -> None:
    milestone = _milestone("milestone")
    project = _project("project", relations=ProjectRelations((milestone.id,)))
    closed = _issue(
        "closed",
        status=IssueStatus.CLOSED,
        estimated_hours=2,
        relations=IssueRelations(milestone_id=milestone.id),
    )
    partial = _issue(
        "partial",
        status=IssueStatus.IN_PROGRESS,
        estimated_hours=6,
        progress_percentage=50,
        relations=IssueRelations(milestone_id=milestone.id),
    )
    units = Units(project, milestone, closed, partial)

    snapshot = _service(units).snapshot()

    assert snapshot.milestones[0].progress == pytest.approx(62.5)
    assert snapshot.projects[0].progress == pytest.approx(62.5)
    units.issues[partial.id] = partial.set_progress(100, NOW)
    assert _service(units).snapshot().milestones[0].progress == 100


def test_assignment_close_and_archive_have_explicit_non_cascading_boundaries() -> None:
    project = _project("project")
    milestone = _milestone("milestone", relation=MilestoneRelation(project.id))
    issue = _issue("issue")
    units = Units(project, milestone, issue)
    service = _service(units)

    service.assign_issue(issue.id, milestone.id)
    assert units.issues[issue.id].relations.milestone_id == milestone.id
    with pytest.raises(ApplicationFailure, match="open issue"):
        service.close_milestone(milestone.id, force=False)
    service.close_milestone(milestone.id, force=True)

    archived = service.archive_milestone(
        str(milestone.id), all_closed=False, dry_run=False, force=False
    )
    assert archived.aggregates[0].retention is RetentionState.ARCHIVED
    assert units.issues[issue.id].retention is RetentionState.VISIBLE
    service.restore_milestone(str(milestone.id), restore_all=False, dry_run=False)
    assert units.milestones[milestone.id].retention is RetentionState.VISIBLE


def test_close_project_accepts_a_small_project_without_an_active_phase() -> None:
    project = _project("project")
    units = Units(project)

    result = _service(units).close_project(project.id, force=False)

    assert result.aggregate.status is ProjectStatus.COMPLETED


def test_purge_rejects_issue_refs_and_cleans_reciprocal_project_link() -> None:
    milestone = _milestone("milestone", retention=RetentionState.ARCHIVED)
    project = _project("project", relations=ProjectRelations((milestone.id,)))
    issue = _issue("issue", relations=IssueRelations(milestone_id=milestone.id))
    units = Units(project, milestone, issue)

    with pytest.raises(ApplicationFailure, match="referenced by issue"):
        _service(units).purge_milestone(milestone.id)
    assert milestone.id in units.milestones
    units.issues.clear()
    _service(units).purge_milestone(milestone.id)
    assert milestone.id not in units.milestones
    assert units.projects[project.id].relations.milestone_ids == ()


def test_daily_summary_uses_injected_time_and_complete_milestone_identity() -> None:
    upcoming = _milestone("upcoming", due_at=Timestamp(NOW.value + timedelta(days=2)))
    later = _milestone("later")
    overdue = _issue(
        "overdue",
        assignee="alice",
        priority=Priority.HIGH,
        due_at=Timestamp(NOW.value - timedelta(days=1)),
        relations=IssueRelations(milestone_id=upcoming.id),
    )
    unrelated = _issue(
        "unrelated",
        assignee="alice",
        relations=IssueRelations(milestone_id=later.id),
    )

    result = _service(Units(upcoming, later, overdue, unrelated)).daily_summary("alice")

    assert result.milestone.milestone.id == upcoming.id
    assert result.overdue == (overdue,)
    assert result.up_next == (overdue,)


def test_critical_path_is_deterministic_and_rejects_cycles() -> None:
    root = _issue("root", estimated_hours=2)
    middle = _issue(
        "middle",
        estimated_hours=3,
        relations=IssueRelations(depends_on=(root.id,)),
    )
    leaf = _issue(
        "leaf",
        estimated_hours=5,
        relations=IssueRelations(depends_on=(middle.id,)),
    )
    service = _service(Units(leaf, root, middle))

    result = service.critical_path(milestone=None, include_closed=True)

    assert result.critical_issue_ids == (root.id, middle.id, leaf.id)
    assert result.total_duration == 10
    cyclic_root = _issue(
        "root",
        estimated_hours=2,
        relations=IssueRelations(depends_on=(leaf.id,)),
    )
    with pytest.raises(ApplicationFailure, match="cycle"):
        _service(Units(cyclic_root, middle, leaf)).critical_path(
            milestone=None, include_closed=True
        )


def test_cross_aggregate_commit_failure_leaves_the_factory_unchanged() -> None:
    project = _project("project")
    units = Units(project, fail_commit=True)

    with pytest.raises(OSError, match="interrupted"):
        _service(units).create_milestone(
            MilestoneCreateCommand(Name("Release"), project_id=project.id)
        )

    assert units.milestones == {}
    assert units.projects[project.id] is project
    assert units.commits == 0
