"""Explicit, exhaustive workflow and retention transition policy."""

from collections.abc import Mapping
from enum import StrEnum

from .failures import InvalidTransition
from .types import IssueStatus, MilestoneStatus, ProjectStatus, RetentionState

ISSUE_TRANSITIONS = {
    IssueStatus.TODO: frozenset(
        {IssueStatus.IN_PROGRESS, IssueStatus.BLOCKED, IssueStatus.CLOSED}
    ),
    IssueStatus.IN_PROGRESS: frozenset(
        {IssueStatus.TODO, IssueStatus.BLOCKED, IssueStatus.REVIEW, IssueStatus.CLOSED}
    ),
    IssueStatus.BLOCKED: frozenset(
        {IssueStatus.TODO, IssueStatus.IN_PROGRESS, IssueStatus.CLOSED}
    ),
    IssueStatus.REVIEW: frozenset(
        {IssueStatus.IN_PROGRESS, IssueStatus.BLOCKED, IssueStatus.CLOSED}
    ),
    IssueStatus.CLOSED: frozenset({IssueStatus.TODO, IssueStatus.IN_PROGRESS}),
}
MILESTONE_TRANSITIONS = {
    MilestoneStatus.OPEN: frozenset({MilestoneStatus.CLOSED}),
    MilestoneStatus.CLOSED: frozenset({MilestoneStatus.OPEN}),
}
PROJECT_TRANSITIONS = {
    ProjectStatus.PLANNING: frozenset(
        {ProjectStatus.ACTIVE, ProjectStatus.ON_HOLD, ProjectStatus.CANCELLED}
    ),
    ProjectStatus.ACTIVE: frozenset(
        {ProjectStatus.ON_HOLD, ProjectStatus.COMPLETED, ProjectStatus.CANCELLED}
    ),
    ProjectStatus.ON_HOLD: frozenset({ProjectStatus.ACTIVE, ProjectStatus.CANCELLED}),
    ProjectStatus.COMPLETED: frozenset({ProjectStatus.ACTIVE}),
    ProjectStatus.CANCELLED: frozenset({ProjectStatus.PLANNING}),
}
RETENTION_TRANSITIONS = {
    RetentionState.VISIBLE: frozenset({RetentionState.ARCHIVED}),
    RetentionState.ARCHIVED: frozenset({RetentionState.VISIBLE, RetentionState.PURGED}),
    RetentionState.PURGED: frozenset[RetentionState](),
}


def require_transition[S: StrEnum](
    current: S, target: S, table: Mapping[S, frozenset[S]]
) -> None:
    if current != target and target not in table[current]:
        raise InvalidTransition(f"{current.value} -> {target.value} is not permitted")
