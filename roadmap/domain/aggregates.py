"""Pure roadmap aggregates."""

from dataclasses import dataclass, field, replace
from typing import Self

from . import types as t
from .failures import InvariantViolation
from .transitions import (
    ISSUE_TRANSITIONS,
    MILESTONE_TRANSITIONS,
    PROJECT_TRANSITIONS,
    RETENTION_TRANSITIONS,
    require_transition,
)


@dataclass(frozen=True, slots=True)
class _Aggregate:
    id: t.EntityId
    created: t.Timestamp
    updated: t.Timestamp
    retention: t.RetentionState = t.RetentionState.VISIBLE

    def __post_init__(self) -> None:
        if self.updated < self.created:
            raise InvariantViolation(
                "updated timestamp cannot precede created timestamp"
            )

    def change_retention(self, retention: t.RetentionState, at: t.Timestamp) -> Self:
        require_transition(self.retention, retention, RETENTION_TRANSITIONS)
        return replace(self, retention=retention, updated=at)


@dataclass(frozen=True, slots=True)
class Issue(_Aggregate):
    title: t.Title = field(kw_only=True)
    headline: str = ""
    content: str = ""
    priority: t.Priority = t.Priority.MEDIUM
    status: t.IssueStatus = t.IssueStatus.TODO
    issue_type: t.IssueType = t.IssueType.OTHER
    relations: t.IssueRelations = field(default_factory=t.IssueRelations)
    labels: tuple[str, ...] = ()
    assignee: str | None = None
    estimated_hours: float | None = None
    due_at: t.Timestamp | None = None
    progress_percentage: float | None = None

    def __post_init__(self) -> None:
        _Aggregate.__post_init__(self)
        self.relations.validate_for(self.id)
        if self.estimated_hours is not None and self.estimated_hours <= 0:
            raise InvariantViolation("estimated hours must be positive")
        progress = self.progress_percentage
        if progress is not None and not 0 <= progress <= 100:
            raise InvariantViolation("progress must be between 0 and 100")

    def rename(self, title: t.Title, at: t.Timestamp) -> "Issue":
        return replace(self, title=title, updated=at)

    def reassign(self, relations: t.IssueRelations, at: t.Timestamp) -> "Issue":
        return replace(self, relations=relations, updated=at)

    def change_status(self, status: t.IssueStatus, at: t.Timestamp) -> "Issue":
        require_transition(self.status, status, ISSUE_TRANSITIONS)
        return replace(self, status=status, updated=at)


@dataclass(frozen=True, slots=True)
class Milestone(_Aggregate):
    name: t.Name = field(kw_only=True)
    headline: str = ""
    content: str = ""
    status: t.MilestoneStatus = t.MilestoneStatus.OPEN
    relation: t.MilestoneRelation = field(default_factory=t.MilestoneRelation)
    due_at: t.Timestamp | None = None

    def __post_init__(self) -> None:
        _Aggregate.__post_init__(self)

    def rename(self, name: t.Name, at: t.Timestamp) -> "Milestone":
        return replace(self, name=name, updated=at)

    def reassign(self, relation: t.MilestoneRelation, at: t.Timestamp) -> "Milestone":
        return replace(self, relation=relation, updated=at)

    def change_status(self, status: t.MilestoneStatus, at: t.Timestamp) -> "Milestone":
        require_transition(self.status, status, MILESTONE_TRANSITIONS)
        return replace(self, status=status, updated=at)


@dataclass(frozen=True, slots=True)
class Project(_Aggregate):
    name: t.Name = field(kw_only=True)
    headline: str = ""
    content: str = ""
    status: t.ProjectStatus = t.ProjectStatus.PLANNING
    priority: t.Priority = t.Priority.MEDIUM
    relations: t.ProjectRelations = field(default_factory=t.ProjectRelations)
    owner: str | None = None
    estimated_hours: float | None = None

    def __post_init__(self) -> None:
        _Aggregate.__post_init__(self)
        if self.estimated_hours is not None and self.estimated_hours <= 0:
            raise InvariantViolation("estimated hours must be positive")

    def rename(self, name: t.Name, at: t.Timestamp) -> "Project":
        return replace(self, name=name, updated=at)

    def reassign(self, relations: t.ProjectRelations, at: t.Timestamp) -> "Project":
        return replace(self, relations=relations, updated=at)

    def change_status(self, status: t.ProjectStatus, at: t.Timestamp) -> "Project":
        require_transition(self.status, status, PROJECT_TRANSITIONS)
        return replace(self, status=status, updated=at)
