"""Explainable local next-work policy over a canonical snapshot."""

from dataclasses import dataclass, replace
from datetime import UTC, datetime

from roadmap.application.contracts import NextWorkAction, NextWorkReport
from roadmap.domain.aggregates import Issue, Milestone, Project
from roadmap.domain.requirements import Requirement, RequirementStatus
from roadmap.domain.types import (
    IssueStatus,
    IssueType,
    MilestoneStatus,
    Priority,
    RetentionState,
    Timestamp,
)

from .requirement_eligibility import is_governed, maintenance_justified
from .requirement_gaps import calculate_requirement_gaps

_PRIORITIES = tuple(Priority)
_URGENCY = ("critical-defect", "overdue", "finish-review", "normal")
_ACTIONS = (
    "verify-requirement",
    "review-issue",
    "start-issue",
    "plan-requirement",
    "start-maintenance",
)


@dataclass(frozen=True, slots=True)
class _Snapshot:
    requirements: dict[str, Requirement]
    issues: dict[str, Issue]
    milestones: dict[str, Milestone]
    broken: dict[str, tuple[str, ...]]
    as_of: datetime


@dataclass(frozen=True, slots=True)
class _Candidate:
    record: NextWorkAction
    prerequisites: frozenset[str]
    current: bool = False


def _visible(item: Requirement | Issue | Milestone) -> bool:
    return item.retention is RetentionState.VISIBLE


def _requirement_blockers(
    requirement: Requirement, snapshot: _Snapshot
) -> dict[str, str]:
    blockers = {}
    if not is_governed(requirement):
        blockers[f"acceptance:{requirement.id}"] = (
            f"requirement {requirement.id} is not active governed intent "
            f"(status={requirement.effective_status}, "
            f"acceptance_current={requirement.acceptance_current})"
        )
    for identity in map(str, requirement.relations.depends_on):
        dependency = snapshot.requirements.get(identity)
        if dependency is None:
            blockers[f"missing:{identity}"] = (
                f"requirement dependency {identity} is missing"
            )
        elif not _visible(dependency):
            blockers[f"archived:{identity}"] = (
                f"requirement dependency {identity} is archived"
            )
        elif dependency.effective_status is not RequirementStatus.VERIFIED:
            blockers[f"requirement:{identity}"] = (
                f"requirement dependency {identity} is {dependency.effective_status}, "
                "not verified"
            )
    for relation in snapshot.broken.get(str(requirement.id), ()):
        blockers[f"broken:{relation}"] = f"broken canonical relation {relation}"
    return blockers


def _issue_dependency_blockers(issue: Issue, snapshot: _Snapshot) -> dict[str, str]:
    blockers = {}
    for identity in map(str, issue.relations.depends_on):
        dependency = snapshot.issues.get(identity)
        if dependency is None:
            blockers[f"missing:{identity}"] = f"issue dependency {identity} is missing"
        elif dependency.status is not IssueStatus.CLOSED:
            blockers[f"issue:{identity}"] = (
                f"issue dependency {identity} is {dependency.status}, not closed"
            )
    if issue.status is IssueStatus.BLOCKED:
        blockers[f"status:{issue.id}"] = (
            "issue status is blocked; explicit unblock required"
        )
    return blockers


def _owners(issue: Issue, snapshot: _Snapshot) -> tuple[Requirement, ...]:
    return tuple(
        sorted(
            (
                requirement
                for requirement in snapshot.requirements.values()
                if _visible(requirement)
                and is_governed(requirement)
                and issue.id in requirement.relations.implemented_by
            ),
            key=lambda requirement: str(requirement.id),
        )
    )


def _milestone_dates(
    identities: tuple[str, ...], snapshot: _Snapshot
) -> tuple[tuple[datetime, str], ...]:
    return tuple(
        (milestone.due_at.value, f"milestone:{identity}")
        for identity in identities
        if (milestone := snapshot.milestones.get(identity)) is not None
        and _visible(milestone)
        and milestone.status is MilestoneStatus.OPEN
        and milestone.due_at is not None
    )


def _urgency(
    deadline: datetime | None, as_of: datetime, critical_bug: bool, action: str
) -> str:
    if critical_bug:
        return "critical-defect"
    if deadline is not None and deadline < as_of:
        return "overdue"
    if action in {"verify-requirement", "review-issue"}:
        return "finish-review"
    return "normal"


