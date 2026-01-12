"""Issue domain model."""

import uuid
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field, model_validator

from roadmap.common.constants import IssueType, Priority, Status
from roadmap.core.domain.comment import Comment


def now_utc():
    """Get current UTC datetime with timezone awareness."""
    from roadmap.common.timezone_utils import now_utc as tz_now_utc

    return tz_now_utc()


class Issue(BaseModel):
    """Issue data model."""

    model_config = {"ser_json_timedelta": "float"}

    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    title: str
    headline: str = ""  # Short summary for list views
    priority: Priority = Priority.MEDIUM
    status: Status = Status.TODO
    issue_type: IssueType = IssueType.OTHER
    milestone: str | None = None
    labels: list[str] = Field(default_factory=list)
    remote_ids: dict[str, str | int] = Field(
        default_factory=dict,
        description="Remote issue IDs keyed by backend name (e.g., {'github': 42, 'gitlab': 123})",
    )
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
    comments: list[Comment] = Field(
        default_factory=list
    )  # Comments on this issue for discussion
    file_path: str | None = Field(
        default=None, exclude=True
    )  # Internal: absolute path where issue file is stored
    github_sync_metadata: dict[str, Any] | None = Field(
        default=None, exclude=True
    )  # Internal: sync metadata tracking for GitHub integration

    @model_validator(mode="before")
    @classmethod
    def migrate_github_issue_to_remote_ids(cls, data: Any) -> Any:
        """Migrate legacy github_issue field to remote_ids dict.

        Handles loading old YAML files that have github_issue field.
        Validates and converts to proper types (string numbers to int).
        """
        if isinstance(data, dict) and "github_issue" in data:
            github_issue = data.pop("github_issue")
            if github_issue is not None:
                # Initialize remote_ids if not present
                if "remote_ids" not in data:
                    data["remote_ids"] = {}

                # Convert string to int if needed
                if isinstance(github_issue, str):
                    if not github_issue.isdigit():
                        raise ValueError(
                            "github_issue: must be an integer or numeric string"
                        )
                    github_issue = int(github_issue)
                elif not isinstance(github_issue, int):
                    raise ValueError("github_issue: must be an integer")

                # Validate positive
                if github_issue <= 0:
                    raise ValueError("github_issue: must be a positive integer")

                # Migrate github_issue to remote_ids
                data["remote_ids"]["github"] = github_issue
        return data

    @property
    def github_issue(self) -> int | str | None:
        """Get GitHub issue ID from remote_ids dict.

        Provides backwards compatibility for code accessing issue.github_issue.
        """
        if self.remote_ids and "github" in self.remote_ids:
            return self.remote_ids["github"]
        return None

    @github_issue.setter
    def github_issue(self, value: int | str | None) -> None:
        """Set GitHub issue ID in remote_ids dict.

        Provides backwards compatibility for code setting issue.github_issue.
        Validates that the value is a positive integer.
        """
        if value is None:
            # Remove github key if setting to None
            if self.remote_ids and "github" in self.remote_ids:
                del self.remote_ids["github"]
        else:
            # Convert string to int and validate
            if isinstance(value, str):
                if not value.isdigit():
                    raise ValueError(
                        "github_issue: must be an integer or numeric string"
                    )
                value = int(value)
            elif not isinstance(value, int):
                raise ValueError("github_issue: must be an integer or numeric string")

            if value <= 0:
                raise ValueError("github_issue: must be a positive integer")

            if not self.remote_ids:
                self.remote_ids = {}
            self.remote_ids["github"] = value

    def model_dump(self, **kwargs) -> dict[str, Any]:
        """Override model_dump to properly serialize remote_ids and github_issue.

        Includes github_issue for backwards compatibility in API/JSON usage.
        For file serialization (YAML), callers should remove github_issue field
        to ensure files use the modern remote_ids format.
        """
        data = super().model_dump(**kwargs)

        # Add github_issue for backwards compatibility in API responses
        # Callers handling file serialization should remove this field
        data["github_issue"] = self.github_issue

        return data

    def model_dump_json(self, **kwargs) -> str:
        """Override model_dump_json to include github_issue property for backwards compatibility."""
        # Get the dumped data which already includes github_issue via model_dump
        data = self.model_dump()
        # Use JSON serialization
        import json

        return json.dumps(data, default=str)

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
        elapsed = datetime.now(UTC) - self.actual_start_date
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
