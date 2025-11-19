"""Milestone domain model."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

from .issue import Status

# Import timezone utilities with circular import protection
try:
    from ..shared.timezone_utils import now_utc
except ImportError:
    # Fallback during module loading
    def now_utc():
        return datetime.now()


class MilestoneStatus(str, Enum):
    """Milestone status values."""

    OPEN = "open"
    CLOSED = "closed"


class RiskLevel(str, Enum):
    """Risk level values for projects and milestones."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Milestone(BaseModel):
    """Milestone data model."""

    name: str
    description: str = ""
    due_date: datetime | None = None
    status: MilestoneStatus = MilestoneStatus.OPEN
    github_milestone: int | None = None
    created: datetime = Field(default_factory=now_utc)
    updated: datetime = Field(default_factory=now_utc)
    content: str = ""  # Markdown content

    # Automatic progress tracking fields
    calculated_progress: float | None = None  # Auto-calculated from issues
    last_progress_update: datetime | None = None
    completion_velocity: float | None = None  # Issues/week
    risk_level: RiskLevel = RiskLevel.LOW
    actual_start_date: datetime | None = None
    actual_end_date: datetime | None = None

    def get_issues(self, all_issues):
        """Get all issues assigned to this milestone.

        Args:
            all_issues: List of Issue objects to filter

        Returns:
            List of issues assigned to this milestone
        """
        return [issue for issue in all_issues if issue.milestone == self.name]

    def get_issue_count(self, all_issues):
        """Get the count of issues assigned to this milestone."""
        return len(self.get_issues(all_issues))

    def get_completion_percentage(
        self, all_issues, method: str = "effort_weighted"
    ) -> float:
        """Get the completion percentage of this milestone.

        Args:
            all_issues: List of all issues in the system
            method: 'effort_weighted' or 'count_based'

        Returns:
            Completion percentage from 0.0 to 100.0
        """
        milestone_issues = self.get_issues(all_issues)
        if not milestone_issues:
            return 0.0

        if method == "count_based":
            # Simple count-based calculation
            completed_issues = [
                issue for issue in milestone_issues if issue.status == Status.DONE
            ]
            return (len(completed_issues) / len(milestone_issues)) * 100.0
        else:
            # Effort-weighted calculation (preferred)
            total_effort = 0.0
            completed_effort = 0.0

            for issue in milestone_issues:
                effort = (
                    issue.estimated_hours or 1.0
                )  # Default to 1 hour if not estimated
                total_effort += effort

                if issue.status == Status.DONE:
                    completed_effort += effort
                elif issue.progress_percentage is not None:
                    # Partial completion based on progress percentage
                    completed_effort += effort * (issue.progress_percentage / 100.0)

            return (
                (completed_effort / total_effort) * 100.0 if total_effort > 0 else 0.0
            )

    def get_total_estimated_hours(self, all_issues) -> float:
        """Get the total estimated hours for all issues in this milestone."""
        milestone_issues = self.get_issues(all_issues)
        total_hours = 0.0
        for issue in milestone_issues:
            if issue.estimated_hours is not None:
                total_hours += issue.estimated_hours
        return total_hours

    def get_remaining_estimated_hours(self, all_issues) -> float:
        """Get the remaining estimated hours for incomplete issues in this milestone."""
        milestone_issues = self.get_issues(all_issues)
        remaining_hours = 0.0
        for issue in milestone_issues:
            if issue.status != Status.DONE and issue.estimated_hours is not None:
                remaining_hours += issue.estimated_hours
        return remaining_hours

    def get_estimated_time_display(self, all_issues) -> str:
        """Get a human-readable display of total estimated time."""
        total_hours = self.get_total_estimated_hours(all_issues)
        if total_hours == 0:
            return "Not estimated"

        if total_hours < 8:
            return f"{total_hours:.1f}h"
        else:
            days = total_hours / 8  # Assuming 8-hour work days
            return f"{days:.1f}d"

    def update_automatic_fields(
        self, all_issues, method: str = "effort_weighted"
    ) -> None:
        """Update all automatic progress tracking fields.

        Args:
            all_issues: List of all issues in the system
            method: Calculation method ('effort_weighted' or 'count_based')
        """
        self.calculated_progress = self.get_completion_percentage(all_issues, method)
        self.last_progress_update = datetime.now()
        self.updated = datetime.now()

        # Update status based on progress
        if self.calculated_progress >= 100.0:
            self.status = MilestoneStatus.CLOSED
            if not self.actual_end_date:
                self.actual_end_date = datetime.now()
        elif self.calculated_progress > 0:
            if self.status == MilestoneStatus.OPEN and not self.actual_start_date:
                self.actual_start_date = datetime.now()

    @property
    def filename(self) -> str:
        """Generate filename for this milestone."""
        safe_name = "".join(
            c for c in self.name if c.isalnum() or c in (" ", "-", "_")
        ).strip()
        safe_name = safe_name.replace(" ", "-").lower()
        return f"{safe_name}.md"