def _record(
    *,
    entity_type: str,
    entity_id: str,
    title: str,
    action: str,
    priorities: tuple[tuple[Priority, str], ...],
    dates: tuple[tuple[datetime, str], ...],
    owners: tuple[str, ...],
    milestones: tuple[str, ...],
    reasons: tuple[str, ...],
    blockers: dict[str, str],
    snapshot: _Snapshot,
    critical_bug: bool = False,
) -> NextWorkAction:
    priority = min((value for value, _ in priorities), key=_PRIORITIES.index)
    deadline = min((value for value, _ in dates), default=None)
    return NextWorkAction(
        entity_type=entity_type,
        entity_id=entity_id,
        title=title,
        action=action,
        urgency=_urgency(deadline, snapshot.as_of, critical_bug, action),
        effective_priority=priority,
        priority_sources=tuple(
            sorted(f"{source}={value}" for value, source in priorities)
        ),
        effective_deadline=deadline,
        deadline_sources=tuple(
            sorted(f"{source}={value.isoformat()}" for value, source in dates)
        ),
        requirement_ids=owners,
        milestone_ids=milestones,
        reasons=tuple(sorted(reasons)),
        blockers=tuple(sorted(set(blockers.values()))),
    )


def _issue_scope(
    issue: Issue, owners: tuple[Requirement, ...], blockers: dict[str, str]
) -> list[str]:
    reasons = ["Ranking uses known canonical data, not complete remote-provider state."]
    if owners:
        reasons.append("Implementation of active governed intent.")
    elif maintenance_justified(issue):
        reasons.append(
            "Maintenance justified by exact label and nonempty Markdown body."
        )
    else:
        blockers[f"scope:{issue.id}"] = (
            "no active governed requirement or valid maintenance justification"
        )
    if issue.estimated_hours is None:
        reasons.append("Estimate missing; ordering does not use duration.")
    reasons.append(f"Issue state: {issue.status}.")
    return reasons


def _issue_action(issue: Issue, owners: tuple[Requirement, ...]) -> str:
    if issue.status is IssueStatus.REVIEW:
        return "review-issue"
    return "start-issue" if owners else "start-maintenance"


def _issue_candidate(issue: Issue, snapshot: _Snapshot) -> _Candidate:
    owners = _owners(issue, snapshot)
    blockers = _issue_dependency_blockers(issue, snapshot)
    reasons = _issue_scope(issue, owners, blockers)
    for owner in owners:
        blockers.update(_requirement_blockers(owner, snapshot))
    priorities = ((issue.priority, f"issue:{issue.id}"),) + tuple(
        (owner.priority, f"requirement:{owner.id}") for owner in owners
    )
    milestones = tuple(
        sorted(
            {str(issue.relations.milestone_id)}
            if issue.relations.milestone_id is not None
            else ()
        )
    )
    dates = _milestone_dates(milestones, snapshot)
    if issue.due_at is not None:
        dates += ((issue.due_at.value, f"issue:{issue.id}"),)
    action = _issue_action(issue, owners)
    effective = min((value for value, _ in priorities), key=_PRIORITIES.index)
    record = _record(
        entity_type="issue",
        entity_id=str(issue.id),
        title=str(issue.title),
        action=action,
        priorities=priorities,
        dates=dates,
        owners=tuple(str(owner.id) for owner in owners),
        milestones=milestones,
        reasons=tuple(reasons),
        blockers=blockers,
        snapshot=snapshot,
        critical_bug=issue.issue_type is IssueType.BUG
        and effective is Priority.CRITICAL,
    )
    return _Candidate(
        record, frozenset(blockers), issue.status is IssueStatus.IN_PROGRESS
    )


def _implementation_blockers(
    requirement: Requirement, snapshot: _Snapshot
) -> dict[str, str]:
    blockers = {}
    for identity in map(str, requirement.relations.implemented_by):
        issue = snapshot.issues.get(identity)
        if issue is None:
            blockers[f"missing:{identity}"] = (
                f"implementation issue {identity} is missing"
            )
        elif not _visible(issue):
            blockers[f"archived:{identity}"] = (
                f"implementation issue {identity} is archived"
            )
        elif issue.status is not IssueStatus.CLOSED:
            blockers[f"issue:{identity}"] = (
                f"implementation issue {identity} is {issue.status}, not closed"
            )
    return blockers


