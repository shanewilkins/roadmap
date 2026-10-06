"""Pure contracts for the target Domain introduced in Phase 4."""

from datetime import UTC, datetime, timedelta
from enum import StrEnum
from itertools import product
from uuid import UUID

import pytest

from roadmap.domain.aggregates import Issue, Milestone, Project
from roadmap.domain.failures import InvalidTransition, InvalidValue, InvariantViolation
from roadmap.domain.transitions import (
    ISSUE_TRANSITIONS,
    MILESTONE_TRANSITIONS,
    PROJECT_TRANSITIONS,
    RETENTION_TRANSITIONS,
    require_transition,
)
from roadmap.domain.types import (
    EntityId,
    IssueComment,
    IssueRelations,
    IssueStatus,
    MilestoneRelation,
    MilestoneStatus,
    Name,
    ProjectRelations,
    ProjectStatus,
    RetentionState,
    Timestamp,
    Title,
)

NOW = Timestamp(datetime(2026, 8, 16, 12, tzinfo=UTC))
LATER = Timestamp(NOW.value + timedelta(minutes=1))


@pytest.mark.parametrize(
    "changes",
    [
        {"actual_start_at": LATER, "actual_end_at": NOW},
        {"comments": (IssueComment(1, "alice", "First", NOW, NOW),) * 2},
        {"comments": (IssueComment(2, "alice", "Reply", NOW, NOW, in_reply_to=1),)},
    ],
)
def test_issue_rejects_inconsistent_dates_and_comment_graph_without_mutation(changes):
    from dataclasses import replace

    original = Issue(EntityId("issue"), NOW, NOW, title=Title("Original"))
    with pytest.raises(InvariantViolation):
        replace(original, **changes)
    assert original.comments == ()
    assert original.actual_start_at is None


@pytest.mark.parametrize(
    "changes",
    [
        {"estimated_hours": 0},
        {"estimated_hours": -1},
        {"actual_hours": -1},
        {"start_at": LATER, "target_end_at": NOW},
    ],
)
def test_project_rejects_invalid_hours_and_date_range(changes):
    with pytest.raises(InvariantViolation):
        Project(EntityId("project"), NOW, NOW, name=Name("Project"), **changes)


@pytest.mark.parametrize("percentage", [-1, 101])
def test_out_of_range_progress_preserves_original(percentage):
    original = Issue(EntityId("issue"), NOW, NOW, title=Title("Original"))
    with pytest.raises(InvariantViolation):
        original.set_progress(percentage, LATER)
    assert original.progress_percentage is None
    assert original.updated == NOW


def test_reset_progress_and_repeated_branch_link_preserve_consistency():
    original = Issue(
        EntityId("issue"),
        NOW,
        NOW,
        title=Title("Original"),
        status=IssueStatus.IN_PROGRESS,
        progress_percentage=50,
    )
    reset = original.set_progress(0, LATER)
    assert reset.status is IssueStatus.TODO
    assert reset.progress_percentage == 0
    assert original.status is IssueStatus.IN_PROGRESS
    with pytest.raises(InvariantViolation):
        original.link_branch("  ", LATER)
    linked = original.link_branch(" feature/work ", LATER)
    assert linked.link_branch("feature/work", LATER) == linked
    assert linked.git_branches == ("feature/work",)


TRANSITION_CASES = (
    [
        ("issue", current, target, ISSUE_TRANSITIONS)
        for current, target in product(IssueStatus, repeat=2)
    ]
    + [
        ("milestone", current, target, MILESTONE_TRANSITIONS)
        for current, target in product(MilestoneStatus, repeat=2)
    ]
    + [
        ("project", current, target, PROJECT_TRANSITIONS)
        for current, target in product(ProjectStatus, repeat=2)
    ]
    + [
        ("retention", current, target, RETENTION_TRANSITIONS)
        for current, target in product(RetentionState, repeat=2)
    ]
)


