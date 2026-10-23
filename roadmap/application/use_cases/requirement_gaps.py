"""Deterministic read-only requirement traceability gap calculation."""

from collections.abc import Iterable
from dataclasses import dataclass

from roadmap.application.contracts import (
    REQUIREMENT_GAP_CATEGORIES,
    RequirementGapGroup,
    RequirementGapGroupCategory,
    RequirementGapRecord,
    RequirementGapReport,
)
from roadmap.domain.aggregates import Issue, Milestone, Project
from roadmap.domain.requirements import Requirement, RequirementStatus
from roadmap.domain.types import IssueStatus, RetentionState


def _record(entity_id, *reasons: str) -> RequirementGapRecord:
    return RequirementGapRecord(str(entity_id), tuple(sorted(reasons)))


def _ordered(
    records: Iterable[RequirementGapRecord],
) -> tuple[RequirementGapRecord, ...]:
    return tuple(sorted(records, key=lambda item: item.entity_id))


def _broken_reasons(
    requirement: Requirement,
    requirement_ids: set[str],
    issue_ids: set[str],
    milestone_ids: set[str],
    project_ids: set[str],
) -> tuple[str, ...]:
    relations = requirement.relations
    reasons = [
        f"supports:{target}"
        for target in map(str, relations.supports)
        if target not in requirement_ids
    ]
    reasons.extend(
        f"depends-on:{target}"
        for target in map(str, relations.depends_on)
        if target not in requirement_ids
    )
    reasons.extend(
        f"implemented-by:{target}"
        for target in map(str, relations.implemented_by)
        if target not in issue_ids
    )
    optional = (
        ("project-target", relations.project_target, project_ids),
        ("milestone-target", relations.milestone_target, milestone_ids),
    )
    reasons.extend(
        f"{relation}:{target}"
        for relation, target, valid_ids in optional
        if target is not None and str(target) not in valid_ids
    )
    return tuple(reasons)


def _blocked_reasons(
    requirement: Requirement,
    requirements: dict[str, Requirement],
    issues: dict[str, Issue],
) -> tuple[str, ...]:
    reasons = []
    for target in map(str, requirement.relations.depends_on):
        dependency = requirements.get(target)
        if dependency is None:
            reasons.append(f"missing dependency {target}")
        elif dependency.effective_status is not RequirementStatus.VERIFIED:
            reasons.append(f"dependency {target} is {dependency.effective_status}")
    reasons.extend(
        f"implementation issue {target} is blocked"
        for target in map(str, requirement.relations.implemented_by)
        if target in issues and issues[target].status is IssueStatus.BLOCKED
    )
    return tuple(reasons)


def _maintenance_justified(issue: Issue) -> bool:
    return "maintenance" in issue.labels and bool(issue.content.strip())


def _release_values(issue: Issue) -> tuple[str, ...]:
    values = sorted(
        label.partition(":")[2]
        for label in issue.labels
        if label.startswith("release:") and label.partition(":")[2]
    )
    return tuple(values) or ("unassigned",)


def _requirement_dimensions(
    requirement: Requirement, issues: dict[str, Issue]
) -> dict[str, tuple[str, ...]]:
    releases = {
        value
        for target in map(str, requirement.relations.implemented_by)
        if (issue := issues.get(target)) is not None
        for value in _release_values(issue)
        if value != "unassigned"
    }
    return {
        "journey": (str(requirement.journey) if requirement.journey else "unassigned",),
        "priority": (str(requirement.priority),),
        "milestone": (str(requirement.relations.milestone_target or "unassigned"),),
        "release": tuple(sorted(releases)) or ("unassigned",),
    }


def _coverage_groups(
    categories: dict[str, tuple[RequirementGapRecord, ...]],
    requirements: dict[str, Requirement],
    issues: dict[str, Issue],
) -> tuple[RequirementGapGroup, ...]:
    grouped: dict[tuple[str, str], dict[str, set[str]]] = {}
    for category, records in categories.items():
        for record in records:
            requirement = requirements.get(record.entity_id)
            dimensions = (
                _requirement_dimensions(requirement, issues)
                if requirement is not None
                else {
                    "journey": ("unassigned",),
                    "priority": ("unassigned",),
                    "milestone": ("unassigned",),
                    "release": _release_values(issues[record.entity_id]),
                }
            )
            for dimension, values in dimensions.items():
                for value in values:
                    grouped.setdefault((dimension, value), {}).setdefault(
                        category, set()
                    ).add(record.entity_id)
    dimension_order = {"journey": 0, "priority": 1, "milestone": 2, "release": 3}
    return tuple(
        RequirementGapGroup(
            dimension,
            value,
            tuple(
                RequirementGapGroupCategory(
                    category,
                    tuple(sorted(grouped[(dimension, value)].get(category, set()))),
                )
                for category in REQUIREMENT_GAP_CATEGORIES
            ),
        )
        for dimension, value in sorted(
            grouped, key=lambda key: (dimension_order[key[0]], key[1])
        )
    )


def _linked_visible_issues(
    requirement: Requirement, issues: dict[str, Issue]
) -> tuple[Issue, ...]:
    return tuple(
        issues[target]
        for target in map(str, requirement.relations.implemented_by)
        if target in issues
    )


def _accepted_unplanned(
    governed: tuple[Requirement, ...], issues: dict[str, Issue]
) -> tuple[RequirementGapRecord, ...]:
    return _ordered(
        _record(requirement.id, "no existing implemented-by target")
        for requirement in governed
        if not _linked_visible_issues(requirement, issues)
    )


