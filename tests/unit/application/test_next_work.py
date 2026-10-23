"""Approved next-work ordering, eligibility and direct-unblocking examples."""

from dataclasses import replace
from datetime import timedelta

import pytest

from roadmap.application.use_cases.next_work import calculate_next_work
from roadmap.domain.aggregates import Issue, Milestone
from roadmap.domain.requirement_relations import RequirementRelations
from roadmap.domain.requirements import RequirementStatus
from roadmap.domain.types import (
    EntityId,
    IssueRelations,
    IssueStatus,
    IssueType,
    MilestoneStatus,
    Name,
    Priority,
    RetentionState,
    Timestamp,
    Title,
)
from tests.unit.domain.test_requirement_governance import accept, verified
from tests.unit.domain.test_requirements import NOW


def issue(identity: str, **changes) -> Issue:
    return replace(
        Issue(
            EntityId(identity),
            NOW,
            NOW,
            title=Title(identity),
            labels=("maintenance",),
            content="Maintain supported tooling.",
        ),
        **changes,
    )


def calculate(requirements=(), issues=(), milestones=(), *, as_of=NOW, limit=None):
    return calculate_next_work(
        tuple(requirements), tuple(issues), tuple(milestones), (), as_of, limit
    )


def test_approved_critical_overdue_finish_and_normal_order():
    critical = issue("critical", priority=Priority.CRITICAL, issue_type=IssueType.BUG)
    overdue = issue("overdue", due_at=Timestamp(NOW.value - timedelta(days=1)))
    review = issue("review", status=IssueStatus.REVIEW, priority=Priority.HIGH)
    high = issue("high", priority=Priority.HIGH)
    maintenance = issue("maintenance")
    blocked = issue("blocked", priority=Priority.CRITICAL, status=IssueStatus.BLOCKED)
    result = calculate(issues=(maintenance, high, review, overdue, critical, blocked))
    assert [item.entity_id for item in result.recommended] == [
        "critical",
        "overdue",
        "review",
        "high",
        "maintenance",
    ]
    assert [item.entity_id for item in result.blocked] == ["blocked"]
    assert result.blocked[0].blockers == (
        "issue status is blocked; explicit unblock required",
    )


def test_plan_and_verify_actions_do_not_auto_verify_closed_work():
    closed = issue("closed", status=IssueStatus.CLOSED)
    ready = replace(
        accept(), relations=RequirementRelations(implemented_by=(closed.id,))
    )
    unplanned = accept()
    result = calculate((unplanned, ready), (closed,))
    assert [item.action for item in result.recommended] == [
        "verify-requirement",
        "plan-requirement",
    ]
    assert ready.status is RequirementStatus.ACCEPTED
    assert calculate((verified(),)).recommended == ()


@pytest.mark.parametrize(
    "status", [RequirementStatus.DEFERRED, RequirementStatus.REJECTED]
)
def test_withdrawn_or_stale_requirement_does_not_justify_issue(status):
    work = issue("work", labels=(), content="")
    owner = replace(accept(), relations=RequirementRelations(implemented_by=(work.id,)))
    withdrawn = owner.transition(status, NOW, "Alice", "Out of scope")
    result = calculate((withdrawn,), (work,))
    assert not result.recommended
    assert "no active governed requirement" in result.blocked[0].blockers[0]
    stale = replace(owner, definition=replace(owner.definition, statement="New intent"))
    assert not calculate((stale,), (work,)).recommended


def test_priority_inheritance_and_milestone_deadline_have_explicit_sources():
    milestone = Milestone(
        EntityId("milestone"),
        NOW,
        NOW,
        name=Name("Release"),
        due_at=Timestamp(NOW.value + timedelta(days=1)),
    )
    work = issue(
        "work",
        labels=(),
        relations=IssueRelations(milestone_id=milestone.id),
        due_at=Timestamp(NOW.value + timedelta(days=3)),
    )
    owner = replace(
        accept(),
        priority=Priority.CRITICAL,
        relations=RequirementRelations(implemented_by=(work.id,)),
    )
    [record] = calculate((owner,), (work,), (milestone,)).recommended
    assert record.effective_priority is Priority.CRITICAL
    assert milestone.due_at is not None
    assert record.effective_deadline == milestone.due_at.value
    assert f"requirement:{owner.id}=critical" in record.priority_sources
    assert f"issue:{work.id}=medium" in record.priority_sources
    assert any("milestone:milestone=" in source for source in record.deadline_sources)
    assert record.requirement_ids == (str(owner.id),)
    assert owner.priority is Priority.CRITICAL and work.priority is Priority.MEDIUM


def test_closed_and_archived_milestone_dates_are_not_inherited():
    milestone = Milestone(
        EntityId("milestone"), NOW, NOW, name=Name("Release"), due_at=NOW
    )
    work = issue("work", relations=IssueRelations(milestone_id=milestone.id))
    for changed in (
        replace(milestone, status=MilestoneStatus.CLOSED),
        replace(milestone, retention=RetentionState.ARCHIVED),
    ):
        assert (
            calculate(issues=(work,), milestones=(changed,))
            .recommended[0]
            .effective_deadline
            is None
        )


