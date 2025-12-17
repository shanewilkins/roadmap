"""Project domain model."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from roadmap.common.constants import ProjectStatus
from .issue import Priority
from .milestone import MilestoneStatus, RiskLevel


class Project(BaseModel):
    """Project data model."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str
    description: str = ""
    status: ProjectStatus = ProjectStatus.PLANNING
    priority: Priority = Priority.MEDIUM
    owner: str | None = None
    start_date: datetime | None = None
    target_end_date: datetime | None = None
    actual_end_date: datetime | None = None
    created: datetime = Field(default_factory=datetime.now)
    updated: datetime = Field(default_factory=datetime.now)
    milestones: list[str] = Field(default_factory=list)  # List of milestone names
    estimated_hours: float | None = None
    actual_hours: float | None = None
    content: str = ""  # Markdown content

    # Automatic progress tracking fields
    calculated_progress: float | None = None  # Auto-calculated from milestones
    last_progress_update: datetime | None = None
    projected_end_date: datetime | None = None  # Auto-calculated
    schedule_variance: int | None = None  # Days ahead/behind
    completion_velocity: float | None = None  # Milestones/week
    risk_level: RiskLevel = RiskLevel.LOW

    file_path: str | None = Field(
        default=None, exclude=True
    )  # Internal: absolute path where project file is stored

    def get_milestones(self, all_milestones):
        """Get all milestones assigned to this project.

        Args:
            all_milestones: List of Milestone objects to filter

        Returns:
            List of milestones assigned to this project
        """
        return [
            milestone
            for milestone in all_milestones
            if milestone.name in self.milestones
        ]

    def get_milestone_count(self, all_milestones) -> int:
        """Get the count of milestones assigned to this project."""
        return len(self.get_milestones(all_milestones))

    def calculate_progress(self, all_milestones, all_issues) -> float:
        """Calculate project progress from milestone completion (effort-weighted).

        Args:
            all_milestones: List of all milestones in the system
            all_issues: List of all issues in the system

        Returns:
            Progress percentage from 0.0 to 100.0
        """
        project_milestones = self.get_milestones(all_milestones)
        if not project_milestones:
            return 0.0

        # Use milestone effort (total estimated hours) as weight
        total_weight = 0.0
        completed_weight = 0.0

        for milestone in project_milestones:
            milestone_weight = milestone.get_total_estimated_hours(all_issues) or 1.0
            total_weight += milestone_weight

            if milestone.status == MilestoneStatus.CLOSED:
                completed_weight += milestone_weight
            else:
                # Partial completion based on milestone progress
                milestone_progress = (
                    milestone.get_completion_percentage(all_issues) / 100.0
                )
                completed_weight += milestone_weight * milestone_progress

        return (completed_weight / total_weight) * 100.0 if total_weight > 0 else 0.0

    def update_automatic_fields(self, all_milestones, all_issues) -> None:
        """Update all automatic progress tracking fields.

        Args:
            all_milestones: List of all milestones in the system
            all_issues: List of all issues in the system
        """
        self.calculated_progress = self.calculate_progress(all_milestones, all_issues)
        self.last_progress_update = datetime.now()
        self.updated = datetime.now()

        # Update status based on progress
        if self.calculated_progress >= 100.0:
            self.status = ProjectStatus.COMPLETED
            if not self.actual_end_date:
                self.actual_end_date = datetime.now()
        elif self.calculated_progress > 0:
            if self.status == ProjectStatus.PLANNING:
                self.status = ProjectStatus.ACTIVE

    @property
    def filename(self) -> str:
        """Generate filename for this project."""
        safe_name = "".join(
            c for c in self.name if c.isalnum() or c in (" ", "-", "_")
        ).strip()
        safe_name = safe_name.replace(" ", "-").lower()
        return f"{self.id}-{safe_name}.md"