def _awaiting_verification(
    governed: tuple[Requirement, ...], issues: dict[str, Issue]
) -> tuple[RequirementGapRecord, ...]:
    records = []
    for requirement in governed:
        linked = _linked_visible_issues(requirement, issues)
        if (
            linked
            and len(linked) == len(requirement.relations.implemented_by)
            and all(item.status is IssueStatus.CLOSED for item in linked)
            and requirement.effective_status is not RequirementStatus.VERIFIED
        ):
            records.append(
                _record(requirement.id, "all linked implementation issues are closed")
            )
    return _ordered(records)


def _blocked(
    governed: tuple[Requirement, ...],
    requirements: dict[str, Requirement],
    issues: dict[str, Issue],
) -> tuple[RequirementGapRecord, ...]:
    records = []
    for requirement in governed:
        reasons = _blocked_reasons(requirement, requirements, issues)
        if reasons:
            records.append(_record(requirement.id, *reasons))
    return _ordered(records)


def _broken(
    requirements: tuple[Requirement, ...],
    requirement_ids: set[str],
    issue_ids: set[str],
    milestone_ids: set[str],
    project_ids: set[str],
) -> tuple[RequirementGapRecord, ...]:
    records = []
    for requirement in requirements:
        reasons = _broken_reasons(
            requirement, requirement_ids, issue_ids, milestone_ids, project_ids
        )
        if reasons:
            records.append(_record(requirement.id, *reasons))
    return _ordered(records)


def _is_governed(requirement: Requirement) -> bool:
    return requirement.acceptance_current and requirement.effective_status in {
        RequirementStatus.ACCEPTED,
        RequirementStatus.IN_PROGRESS,
        RequirementStatus.VERIFIED,
    }


@dataclass(frozen=True, slots=True)
class _GapContext:
    requirements: tuple[Requirement, ...]
    issues: tuple[Issue, ...]
    requirement_by_id: dict[str, Requirement]
    issue_by_id: dict[str, Issue]
    requirement_ids: set[str]
    issue_ids: set[str]
    milestone_ids: set[str]
    project_ids: set[str]
    governed: tuple[Requirement, ...]


def _visible_requirements(
    requirements: tuple[Requirement, ...],
) -> tuple[Requirement, ...]:
    return tuple(
        item for item in requirements if item.retention is RetentionState.VISIBLE
    )


def _visible_issues(issues: tuple[Issue, ...]) -> tuple[Issue, ...]:
    return tuple(item for item in issues if item.retention is RetentionState.VISIBLE)


def _context(
    requirements: tuple[Requirement, ...],
    issues: tuple[Issue, ...],
    milestones: tuple[Milestone, ...],
    projects: tuple[Project, ...],
) -> _GapContext:
    visible_requirements = _visible_requirements(requirements)
    visible_issues = _visible_issues(issues)
    requirement_by_id = {str(item.id): item for item in visible_requirements}
    issue_by_id = {str(item.id): item for item in visible_issues}
    return _GapContext(
        visible_requirements,
        visible_issues,
        requirement_by_id,
        issue_by_id,
        {str(item.id) for item in requirements},
        {str(item.id) for item in issues},
        {str(item.id) for item in milestones},
        {str(item.id) for item in projects},
        tuple(item for item in visible_requirements if _is_governed(item)),
    )


def _unjustified(context: _GapContext) -> tuple[RequirementGapRecord, ...]:
    justified_issue_ids = {
        str(target)
        for requirement in context.governed
        for target in requirement.relations.implemented_by
        if str(target) in context.issue_by_id
    }
    return _ordered(
        _record(issue.id, "no accepted requirement or maintenance rationale")
        for issue in context.issues
        if str(issue.id) not in justified_issue_ids
        and not _maintenance_justified(issue)
    )


def _stale(requirements: tuple[Requirement, ...]) -> tuple[RequirementGapRecord, ...]:
    return _ordered(
        _record(item.id, "evidence belongs to an inactive or stale acceptance")
        for item in requirements
        if item.evidence and not _is_governed(item)
    )


def _failed(governed: tuple[Requirement, ...]) -> tuple[RequirementGapRecord, ...]:
    return _ordered(
        _record(item.id, "latest evidence contains fail or incomplete")
        for item in governed
        if {"fail", "incomplete"} & set(item.verification.values())
    )


def calculate_requirement_gaps(
    requirements: tuple[Requirement, ...],
    issues: tuple[Issue, ...],
    milestones: tuple[Milestone, ...],
    projects: tuple[Project, ...],
) -> RequirementGapReport:
    context = _context(requirements, issues, milestones, projects)
    categories = {
        "accepted_unplanned": _accepted_unplanned(
            context.governed, context.issue_by_id
        ),
        "unjustified_work": _unjustified(context),
        "implemented_awaiting_verification": _awaiting_verification(
            context.governed, context.issue_by_id
        ),
        "stale_evidence": _stale(context.requirements),
        "failed_evidence": _failed(context.governed),
        "broken_links": _broken(
            context.requirements,
            context.requirement_ids,
            context.issue_ids,
            context.milestone_ids,
            context.project_ids,
        ),
        "blocked_requirements": _blocked(
            context.governed, context.requirement_by_id, context.issue_by_id
        ),
    }
    return RequirementGapReport(
        **categories,
        groups=_coverage_groups(
            categories, context.requirement_by_id, context.issue_by_id
        ),
    )
