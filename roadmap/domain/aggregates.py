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
    actual_start_at: t.Timestamp | None = None
    actual_end_at: t.Timestamp | None = None
    git_branches: tuple[str, ...] = ()
    comments: tuple[t.IssueComment, ...] = ()
    history: tuple[t.IssueEvent, ...] = ()

    def __post_init__(self) -> None:
        _Aggregate.__post_init__(self)
        self.relations.validate_for(self.id)
        if self.estimated_hours is not None and self.estimated_hours <= 0:
            raise InvariantViolation("estimated hours must be positive")
        progress = self.progress_percentage
        if progress is not None and not 0 <= progress <= 100:
            raise InvariantViolation("progress must be between 0 and 100")
        if self.actual_start_at and self.actual_end_at:
            if self.actual_end_at < self.actual_start_at:
                raise InvariantViolation("actual end cannot precede actual start")
        comment_ids = {comment.id for comment in self.comments}
        if len(comment_ids) != len(self.comments):
            raise InvariantViolation("comment IDs must be unique within an issue")
        if any(
            comment.in_reply_to is not None and comment.in_reply_to not in comment_ids
            for comment in self.comments
        ):
            raise InvariantViolation("comment reply target must exist on the issue")

    def rename(self, title: t.Title, at: t.Timestamp) -> "Issue":
        return replace(self, title=title, updated=at)

    def reassign(self, relations: t.IssueRelations, at: t.Timestamp) -> "Issue":
        return replace(self, relations=relations, updated=at)

    def change_status(self, status: t.IssueStatus, at: t.Timestamp) -> "Issue":
        require_transition(self.status, status, ISSUE_TRANSITIONS)
        return replace(self, status=status, updated=at)

    def revise(
        self,
        *,
        at: t.Timestamp,
        title: t.Title,
        content: str,
        priority: t.Priority,
        relations: t.IssueRelations,
        assignee: str | None,
        estimated_hours: float | None,
    ) -> "Issue":
        return replace(
            self,
            title=title,
            content=content,
            priority=priority,
            relations=relations,
            assignee=assignee,
            estimated_hours=estimated_hours,
            updated=at,
        )

    def record_event(
        self, action: str, at: t.Timestamp, reason: str | None = None
    ) -> "Issue":
        event = t.IssueEvent(action, at, reason.strip() if reason else None)
        return replace(self, history=(*self.history, event), updated=at)

    def start(self, at: t.Timestamp, reason: str | None = None) -> "Issue":
        changed = self.change_status(t.IssueStatus.IN_PROGRESS, at)
        changed = replace(changed, actual_start_at=at, progress_percentage=0.0)
        return changed.record_event("started", at, reason)

    def set_progress(self, percentage: float, at: t.Timestamp) -> "Issue":
        if not 0 <= percentage <= 100:
            raise InvariantViolation("progress must be between 0 and 100")
        changed = self
        if percentage == 0 and self.status is not t.IssueStatus.TODO:
            changed = self.change_status(t.IssueStatus.TODO, at)
        elif 0 < percentage < 100 and self.status in {
            t.IssueStatus.TODO,
            t.IssueStatus.CLOSED,
        }:
            changed = self.change_status(t.IssueStatus.IN_PROGRESS, at)
        return replace(changed, progress_percentage=percentage, updated=at)

    def close(
        self, at: t.Timestamp, completed_at: t.Timestamp | None, reason: str | None
    ) -> "Issue":
        changed = self.change_status(t.IssueStatus.CLOSED, at)
        changed = replace(
            changed,
            progress_percentage=100.0,
            actual_end_at=completed_at,
        )
        return changed.record_event("closed", at, reason)

    def add_comment(self, comment: t.IssueComment, at: t.Timestamp) -> "Issue":
        return replace(self, comments=(*self.comments, comment), updated=at)

    def link_branch(self, branch: str, at: t.Timestamp) -> "Issue":
        value = branch.strip()
        if not value:
            raise InvariantViolation("branch reference cannot be empty")
        branches = self.git_branches
        if value not in branches:
            branches = (*branches, value)
        return replace(self, git_branches=branches, updated=at)


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

    def revise(
        self,
        *,
        at: t.Timestamp,
        name: t.Name,
        headline: str,
        content: str,
        status: t.MilestoneStatus,
        relation: t.MilestoneRelation,
        due_at: t.Timestamp | None,
    ) -> "Milestone":
        changed = replace(
            self,
            name=name,
            headline=headline,
            content=content,
            relation=relation,
            due_at=due_at,
            updated=at,
        )
        return (
            changed.change_status(status, at) if status is not self.status else changed
        )


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
    start_at: t.Timestamp | None = None
    target_end_at: t.Timestamp | None = None
    actual_end_at: t.Timestamp | None = None
    actual_hours: float | None = None
    repository_url: str | None = None

    def __post_init__(self) -> None:
        _Aggregate.__post_init__(self)
        if self.estimated_hours is not None and self.estimated_hours <= 0:
            raise InvariantViolation("estimated hours must be positive")
        if self.actual_hours is not None and self.actual_hours < 0:
            raise InvariantViolation("actual hours cannot be negative")
        if self.start_at and self.target_end_at and self.target_end_at < self.start_at:
            raise InvariantViolation("target end cannot precede project start")

    def rename(self, name: t.Name, at: t.Timestamp) -> "Project":
        return replace(self, name=name, updated=at)

    def reassign(self, relations: t.ProjectRelations, at: t.Timestamp) -> "Project":
        return replace(self, relations=relations, updated=at)

    def change_status(self, status: t.ProjectStatus, at: t.Timestamp) -> "Project":
        require_transition(self.status, status, PROJECT_TRANSITIONS)
        return replace(self, status=status, updated=at)

    def revise(
        self,
        *,
        at: t.Timestamp,
        name: t.Name,
        headline: str,
        content: str,
        status: t.ProjectStatus,
        priority: t.Priority,
        owner: str | None,
        estimated_hours: float | None,
        repository_url: str | None,
    ) -> "Project":
        changed = replace(
            self,
            name=name,
            headline=headline,
            content=content,
            priority=priority,
            owner=owner,
            estimated_hours=estimated_hours,
            repository_url=repository_url,
            updated=at,
        )
        return (
            changed.change_status(status, at) if status is not self.status else changed
        )