@pytest.mark.parametrize(
    ("machine", "current", "target", "table"),
    TRANSITION_CASES,
    ids=lambda value: (
        value if isinstance(value, str) else getattr(value, "value", None)
    ),
)
def test_transition_tables_are_exhaustive(
    machine: str,
    current: StrEnum,
    target: StrEnum,
    table: dict[StrEnum, frozenset[StrEnum]],
) -> None:
    """Every pair is either explicitly permitted or rejected without mutation."""
    expected = current == target or target in table[current]
    if expected:
        require_transition(current, target, table)
    else:
        with pytest.raises(InvalidTransition, match="not permitted"):
            require_transition(current, target, table)


def test_stable_issue_id_survives_supported_identity_independent_changes() -> None:
    original = Issue(
        EntityId("5898cb1f"),
        NOW,
        NOW,
        title=Title("Original"),
        relations=IssueRelations(milestone_id=EntityId("milestone-old")),
    )
    changed = original.rename(Title("Renamed"), LATER)
    changed = changed.reassign(
        IssueRelations(milestone_id=EntityId("milestone-new")), LATER
    )
    changed = changed.change_status(IssueStatus.CLOSED, LATER)
    changed = changed.change_retention(RetentionState.ARCHIVED, LATER)
    changed = changed.change_retention(RetentionState.VISIBLE, LATER)

    assert changed.id == original.id
    assert changed.status is IssueStatus.CLOSED
    assert changed.retention is RetentionState.VISIBLE


def test_every_aggregate_has_stable_opaque_identity() -> None:
    milestone = Milestone(EntityId("milestone-id"), NOW, NOW, name=Name("Milestone"))
    project = Project(EntityId("project-id"), NOW, NOW, name=Name("Project"))

    assert milestone.rename(Name("Renamed"), LATER).id == milestone.id
    assert (
        milestone.reassign(MilestoneRelation(EntityId("project-id")), LATER).id
        == milestone.id
    )
    assert project.rename(Name("Renamed"), LATER).id == project.id
    assert project.reassign(ProjectRelations((milestone.id,)), LATER).id == project.id


def test_new_ids_are_complete_lowercase_uuid4_values() -> None:
    entity_id = EntityId.new()
    parsed = UUID(entity_id)

    assert str(parsed) == entity_id
    assert parsed.version == 4


@pytest.mark.parametrize("value", ["", " leading", "trailing ", "a/b", "a\\b", "a\nb"])
def test_invalid_ids_are_rejected(value: str) -> None:
    with pytest.raises(InvalidValue):
        EntityId(value)


def test_timestamps_require_timezone_information() -> None:
    with pytest.raises(InvalidValue, match="UTC offset"):
        Timestamp(datetime(2026, 8, 16, 12))


def test_issue_invariants_reject_bad_progress_estimates_and_relations() -> None:
    with pytest.raises(InvariantViolation, match="progress"):
        Issue(EntityId("i-1"), NOW, NOW, title=Title("Issue"), progress_percentage=101)
    with pytest.raises(InvariantViolation, match="estimated"):
        Issue(EntityId("i-1"), NOW, NOW, title=Title("Issue"), estimated_hours=0)
    with pytest.raises(InvalidValue, match="reference self"):
        Issue(
            EntityId("i-1"),
            NOW,
            NOW,
            title=Title("Issue"),
            relations=IssueRelations(depends_on=(EntityId("i-1"),)),
        )


def test_aggregate_timestamps_cannot_move_before_creation() -> None:
    earlier = Timestamp(NOW.value - timedelta(seconds=1))
    with pytest.raises(InvariantViolation, match="precede"):
        Project(EntityId("p-1"), NOW, earlier, name=Name("Project"))


def test_project_relations_reject_duplicate_milestones() -> None:
    milestone_id = EntityId("m-1")
    with pytest.raises(InvalidValue, match="unique"):
        ProjectRelations((milestone_id, milestone_id))
