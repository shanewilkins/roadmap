"""Phase 7 contracts for transactional issue mutation use cases."""

from datetime import UTC, datetime, timedelta

import pytest

from roadmap.application.contracts import IssueCreateCommand, IssueUpdateCommand
from roadmap.application.failures import ApplicationFailure, FailureCategory
from roadmap.application.use_cases import IssueMutations
from roadmap.domain.aggregates import Issue, Milestone
from roadmap.domain.types import (
    EntityId,
    IssueRelations,
    IssueStatus,
    Name,
    RetentionState,
    Timestamp,
    Title,
)

NOW = Timestamp(datetime(2026, 8, 17, 12, tzinfo=UTC))
LATER = Timestamp(NOW.value + timedelta(hours=2))


def _issue(identity: str, **updates) -> Issue:
    values = {
        "id": EntityId(identity),
        "created": NOW,
        "updated": NOW,
        "title": Title(f"Issue {identity}"),
    }
    values.update(updates)
    return Issue(**values)


class Unit:
    def __init__(self, factory):
        self.factory = factory
        self.projection_stale = factory.projection_stale
        self.saved: dict[EntityId, Issue] = {}
        self.deleted: set[EntityId] = set()

    def __enter__(self):
        return self

    def __exit__(self, _exc_type, _exc, _traceback):
        return None

    def list_issues(self):
        return tuple(self.factory.issues.values())

    def load_issue(self, issue_id):
        return self.factory.issues.get(issue_id)

    def load_milestone(self, milestone_id):
        return self.factory.milestones.get(milestone_id)

    def save_issue(self, issue):
        self.saved[issue.id] = issue

    def delete_issue(self, issue_id):
        if issue_id not in self.factory.issues:
            return False
        self.deleted.add(issue_id)
        return True

    def commit(self):
        self.factory.issues.update(self.saved)
        for issue_id in self.deleted:
            self.factory.issues.pop(issue_id, None)
        self.factory.commits += 1

    def rollback(self):
        self.saved.clear()
        self.deleted.clear()


class Units:
    def __init__(self, *issues: Issue, projection_stale: bool = False):
        self.issues = {issue.id: issue for issue in issues}
        milestone = Milestone(EntityId("milestone"), NOW, NOW, name=Name("Milestone"))
        self.milestones = {milestone.id: milestone}
        self.projection_stale = projection_stale
        self.commits = 0

    def create(self):
        return Unit(self)


class Identity:
    def current_identity(self):
        return "current-user"


class Assignees:
    def canonical_assignee(self, assignee):
        return {"Alice": "alice", "current-user": "current-user"}.get(assignee)


class Clock:
    def now(self):
        return NOW


def _service(units: Units) -> IssueMutations:
    return IssueMutations(units, Identity(), Assignees(), Clock())


def test_create_assigns_complete_identity_and_updates_reciprocal_relations() -> None:
    dependency = _issue("dependency")
    units = Units(dependency, projection_stale=True)

    result = _service(units).create(
        IssueCreateCommand(
            Title("Created issue"),
            milestone_id=EntityId("milestone"),
            depends_on=(dependency.id,),
        )
    )

    assert len(result.issue.id) == 36
    assert result.issue.assignee == "current-user"
    assert result.issue.id in units.issues[dependency.id].relations.blocks
    assert result.projection_stale
    assert units.commits == 1


@pytest.mark.parametrize(
    "command,message",
    [
        (
            IssueCreateCommand(
                Title("Missing milestone"),
                milestone_id=EntityId("absent"),
            ),
            "Milestone 'absent' was not found",
        ),
        (
            IssueCreateCommand(Title("Bad assignee"), assignee="unknown"),
            "Invalid assignee",
        ),
    ],
)
def test_invalid_create_does_not_commit(command, message) -> None:
    units = Units()

    with pytest.raises(ApplicationFailure, match=message):
        _service(units).create(command)

    assert units.issues == {}
    assert units.commits == 0


def test_update_is_validated_and_identical_update_is_idempotent() -> None:
    issue = _issue("issue")
    units = Units(issue)
    service = _service(units)

    unchanged = service.update(IssueUpdateCommand(issue.id, title=issue.title))
    assert unchanged.issue is issue
    assert units.commits == 0

    changed = service.update(
        IssueUpdateCommand(issue.id, title=Title("Renamed"), assignee="Alice")
    )
    assert changed.issue.title == "Renamed"
    assert changed.issue.assignee == "alice"
    assert changed.issue.history[-1].action == "updated"
    assert units.commits == 1


