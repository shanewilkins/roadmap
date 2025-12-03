"""Issue domain model."""

import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


def now_utc():
    """Get current UTC datetime with timezone awareness."""
    from ..shared.timezone_utils import now_utc as tz_now_utc

    return tz_now_utc()


class Priority(str, Enum):
    """Issue priority levels."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class IssueType(str, Enum):
    """Issue type categories."""

    FEATURE = "feature"
    BUG = "bug"
    OTHER = "other"


class Status(str, Enum):
    """Issue status values."""

    TODO = "todo"
    IN_PROGRESS = "in-progress"
    BLOCKED = "blocked"
    REVIEW = "review"
    CLOSED = "closed"


class Issue(BaseModel):
    """Issue data model."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    title: str
    priority: Priority = Priority.MEDIUM
    status: Status = Status.TODO
    issue_type: IssueType = IssueType.OTHER
    milestone: str | None = None
    labels: list[str] = Field(default_factory=list)
    github_issue: int | None = None
    created: datetime = Field(default_factory=now_utc)
    updated: datetime = Field(default_factory=now_utc)
    assignee: str | None = None
    content: str = ""  # Markdown content
    estimated_hours: float | None = None  # Estimated time to complete in hours
    due_date: datetime | None = None  # When the issue should be completed
    depends_on: list[str] = Field(
        default_factory=list
    )  # List of issue IDs this depends on
    blocks: list[str] = Field(default_factory=list)  # List of issue IDs this blocks
    actual_start_date: datetime | None = None  # When work actually started
    actual_end_date: datetime | None = None  # When work was completed
    progress_percentage: float | None = None  # Progress from 0.0 to 100.0
    handoff_notes: str | None = None  # Notes for task handoff
    previous_assignee: str | None = None  # Who was previously assigned
    handoff_date: datetime | None = None  # When the task was handed off
    git_branches: list[str] = Field(
        default_factory=list
    )  # Git branches linked to this issue
    git_commits: list[dict[str, Any]] = Field(
        default_factory=list
    )  # Git commits referencing this issue
    completed_date: str | None = None  # ISO string when issue was completed via Git
    file_path: str | None = Field(
        default=None, exclude=True
    )  # Internal: absolute path where issue file is stored

    @property
    def is_backlog(self) -> bool:
        """Check if this issue is in the backlog (no milestone assigned)."""
        return self.milestone is None or self.milestone == ""

    @property
    def milestone_name(self) -> str:
        """Get the milestone name or 'Backlog' if none assigned."""
        return self.milestone if self.milestone else "Backlog"

    @property
    def estimated_time_display(self) -> str:
        """Get a human-readable display of estimated time."""
        if self.estimated_hours is None:
            return "Not estimated"

        if self.estimated_hours < 1:
            minutes = int(self.estimated_hours * 60)
            return f"{minutes}m"
        elif self.estimated_hours < 8:
            return f"{self.estimated_hours:.1f}h"
        else:
            days = self.estimated_hours / 8  # Assuming 8-hour work days
            return f"{days:.1f}d"

    @property
    def is_started(self) -> bool:
        """Check if work has actually started on this issue."""
        return self.actual_start_date is not None

    @property
    def is_completed(self) -> bool:
        """Check if work has been completed on this issue."""
        return self.actual_end_date is not None

    @property
    def progress_display(self) -> str:
        """Get a human-readable display of progress as percentage (0-100%).

        Returns:
            - Empty string for Todo (not yet started)
            - "100%" for Closed
            - Explicit percentage if set
            - "0%" for other statuses (in-progress, blocked, review) when no explicit progress
        """
        if self.progress_percentage is not None:
            return f"{self.progress_percentage:.0f}%"

        # Infer progress from status when not explicitly set
        if self.status == Status.CLOSED:
            return "100%"
        elif self.status == Status.TODO:
            return ""  # Blank for todo - no progress tracking yet
        else:
            # For in-progress, blocked, review - default to 0% if no explicit progress
            return "0%"

    @property
    def actual_duration_hours(self) -> float | None:
        """Calculate actual duration if both start and end dates are set."""
        if self.actual_start_date and self.actual_end_date:
            delta = self.actual_end_date - self.actual_start_date
            return delta.total_seconds() / 3600  # Convert to hours
        return None

    @property
    def is_overdue(self) -> bool:
        """Check if the issue is overdue based on estimates and actual start."""
        if not self.actual_start_date or not self.estimated_hours:
            return False

        if self.actual_end_date:
            # Already completed, check if it took longer than estimated
            actual_hours = self.actual_duration_hours
            return bool(actual_hours and actual_hours > self.estimated_hours)

        # Still in progress, check if it's taking longer than estimated
        elapsed = datetime.now() - self.actual_start_date
        elapsed_hours = elapsed.total_seconds() / 3600
        return elapsed_hours > self.estimated_hours

    @property
    def has_been_handed_off(self) -> bool:
        """Check if this issue has been handed off to another person."""
        return self.previous_assignee is not None and self.handoff_date is not None

    @property
    def handoff_context_summary(self) -> str:
        """Get a summary of handoff context for display."""
        if not self.has_been_handed_off:
            return "No previous handoff"

        if self.handoff_notes:
            return f"From {self.previous_assignee}: {self.handoff_notes[:100]}..."
        else:
            return f"Handed off from {self.previous_assignee}"

    @property
    def filename(self) -> str:
        """Generate filename for this issue."""
        safe_title = "".join(
            c for c in self.title if c.isalnum() or c in (" ", "-", "_")
        ).strip()
        safe_title = safe_title.replace(" ", "-").lower()
        return f"{self.id}-{safe_title}.md"
