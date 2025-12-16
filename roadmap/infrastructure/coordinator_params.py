"""Coordinator layer parameter dataclasses.

Consolidates coordinator method parameters into well-structured dataclasses
for improved API consistency and reduced parameter passing complexity.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from roadmap.core.domain import IssueType, Priority


@dataclass
class IssueCreateParams:
    """Parameters for creating a new issue through IssueCoordinator."""

    title: str
    priority: Priority = Priority.MEDIUM
    issue_type: IssueType = IssueType.OTHER
    milestone: str | None = None
    labels: list[str] | None = None
    assignee: str | None = None
    estimated_hours: float | None = None
    depends_on: list[str] | None = None
    blocks: list[str] | None = None


@dataclass
class IssueListParams:
    """Parameters for listing issues through IssueCoordinator."""

    milestone: str | None = None
    status: str | None = None
    priority: Priority | None = None
    issue_type: IssueType | None = None
    assignee: str | None = None


@dataclass
class IssueUpdateParams:
    """Parameters for updating an issue through IssueCoordinator."""

    issue_id: str
    updates: dict[str, Any] = field(default_factory=dict)


@dataclass
class MilestoneCreateParams:
    """Parameters for creating a new milestone through MilestoneCoordinator."""

    name: str
    description: str = ""
    due_date: datetime | None = None


@dataclass
class MilestoneUpdateParams:
    """Parameters for updating a milestone through MilestoneCoordinator."""

    name: str
    description: str | None = None
    due_date: datetime | None = None
    clear_due_date: bool = False
    status: str | None = None


@dataclass
class ProjectCreateParams:
    """Parameters for creating a new project through ProjectCoordinator."""

    name: str
    description: str = ""
    milestones: list[str] | None = None


@dataclass
class ProjectUpdateParams:
    """Parameters for updating a project through ProjectCoordinator."""

    project_id: str
    updates: dict[str, Any] = field(default_factory=dict)
