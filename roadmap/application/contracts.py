"""Framework-neutral request and response data."""

from dataclasses import dataclass
from enum import StrEnum

from roadmap.domain.aggregates import Issue, Milestone, Project
from roadmap.domain.types import (
    EntityId,
    IssueRelations,
    IssueType,
    MilestoneStatus,
    Name,
    Priority,
    ProjectStatus,
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
    milestone_name: str | None = None


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
class IssueCreateCommand:
    title: Title
    priority: Priority = Priority.MEDIUM
    issue_type: IssueType = IssueType.OTHER
    milestone_id: EntityId | None = None
    assignee: str | None = None
    labels: tuple[str, ...] = ()
    estimated_hours: float | None = None
    depends_on: tuple[EntityId, ...] = ()
    blocks: tuple[EntityId, ...] = ()
    content: str = ""


@dataclass(frozen=True, slots=True)
class IssueUpdateCommand:
    issue_id: EntityId
    title: Title | None = None
    priority: Priority | None = None
    status: str | None = None
    assignee: str | None = None
    milestone_id: EntityId | None = None
    content: str | None = None
    estimated_hours: float | None = None
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class IssueMutationResult:
    issue: Issue
    projection_stale: bool = False


@dataclass(frozen=True, slots=True)
class IssueBatchResult:
    issues: tuple[Issue, ...]
    projection_stale: bool = False


@dataclass(frozen=True, slots=True)
class GitSnapshot:
    branch: str | None
    head: str | None
    changed_paths: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ProjectCreateCommand:
    name: Name
    content: str = ""
    repository_url: str | None = None


@dataclass(frozen=True, slots=True)
class ProjectUpdateCommand:
    project_id: EntityId
    name: Name | None = None
    content: str | None = None
    repository_url: str | None = None
    status: ProjectStatus | None = None
    priority: Priority | None = None
    owner: str | None = None
    estimated_hours: float | None = None


@dataclass(frozen=True, slots=True)
class MilestoneCreateCommand:
    name: Name
    content: str = ""
    due_at: Timestamp | None = None
    project_id: EntityId | None = None


@dataclass(frozen=True, slots=True)
class MilestoneUpdateCommand:
    milestone_id: EntityId
    name: Name | None = None
    content: str | None = None
    due_at: Timestamp | None = None
    status: MilestoneStatus | None = None
    project_id: EntityId | None = None


@dataclass(frozen=True, slots=True)
class MilestoneSummary:
    milestone: Milestone
    issue_count: int
    closed_count: int
    estimated_hours: float
    remaining_hours: float
    progress: float


@dataclass(frozen=True, slots=True)
class ProjectSummary:
    project: Project
    milestone_count: int
    issue_count: int
    closed_count: int
    estimated_hours: float
    remaining_hours: float
    progress: float


@dataclass(frozen=True, slots=True)
class PlanningSnapshot:
    projects: tuple[ProjectSummary, ...]
    milestones: tuple[MilestoneSummary, ...]
    issues: tuple[Issue, ...]


@dataclass(frozen=True, slots=True)
class PlanningMutationResult:
    aggregate: Project | Milestone | Issue
    projection_stale: bool = False


@dataclass(frozen=True, slots=True)
class PlanningBatchResult:
    aggregates: tuple[Project | Milestone, ...]
    projection_stale: bool = False


@dataclass(frozen=True, slots=True)
class DailySummary:
    current_user: str
    milestone: MilestoneSummary
    in_progress: tuple[Issue, ...]
    overdue: tuple[Issue, ...]
    blocked: tuple[Issue, ...]
    up_next: tuple[Issue, ...]
    completed_today: tuple[Issue, ...]

    @property
    def has_issues(self) -> bool:
        return any(
            (
                self.in_progress,
                self.overdue,
                self.blocked,
                self.up_next,
                self.completed_today,
            )
        )


@dataclass(frozen=True, slots=True)
class CriticalPathNode:
    issue_id: EntityId
    issue_title: str
    duration_hours: float
    dependencies: tuple[EntityId, ...]
    slack_time: float = 0.0
    is_critical: bool = True


@dataclass(frozen=True, slots=True)
class CriticalPathResult:
    critical_path: tuple[CriticalPathNode, ...]
    total_duration: float
    critical_issue_ids: tuple[EntityId, ...]
    blocking_issues: tuple[tuple[EntityId, tuple[EntityId, ...]], ...]
    project_end_at: Timestamp | None = None
