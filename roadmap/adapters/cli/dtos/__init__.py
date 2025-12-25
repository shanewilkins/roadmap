"""CLI Data Transfer Objects (DTOs).

This module provides lightweight data transfer objects for the CLI layer.
DTOs decouple the CLI presentation layer from domain models, enabling:
- Selective field exposure (hide implementation details)
- Type conversion to CLI-friendly formats
- Easier testing with mocks
- Cleaner separation of concerns
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class BaseDTO:
    """Base class for all DTOs with common functionality."""

    @classmethod
    def from_dict(cls, data: dict):
        """Create DTO from dictionary (flexible initialization)."""
        # Filter to only include known fields
        fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in fields}
        return cls(**filtered)


@dataclass
class IssueDTO(BaseDTO):
    """CLI-level issue representation for presentation and commands.

    This DTO provides a CLI-friendly view of issues, converting domain enums
    to strings and hiding internal implementation details.

    Attributes:
        id: Unique issue identifier
        title: Issue title/summary
        priority: Priority level (string, not enum)
        status: Current status (string, not enum)
        issue_type: Type of issue (string, not enum)
        assignee: Assigned user, if any
        milestone: Associated milestone name, if any
        due_date: When issue should be completed
        estimated_hours: Estimated time in hours
        actual_end_date: When issue was completed
        progress_percentage: Completion percentage (0-100)
        created: When issue was created
        updated: Last update time
    """

    id: str
    title: str
    priority: str  # String, not enum (e.g., "high", "medium")
    status: str  # String, not enum (e.g., "todo", "in_progress")
    issue_type: str = "other"  # String, not enum
    assignee: str | None = None
    milestone: str | None = None
    due_date: datetime | None = None
    estimated_hours: float | None = None
    actual_end_date: datetime | None = None
    progress_percentage: float | None = None
    created: datetime | None = None
    updated: datetime | None = None
    # Extended fields for detailed views
    content: str | None = None
    labels: list[str] = field(default_factory=list)
    github_issue: str | None = None


@dataclass
class MilestoneDTO(BaseDTO):
    """CLI-level milestone representation.

    Attributes:
        id: Unique milestone identifier (usually name)
        name: Milestone name
        status: Status (string, not enum)
        due_date: Target completion date
        description: Milestone description
        progress_percentage: Overall completion percentage
        issue_count: Number of associated issues
        completed_count: Number of completed issues
    """

    id: str
    name: str
    status: str  # String, not enum
    due_date: datetime | None = None
    description: str = ""
    progress_percentage: float | None = None
    issue_count: int = 0
    completed_count: int = 0
    created: datetime | None = None
    updated: datetime | None = None


@dataclass
class ProjectDTO(BaseDTO):
    """CLI-level project representation.

    Attributes:
        id: Unique project identifier
        name: Project name
        status: Status (string, not enum)
        description: Project description
        owner: Project owner/creator
        target_end_date: Target completion date
        actual_end_date: Actual completion date
        milestone_count: Number of milestones
        issue_count: Total number of issues
    """

    id: str
    name: str
    status: str  # String, not enum
    description: str = ""
    owner: str | None = None
    target_end_date: datetime | None = None
    actual_end_date: datetime | None = None
    milestone_count: int = 0
    issue_count: int = 0
    created: datetime | None = None
    updated: datetime | None = None


__all__ = [
    "BaseDTO",
    "IssueDTO",
    "MilestoneDTO",
    "ProjectDTO",
]