def test_lifecycle_transitions_record_times_and_repeated_commands_are_noops() -> None:
    issue = _issue("issue")
    units = Units(issue)
    service = _service(units)

    started = service.start(issue.id).issue
    assert started.status is IssueStatus.IN_PROGRESS
    assert started.actual_start_at == NOW
    assert service.start(issue.id).issue == started
    assert units.commits == 1

    progressed = service.progress(issue.id, 50).issue
    assert progressed.progress_percentage == 50
    assert service.progress(issue.id, 50).issue == progressed
    closed = service.close(issue.id, LATER, "done", record_time=True).issue
    assert closed.status is IssueStatus.CLOSED
    assert closed.progress_percentage == 100
    assert closed.actual_end_at == LATER
    assert closed.history[-1].reason == "done"


def test_invalid_transition_leaves_canonical_state_unchanged() -> None:
    issue = _issue("issue", status=IssueStatus.TODO)
    units = Units(issue)

    with pytest.raises(ApplicationFailure, match="todo -> review") as captured:
        _service(units).transition(issue.id, IssueStatus.REVIEW)

    assert captured.value.category is FailureCategory.INVALID_REQUEST
    assert units.issues[issue.id] is issue
    assert units.commits == 0


def test_comments_validate_replies_and_allocate_stable_local_ids() -> None:
    issue = _issue("issue")
    units = Units(issue)
    service = _service(units)

    first = service.add_comment(issue.id, "alice", "First", None)
    second = service.add_comment(issue.id, "bob", "Reply", first.id)
    assert (first.id, second.id, second.in_reply_to) == (1, 2, 1)

    before = units.issues[issue.id]
    with pytest.raises(ApplicationFailure, match="Cannot find comment 99"):
        service.add_comment(issue.id, "alice", "Missing parent", 99)
    assert units.issues[issue.id] == before


def test_dependency_add_remove_and_replace_are_reciprocal() -> None:
    issue = _issue("issue")
    first = _issue("first")
    second = _issue("second")
    units = Units(issue, first, second)
    service = _service(units)

    service.add_dependency(issue.id, first.id)
    assert first.id in units.issues[issue.id].relations.depends_on
    assert issue.id in units.issues[first.id].relations.blocks

    service.replace_dependency(issue.id, first.id, second.id)
    assert units.issues[issue.id].relations.depends_on == (second.id,)
    assert issue.id not in units.issues[first.id].relations.blocks
    assert issue.id in units.issues[second.id].relations.blocks

    service.remove_dependency(issue.id, second.id)
    assert units.issues[issue.id].relations.depends_on == ()
    assert units.issues[second.id].relations.blocks == ()


def test_dependency_cycle_is_rejected_without_partial_reciprocal_write() -> None:
    first = _issue("first", relations=IssueRelations(depends_on=(EntityId("second"),)))
    second = _issue(
        "second",
        relations=IssueRelations(
            depends_on=(EntityId("third"),), blocks=(EntityId("first"),)
        ),
    )
    third = _issue("third", relations=IssueRelations(blocks=(EntityId("second"),)))
    units = Units(first, second, third)

    with pytest.raises(ApplicationFailure, match="cycle"):
        _service(units).add_dependency(third.id, first.id)

    assert units.issues[first.id] is first
    assert units.issues[second.id] is second
    assert units.issues[third.id] is third
    assert units.commits == 0


def test_archive_preview_restore_and_purge_have_explicit_boundaries() -> None:
    issue = _issue("issue", status=IssueStatus.CLOSED)
    units = Units(issue)
    service = _service(units)

    preview = service.archive(issue.id, dry_run=True)
    assert preview.issues[0].retention is RetentionState.ARCHIVED
    assert units.issues[issue.id].retention is RetentionState.VISIBLE

    service.archive(issue.id)
    assert units.issues[issue.id].retention is RetentionState.ARCHIVED
    service.restore(issue.id)
    assert units.issues[issue.id].retention is RetentionState.VISIBLE

    with pytest.raises(ApplicationFailure, match="must be archived"):
        service.purge(issue.id)
    service.archive(issue.id)
    purged = service.purge(issue.id)
    assert purged.id == issue.id
    assert issue.id not in units.issues


def test_purge_rejects_inbound_references_without_deleting() -> None:
    archived = _issue(
        "archived", retention=RetentionState.ARCHIVED, status=IssueStatus.CLOSED
    )
    referencing = _issue("other", relations=IssueRelations(depends_on=(archived.id,)))
    units = Units(archived, referencing)

    with pytest.raises(ApplicationFailure, match="referenced by other"):
        _service(units).purge(archived.id)

    assert archived.id in units.issues
    assert units.commits == 0
