"""Service layer dataclasses for internal parameter passing.

These models decouple service method signatures from their implementations.
They're used internally by services (not exposed to CLI).

Benefits:
- Services have clean, stable signatures
- Easy to add new fields without breaking callers
- Self-documenting business logic
- Better testability (can mock as single object)
"""

from dataclasses import dataclass, field
from datetime import datetime


# Sentinel value to distinguish "not provided" from "None"
class _NotProvided:
    """Sentinel value indicating a field was not provided in an update."""

    def __repr__(self):
        return "<NOT_PROVIDED>"


NOT_PROVIDED = _NotProvided()


@dataclass
class IssueCreateServiceParams:
    """Parameters for creating an issue (service layer)."""

    title: str
    priority: str | None = None
    status: str = "todo"
    issue_type: str | None = None
    milestone: str | None = None
    assignee: str | None = None
    content: str | None = None
    estimate: float | None = None
    labels: list[str] = field(default_factory=list)
    depends_on: list[str] = field(default_factory=list)
    blocks: list[str] = field(default_factory=list)


@dataclass
class IssueUpdateServiceParams:
    """Parameters for updating an issue (service layer)."""

    issue_id: str
    title: str | None | _NotProvided = NOT_PROVIDED
    priority: str | None | _NotProvided = NOT_PROVIDED
    status: str | None | _NotProvided = NOT_PROVIDED
    assignee: str | None | _NotProvided = NOT_PROVIDED
    milestone: str | None | _NotProvided = NOT_PROVIDED
    content: str | None | _NotProvided = NOT_PROVIDED
    estimate: float | None | _NotProvided = NOT_PROVIDED
    reason: str | None | _NotProvided = NOT_PROVIDED


@dataclass
class IssueQueryParams:
    """Parameters for querying/filtering issues (service layer)."""

    status: str | None = None
    priority: str | None = None
    issue_type: str | None = None
    assignee: str | None = None
    milestone: str | None = None
    overdue: bool = False
    blocked: bool = False
    unassigned: bool = False
    limit: int | None = None
    offset: int = 0


@dataclass
class MilestoneCreateServiceParams:
    """Parameters for creating a milestone (service layer)."""

    name: str
    content: str = ""
    due_date: datetime | None = None


@dataclass
class MilestoneUpdateServiceParams:
    """Parameters for updating a milestone (service layer)."""

    name: str
    content: str | None = None
    due_date: datetime | None = None
    clear_due_date: bool = False
    status: str | None = None


@dataclass
class ProjectCreateServiceParams:
    """Parameters for creating a project (service layer)."""

    name: str
    content: str = ""
    milestones: list | None = None


@dataclass
class ProjectUpdateServiceParams:
    """Parameters for updating a project (service layer)."""

    project_id: str
    name: str | None = None
    content: str | None = None
    milestones: list | None = None
    status: str | None = None