def test_unblocking_value_counts_last_direct_prerequisite_not_transitive_chain():
    first = issue("a")
    second = issue("b", relations=IssueRelations(depends_on=(first.id,)))
    third = issue("c", relations=IssueRelations(depends_on=(second.id,)))
    extra = issue("d", relations=IssueRelations(depends_on=(first.id, second.id)))
    result = calculate(issues=(first, second, third, extra))
    [action] = result.recommended
    assert action.unblocking_value == 1
    assert action.unblocks == ("issue:b",)
    assert len(result.blocked) == 3


def test_requirement_verification_unblocks_but_planning_does_not():
    closed = issue("closed", status=IssueStatus.CLOSED)
    prerequisite = replace(
        accept(), relations=RequirementRelations(implemented_by=(closed.id,))
    )
    dependent = replace(
        accept(), relations=RequirementRelations(depends_on=(prerequisite.id,))
    )
    [action] = calculate((dependent, prerequisite), (closed,)).recommended
    assert action.unblocks == (f"requirement:{dependent.id}",)
    unplanned = replace(prerequisite, relations=RequirementRelations())
    [action] = calculate((dependent, unplanned)).recommended
    assert action.action == "plan-requirement"
    assert action.unblocking_value == 0


def test_unmet_requirement_dependencies_gate_implementation_too():
    prerequisite = accept()
    work = issue("work", labels=())
    dependent = replace(
        accept(),
        relations=RequirementRelations(
            depends_on=(prerequisite.id,), implemented_by=(work.id,)
        ),
    )
    result = calculate((dependent, prerequisite), (work,))
    blocked_issue = next(item for item in result.blocked if item.entity_type == "issue")
    assert any("not verified" in reason for reason in blocked_issue.blockers)
    assert all(item.entity_id != "work" for item in result.recommended)


def test_missing_archived_and_multiple_implementation_targets_are_not_ready():
    closed = issue("closed", status=IssueStatus.CLOSED)
    archived = issue(
        "archived", status=IssueStatus.CLOSED, retention=RetentionState.ARCHIVED
    )
    owner = replace(
        accept(),
        relations=RequirementRelations(
            implemented_by=(closed.id, archived.id, EntityId("missing"))
        ),
    )
    result = calculate((owner,), (closed, archived))
    assert not result.recommended
    [blocked] = result.blocked
    assert any("missing" in reason for reason in blocked.blockers)
    assert any("archived" in reason for reason in blocked.blockers)


def test_current_work_estimates_and_stable_ties_with_post_ranking_limit():
    a, b = issue("a"), issue("b", estimated_hours=100)
    current = issue("current", status=IssueStatus.IN_PROGRESS)
    archived = issue("archived", retention=RetentionState.ARCHIVED)
    result = calculate(issues=(b, current, a, archived), limit=1)
    assert [item.entity_id for item in result.recommended] == ["a"]
    assert result.recommended_total == 2
    assert [item.entity_id for item in result.current_work] == ["current"]
    assert any("Estimate missing" in reason for reason in result.recommended[0].reasons)
    assert result == calculate(issues=(archived, a, b, current), limit=1)


def test_injected_time_changes_overdue_band_only_at_actual_deadline():
    work = issue("dated", due_at=NOW)
    assert calculate(issues=(work,)).recommended[0].urgency == "normal"
    later = Timestamp(NOW.value + timedelta(seconds=1))
    assert calculate(issues=(work,), as_of=later).recommended[0].urgency == "overdue"


def test_cycles_and_missing_issue_dependencies_are_explained_not_recommended():
    first = issue("first", relations=IssueRelations(depends_on=(EntityId("second"),)))
    second = issue("second", relations=IssueRelations(depends_on=(first.id,)))
    missing = issue(
        "missing", relations=IssueRelations(depends_on=(EntityId("absent"),))
    )
    result = calculate(issues=(first, second, missing))
    assert not result.recommended
    assert len(result.blocked) == 3
    assert any(
        "is missing" in reason for item in result.blocked for reason in item.blockers
    )


def test_maintenance_requires_exact_label_and_nonempty_rationale():
    result = calculate(
        issues=(
            issue("wrong-label", labels=("Maintenance",)),
            issue("empty-body", content=" \n"),
            issue("valid"),
        )
    )
    assert [item.entity_id for item in result.recommended] == ["valid"]
    assert len(result.blocked) == 2


def test_deadline_then_priority_then_unblocking_then_uuid_ties():
    early = issue(
        "early", priority=Priority.LOW, due_at=Timestamp(NOW.value + timedelta(days=1))
    )
    late = issue(
        "late", priority=Priority.HIGH, due_at=Timestamp(NOW.value + timedelta(days=2))
    )
    a, z = issue("a"), issue("z")
    dependent = issue("dependent", relations=IssueRelations(depends_on=(z.id,)))
    result = calculate(issues=(a, z, dependent, late, early))
    assert [item.entity_id for item in result.recommended] == [
        "early",
        "late",
        "z",
        "a",
    ]
    assert result.recommended[2].unblocks == ("issue:dependent",)


def test_empty_snapshot_and_verified_dependency_are_supported():
    assert calculate().recommended == ()
    assert calculate().blocked == ()
    prerequisite = verified()
    work = issue("work", labels=())
    owner = replace(
        accept(),
        relations=RequirementRelations(
            depends_on=(prerequisite.id,), implemented_by=(work.id,)
        ),
    )
    assert [
        item.entity_id for item in calculate((owner, prerequisite), (work,)).recommended
    ] == ["work"]
