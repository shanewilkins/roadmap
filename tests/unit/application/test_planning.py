"""Phase 8 contracts for the canonical planning product."""

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from roadmap.application.contracts import (
    MilestoneCreateCommand,
    MilestoneUpdateCommand,
    ProjectCreateCommand,
    ProjectUpdateCommand,
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


@pytest.mark.parametrize("kind", ["project", "milestone"])
def test_archived_planning_entities_require_explicit_visibility(kind):
    value = (
        _project("archived", retention=RetentionState.ARCHIVED)
        if kind == "project"
        else _milestone("archived", retention=RetentionState.ARCHIVED)
    )
    units = Units(value)
    lookup = getattr(_service(units), kind)
    with pytest.raises(ApplicationFailure, match="not found"):
        lookup(str(value.id))
    assert getattr(lookup(str(value.id), include_archived=True), kind) == value
    assert units.commits == 0


def _issue(identity: str, **updates) -> Issue:
    values: dict[str, Any] = {
        "id": EntityId(identity),
        "created": NOW,
        "updated": NOW,
        "title": Title(f"Issue {identity}"),
    }
    values.update(updates)
    return Issue(**values)


def _milestone(identity: str, **updates) -> Milestone:
    values: dict[str, Any] = {
        "id": EntityId(identity),
        "created": NOW,
        "updated": NOW,
        "name": Name(f"Milestone {identity}"),
    }
    values.update(updates)
    return Milestone(**values)


def _project(identity: str, **updates) -> Project:
    values: dict[str, Any] = {
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

    def create(self, *, read_only=False):
        return Unit(self)


class Clock:
    def now(self):
        return NOW


def _service(units: Units) -> Planning:
    return Planning(units, Clock())


@pytest.mark.parametrize("kind", ["project", "milestone"])
def test_duplicate_names_refuse_creation_without_commit(kind):
    existing = _project("one") if kind == "project" else _milestone("one")
    units = Units(existing)
    service = _service(units)
    command = (
        ProjectCreateCommand(existing.name)
        if kind == "project"
        else MilestoneCreateCommand(existing.name)
    )
    with pytest.raises(ApplicationFailure, match="already exists"):
        getattr(service, f"create_{kind}")(command)
    assert units.commits == 0
    assert tuple(getattr(units, f"{kind}s").values()) == (existing,)


@pytest.mark.parametrize("missing", ["issue", "milestone"])
def test_assignment_with_missing_entity_preserves_existing_relations(missing):
    issue, milestone = _issue("issue"), _milestone("milestone")
    units = Units(issue, milestone)
    with pytest.raises(ApplicationFailure, match="not found"):
        _service(units).assign_issue(
            EntityId("missing") if missing == "issue" else issue.id,
            EntityId("missing") if missing == "milestone" else milestone.id,
        )
    assert units.issues[issue.id] == issue
    assert units.milestones[milestone.id] == milestone
    assert units.commits == 0


def test_repeated_assignment_and_closure_do_not_add_events_or_commits():
    issue, milestone, project = (
        _issue("issue"),
        _milestone("milestone"),
        _project("project"),
    )
    units = Units(issue, milestone, project)
    service = _service(units)
    service.assign_issue(issue.id, milestone.id)
    service.close_milestone(milestone.id, force=True)
    service.close_project(project.id, force=False)
    before = (
        dict(units.issues),
        dict(units.milestones),
        dict(units.projects),
        units.commits,
    )
    service.assign_issue(issue.id, milestone.id)
    service.close_milestone(milestone.id, force=True)
    service.close_project(project.id, force=False)
    assert (units.issues, units.milestones, units.projects, units.commits) == before


def test_projectless_milestone_and_unique_prefix_resolution():
    units = Units(_project("project-unique"))
    service = _service(units)
    result = service.create_milestone(MilestoneCreateCommand(Name("Standalone")))
    assert isinstance(result.aggregate, Milestone)
    assert result.aggregate.relation.project_id is None
    assert service.project("project-u").project.id == EntityId("project-unique")
    assert units.commits == 1


def test_unchanged_project_update_does_not_commit():
    project = _project("project")
    units = Units(project)
    assert (
        _service(units).update_project(ProjectUpdateCommand(project.id)).aggregate
        == project
    )
    assert units.commits == 0


@pytest.mark.parametrize("kind", ["project", "milestone"])
def test_archive_requires_a_selector(kind):
    units = Units(_project("project"), _milestone("milestone"))
    with pytest.raises(ApplicationFailure):
        getattr(_service(units), f"archive_{kind}")(
            None, all_closed=False, dry_run=False, force=False
        )
    assert units.commits == 0


def test_daily_summary_terminates_on_manually_authored_dependency_cycle():
    milestone = _milestone("milestone", due_at=Timestamp(NOW.value + timedelta(days=1)))
    first = _issue(
        "a",
        assignee="alice",
        priority=Priority.HIGH,
        relations=IssueRelations(
            milestone_id=milestone.id, depends_on=(EntityId("b"),)
        ),
    )
    second = _issue(
        "b",
        assignee="alice",
        priority=Priority.HIGH,
        relations=IssueRelations(milestone_id=milestone.id, depends_on=(first.id,)),
    )
    units = Units(milestone, first, second)
    service = _service(units)
    result = service.daily_summary("alice")
    assert {item.id for item in result.up_next} == {first.id, second.id}
    assert service.daily_summary("alice") == result
    assert units.commits == 0


def test_daily_summary_finds_legacy_padded_assignee_without_rewriting():
    milestone = _milestone("milestone")
    issue = _issue(
        "legacy",
        assignee=" alice ",
        priority=Priority.HIGH,
        relations=IssueRelations(milestone_id=milestone.id),
    )
    units = Units(milestone, issue)
    result = _service(units).daily_summary("alice")
    assert [item.id for item in result.up_next] == [issue.id]
    assert units.issues[issue.id].assignee == " alice "
    assert units.commits == 0


def test_critical_path_handles_dependency_absent_from_visible_snapshot():
    issue = _issue(
        "visible",
        estimated_hours=2,
        relations=IssueRelations(depends_on=(EntityId("absent"),)),
    )
    units = Units(issue)
    result = _service(units).critical_path(milestone=None, include_closed=False)
    assert result.total_duration == 2
    assert units.commits == 0


def test_reprojecting_existing_reciprocal_link_does_not_duplicate_it():
    milestone = _milestone("milestone")
    project = _project("project", relations=ProjectRelations((milestone.id,)))
    units = Units(milestone, project)
    _service(units).update_milestone(
        MilestoneUpdateCommand(milestone.id, project_id=project.id)
    )
    assert units.projects[project.id].relations.milestone_ids == (milestone.id,)
    assert units.milestones[milestone.id].relation.project_id == project.id


def test_purge_milestone_leaves_unrelated_project_unchanged():
    milestone = _milestone("milestone", retention=RetentionState.ARCHIVED)
    linked = _project("linked", relations=ProjectRelations((milestone.id,)))
    unrelated = _project("unrelated")
    units = Units(milestone, linked, unrelated)
    _service(units).purge_milestone(milestone.id)
    assert units.projects[unrelated.id] == unrelated
    assert units.projects[linked.id].relations.milestone_ids == ()
    assert milestone.id not in units.milestones


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
