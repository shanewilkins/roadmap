"""Data models for roadmap CLI."""

import uuid
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field

# Import security functions - using a try/except to avoid circular imports
try:
    from .security import create_secure_file, validate_path
except ImportError:
    # Fallback for when security module is not available
    def validate_path(path):
        pass

    def create_secure_file(path, mode="w", **kwargs):
        return open(path, mode, **kwargs)


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
    DONE = "done"


class MilestoneStatus(str, Enum):
    """Milestone status values."""

    OPEN = "open"
    CLOSED = "closed"


class Issue(BaseModel):
    """Issue data model."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    title: str
    priority: Priority = Priority.MEDIUM
    status: Status = Status.TODO
    issue_type: IssueType = IssueType.OTHER
    milestone: Optional[str] = None
    labels: List[str] = Field(default_factory=list)
    github_issue: Optional[int] = None
    created: datetime = Field(default_factory=datetime.now)
    updated: datetime = Field(default_factory=datetime.now)
    assignee: Optional[str] = None
    content: str = ""  # Markdown content
    estimated_hours: Optional[float] = None  # Estimated time to complete in hours
    depends_on: List[str] = Field(
        default_factory=list
    )  # List of issue IDs this depends on
    blocks: List[str] = Field(default_factory=list)  # List of issue IDs this blocks
    actual_start_date: Optional[datetime] = None  # When work actually started
    actual_end_date: Optional[datetime] = None  # When work was completed
    progress_percentage: Optional[float] = None  # Progress from 0.0 to 100.0
    handoff_notes: Optional[str] = None  # Notes for task handoff
    previous_assignee: Optional[str] = None  # Who was previously assigned
    handoff_date: Optional[datetime] = None  # When the task was handed off
    git_branches: List[str] = Field(
        default_factory=list
    )  # Git branches linked to this issue
    git_commits: List[Dict[str, Any]] = Field(
        default_factory=list
    )  # Git commits referencing this issue
    completed_date: Optional[str] = None  # ISO string when issue was completed via Git

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
        """Get a human-readable display of progress."""
        if self.progress_percentage is None:
            if self.status == Status.DONE:
                return "100%"
            elif self.status == Status.IN_PROGRESS:
                return "In Progress"
            else:
                return "Not Started"
        return f"{self.progress_percentage:.0f}%"

    @property
    def actual_duration_hours(self) -> Optional[float]:
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
            return actual_hours and actual_hours > self.estimated_hours

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


class Milestone(BaseModel):
    """Milestone data model."""

    name: str
    description: str = ""
    due_date: Optional[datetime] = None
    status: MilestoneStatus = MilestoneStatus.OPEN
    github_milestone: Optional[int] = None
    created: datetime = Field(default_factory=datetime.now)
    updated: datetime = Field(default_factory=datetime.now)
    content: str = ""  # Markdown content

    def get_issues(self, all_issues: List["Issue"]) -> List["Issue"]:
        """Get all issues assigned to this milestone."""
        return [issue for issue in all_issues if issue.milestone == self.name]

    def get_issue_count(self, all_issues: List["Issue"]) -> int:
        """Get the count of issues assigned to this milestone."""
        return len(self.get_issues(all_issues))

    def get_completion_percentage(self, all_issues: List["Issue"]) -> float:
        """Get the completion percentage of this milestone."""
        milestone_issues = self.get_issues(all_issues)
        if not milestone_issues:
            return 0.0

        completed_issues = [
            issue for issue in milestone_issues if issue.status == Status.DONE
        ]
        return (len(completed_issues) / len(milestone_issues)) * 100.0

    def get_total_estimated_hours(self, all_issues: List["Issue"]) -> float:
        """Get the total estimated hours for all issues in this milestone."""
        milestone_issues = self.get_issues(all_issues)
        total_hours = 0.0
        for issue in milestone_issues:
            if issue.estimated_hours is not None:
                total_hours += issue.estimated_hours
        return total_hours

    def get_remaining_estimated_hours(self, all_issues: List["Issue"]) -> float:
        """Get the remaining estimated hours for incomplete issues in this milestone."""
        milestone_issues = self.get_issues(all_issues)
        remaining_hours = 0.0
        for issue in milestone_issues:
            if issue.status != Status.DONE and issue.estimated_hours is not None:
                remaining_hours += issue.estimated_hours
        return remaining_hours

    def get_estimated_time_display(self, all_issues: List["Issue"]) -> str:
        """Get a human-readable display of total estimated time."""
        total_hours = self.get_total_estimated_hours(all_issues)
        if total_hours == 0:
            return "Not estimated"

        if total_hours < 8:
            return f"{total_hours:.1f}h"
        else:
            days = total_hours / 8  # Assuming 8-hour work days
            return f"{days:.1f}d"

    @property
    def filename(self) -> str:
        """Generate filename for this milestone."""
        safe_name = "".join(
            c for c in self.name if c.isalnum() or c in (" ", "-", "_")
        ).strip()
        safe_name = safe_name.replace(" ", "-").lower()
        return f"{safe_name}.md"


class Comment(BaseModel):
    """Comment data model for issues."""

    id: int  # GitHub comment ID
    issue_id: str  # Local issue ID or GitHub issue number
    author: str  # GitHub username
    body: str  # Comment content (markdown)
    created_at: datetime
    updated_at: datetime
    github_url: Optional[str] = None  # GitHub comment URL

    def __str__(self) -> str:
        """String representation."""
        return (
            f"Comment by {self.author} on {self.created_at.strftime('%Y-%m-%d %H:%M')}"
        )


class RoadmapConfig(BaseModel):
    """Configuration model for roadmap."""

    github: dict = Field(default_factory=dict)
    defaults: dict = Field(default_factory=lambda: {"auto_branch": False, "branch_name_template": "feature/{id}-{slug}"})
    milestones: dict = Field(default_factory=dict)
    sync: dict = Field(default_factory=dict)
    display: dict = Field(default_factory=dict)

    @classmethod
    def load_from_file(cls, config_path: Path) -> "RoadmapConfig":
        """Load configuration from YAML file."""
        import yaml

        if not config_path.exists():
            return cls()

        # Validate the configuration file path for security
        validate_path(str(config_path))

        with open(config_path, "r") as f:
            data = yaml.safe_load(f) or {}

        return cls(**data)

    def save_to_file(self, config_path: Path) -> None:
        """Save configuration to YAML file."""
        import yaml

        config_path.parent.mkdir(parents=True, exist_ok=True)
        with create_secure_file(config_path, "w") as f:
            yaml.dump(self.model_dump(), f, default_flow_style=False)