def _requirement_candidate(requirement: Requirement, snapshot: _Snapshot) -> _Candidate:
    blockers = _requirement_blockers(requirement, snapshot)
    linked = tuple(
        issue
        for identity in map(str, requirement.relations.implemented_by)
        if (issue := snapshot.issues.get(identity)) is not None and _visible(issue)
    )
    action = "verify-requirement" if linked else "plan-requirement"
    if linked:
        blockers.update(_implementation_blockers(requirement, snapshot))
    milestones = (
        (str(requirement.relations.milestone_target),)
        if requirement.relations.milestone_target is not None
        else ()
    )
    reasons = (
        f"Requirement state: {requirement.effective_status}.",
        f"Verification results: {', '.join(sorted(set(requirement.verification.values())))}.",
        "Plan visible implementation work."
        if not linked
        else "Review current criterion evidence; closed work does not verify intent.",
    )
    record = _record(
        entity_type="requirement",
        entity_id=str(requirement.id),
        title=str(requirement.definition.title),
        action=action,
        priorities=((requirement.priority, f"requirement:{requirement.id}"),),
        dates=_milestone_dates(milestones, snapshot),
        owners=(str(requirement.id),),
        milestones=milestones,
        reasons=reasons,
        blockers=blockers,
        snapshot=snapshot,
    )
    return _Candidate(record, frozenset(blockers))


def _sort_key(record: NextWorkAction):
    return (
        _URGENCY.index(record.urgency),
        record.effective_deadline or datetime.max.replace(tzinfo=UTC),
        _PRIORITIES.index(record.effective_priority),
        -record.unblocking_value,
        _ACTIONS.index(record.action),
        record.entity_id,
        record.entity_type,
    )


def _with_unblocking(
    candidate: _Candidate, candidates: tuple[_Candidate, ...]
) -> NextWorkAction:
    record = candidate.record
    if record.action == "plan-requirement":
        return record
    token = f"{record.entity_type}:{record.entity_id}"
    unblocks = tuple(
        sorted(
            f"{other.record.entity_type}:{other.record.entity_id}"
            for other in candidates
            if other is not candidate and other.prerequisites == {token}
        )
    )
    return replace(record, unblocking_value=len(unblocks), unblocks=unblocks)


def _report(
    candidates: tuple[_Candidate, ...], as_of: datetime, limit: int | None
) -> NextWorkReport:
    current, recommended, blocked = [], [], []
    for candidate in candidates:
        record = _with_unblocking(candidate, candidates)
        if record.blockers:
            blocked.append(record)
        elif candidate.current:
            current.append(record)
        else:
            recommended.append(record)
    ordered = tuple(sorted(recommended, key=_sort_key))
    return NextWorkReport(
        as_of,
        tuple(sorted(current, key=_sort_key)),
        ordered if limit is None else ordered[:limit],
        tuple(sorted(blocked, key=_sort_key)),
        len(ordered),
    )


def _candidates(snapshot: _Snapshot) -> tuple[_Candidate, ...]:
    issue_candidates = tuple(
        _issue_candidate(issue, snapshot)
        for issue in snapshot.issues.values()
        if _visible(issue) and issue.status is not IssueStatus.CLOSED
    )
    requirement_candidates = tuple(
        _requirement_candidate(requirement, snapshot)
        for requirement in snapshot.requirements.values()
        if _visible(requirement)
        and requirement.effective_status
        not in {
            RequirementStatus.VERIFIED,
            RequirementStatus.DEFERRED,
            RequirementStatus.REJECTED,
        }
    )
    return (*issue_candidates, *requirement_candidates)


def calculate_next_work(
    requirements: tuple[Requirement, ...],
    issues: tuple[Issue, ...],
    milestones: tuple[Milestone, ...],
    projects: tuple[Project, ...],
    as_of: Timestamp,
    limit: int | None = None,
) -> NextWorkReport:
    gaps = calculate_requirement_gaps(requirements, issues, milestones, projects)
    snapshot = _Snapshot(
        {str(item.id): item for item in requirements},
        {str(item.id): item for item in issues},
        {str(item.id): item for item in milestones},
        {item.entity_id: item.reasons for item in gaps.broken_links},
        as_of.value.astimezone(UTC),
    )
    return _report(_candidates(snapshot), snapshot.as_of, limit)
