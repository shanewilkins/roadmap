"""Framework-neutral request and response data."""

from dataclasses import dataclass
from enum import StrEnum

from roadmap.domain.aggregates import Issue
from roadmap.domain.types import (
    EntityId,
    IssueRelations,
    IssueType,
    Priority,
    Timestamp,
    Title,
)


class IssueScope(StrEnum):
    """Lifecycle population selected by an issue query."""

    VISIBLE = "visible"
    CLOSED = "closed"
    ARCHIVED = "archived"
    ALL = "all"


@dataclass(frozen=True, slots=True)
class IssueCommentView:
    id: int
    author: str
    body: str
    created_at: Timestamp
    updated_at: Timestamp
    in_reply_to: int | None = None


@dataclass(frozen=True, slots=True)
class IssueQueryRecord:
    issue: Issue
    comments: tuple[IssueCommentView, ...] = ()
    actual_end_at: Timestamp | None = None


@dataclass(frozen=True, slots=True)
class IssueListQuery:
    scope: IssueScope = IssueScope.VISIBLE
    milestone: EntityId | None = None
    backlog: bool = False
    next_milestone: bool = False
    assignee: str | None = None
    current_assignee: bool = False
    open_only: bool = False
    blocked_only: bool = False
    status: str | None = None
    priority: str | None = None
    issue_type: str | None = None
    overdue: bool = False
    search: str | None = None


@dataclass(frozen=True, slots=True)
class IssueListResult:
    records: tuple[IssueQueryRecord, ...]
    description: str
    next_milestone_missing: bool = False


@dataclass(frozen=True, slots=True)
class IssueDraft:
    title: Title
    priority: Priority = Priority.MEDIUM
    issue_type: IssueType = IssueType.OTHER
    relations: IssueRelations = IssueRelations()
    headline: str = ""
    content: str = ""


@dataclass(frozen=True, slots=True)
class MutationReceipt:
    entity_id: EntityId
    updated: Timestamp
    projection_stale: bool = False


@dataclass(frozen=True, slots=True)
class GitSnapshot:
    branch: str | None
    head: str | None
    changed_paths: tuple[str, ...]
