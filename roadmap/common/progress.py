"""Progress calculation engine for automatic milestone and project updates.

This module provides the core functionality to automatically calculate and update
progress for milestones and projects based on issue completion, implementing
the requirements from issue 515a927c.
"""

from datetime import UTC, datetime, timedelta
from typing import Any

from structlog import get_logger

from roadmap.common.constants import MilestoneStatus, RiskLevel
from roadmap.core.domain import Issue, Milestone, Project

logger = get_logger()


class ProgressCalculationEngine:
    """Engine for calculating and updating milestone and project progress."""

    def __init__(self, method: str = "effort_weighted"):
        """Initialize the progress calculation engine.

        Args:
            method: Calculation method - 'effort_weighted' or 'count_based'
        """
        self.method = method

    def update_milestone_progress(
        self, milestone: Milestone, all_issues: list[Issue]
    ) -> bool:
        """Update milestone progress and status based on assigned issues.

        Args:
            milestone: The milestone to update
            all_issues: List of all issues in the system

        Returns:
            True if the milestone was updated, False otherwise
        """
        old_progress = milestone.calculated_progress
        old_status = milestone.status

        # Update automatic fields
        milestone.update_automatic_fields(all_issues, self.method)

        # Check if anything changed
        progress_changed = old_progress != milestone.calculated_progress
        status_changed = old_status != milestone.status

        if progress_changed or status_changed:
            old_progress_str = (
                f"{old_progress:.1f}" if old_progress is not None else "None"
            )
            new_progress_str = (
                f"{milestone.calculated_progress:.1f}"
                if milestone.calculated_progress is not None
                else "None"
            )
            logger.info(
                f"Updated milestone '{milestone.name}': progress {old_progress_str}% -> {new_progress_str}%, status {old_status} -> {milestone.status}"
            )
            return True

        return False

    def update_project_progress(
        self, project: Project, all_milestones: list[Milestone], all_issues: list[Issue]
    ) -> bool:
        """Update project progress and status based on assigned milestones.

        Args:
            project: The project to update
            all_milestones: List of all milestones in the system
            all_issues: List of all issues in the system

        Returns:
            True if the project was updated, False otherwise
        """
        old_progress = project.calculated_progress
        old_status = project.status

        # Update automatic fields
        project.update_automatic_fields(all_milestones, all_issues)

        # Calculate additional timeline intelligence
        self._update_project_timeline(project, all_milestones, all_issues)

        # Check if anything changed
        progress_changed = old_progress != project.calculated_progress
        status_changed = old_status != project.status

        if progress_changed or status_changed:
            old_progress_str = (
                f"{old_progress:.1f}" if old_progress is not None else "None"
            )
            new_progress_str = (
                f"{project.calculated_progress:.1f}"
                if project.calculated_progress is not None
                else "None"
            )
            logger.info(
                f"Updated project '{project.name}': progress {old_progress_str}% -> {new_progress_str}%, status {old_status} -> {project.status}"
            )
            return True

        return False

    def update_issue_dependencies(
        self,
        updated_issue: Issue,
        all_issues: list[Issue],
        all_milestones: list[Milestone],
        all_projects: list[Project],
    ) -> tuple[list[Milestone], list[Project]]:
        """Update all dependencies when an issue changes.

        Args:
            updated_issue: The issue that was updated
            all_issues: List of all issues in the system
            all_milestones: List of all milestones in the system
            all_projects: List of all projects in the system

        Returns:
            Tuple of (updated_milestones, updated_projects)
        """
        updated_milestones = []
        updated_projects = []

        # Find milestone affected by this issue
        if updated_issue.milestone:
            for milestone in all_milestones:
                if milestone.name == updated_issue.milestone:
                    if self.update_milestone_progress(milestone, all_issues):
                        updated_milestones.append(milestone)

                    # Find projects affected by this milestone
                    for project in all_projects:
                        if milestone.name in project.milestones:
                            if self.update_project_progress(
                                project, all_milestones, all_issues
                            ):
                                updated_projects.append(project)

        return updated_milestones, updated_projects

    def recalculate_all_progress(
        self,
        all_issues: list[Issue],
        all_milestones: list[Milestone],
        all_projects: list[Project],
    ) -> dict[str, int]:
        """Recalculate progress for all milestones and projects.

        Args:
            all_issues: List of all issues in the system
            all_milestones: List of all milestones in the system
            all_projects: List of all projects in the system

        Returns:
            Dictionary with counts of updated items
        """
        updated_milestones = 0
        updated_projects = 0

        # Update all milestones
        for milestone in all_milestones:
            if self.update_milestone_progress(milestone, all_issues):
                updated_milestones += 1

        # Update all projects
        for project in all_projects:
            if self.update_project_progress(project, all_milestones, all_issues):
                updated_projects += 1

        logger.info(
            f"Recalculated progress: {updated_milestones} milestones, {updated_projects} projects updated"
        )

        return {"milestones": updated_milestones, "projects": updated_projects}

    def _update_project_timeline(
        self, project: Project, all_milestones: list[Milestone], all_issues: list[Issue]
    ) -> None:
        """Update project timeline projections and risk assessment.

        Args:
            project: The project to update
            all_milestones: List of all milestones
            all_issues: List of all issues
        """
        project_milestones = project.get_milestones(all_milestones)

        if not project_milestones:
            return

        # Calculate completion velocity
        velocity = self._calculate_completion_velocity(project_milestones, all_issues)
        if velocity is not None:
            project.completion_velocity = velocity

        # Calculate projected completion date
        projected_date = self._calculate_projected_completion(
            project, project_milestones, all_issues
        )
        if projected_date:
            project.projected_end_date = projected_date

            # Calculate schedule variance
            if project.target_end_date:
                variance_days = (projected_date - project.target_end_date).days
                project.schedule_variance = variance_days

                # Update risk level based on schedule variance
                if variance_days > 14:  # More than 2 weeks behind
                    project.risk_level = RiskLevel.HIGH
                elif variance_days > 7:  # More than 1 week behind
                    project.risk_level = RiskLevel.MEDIUM
                elif variance_days < -7:  # More than 1 week ahead
                    project.risk_level = RiskLevel.LOW
                else:
                    project.risk_level = RiskLevel.LOW

    def _calculate_completion_velocity(
        self,
        milestones: list[Milestone],
        all_issues: list[Issue],
        window_weeks: int = 4,
    ) -> float | None:
        """Calculate completion velocity based on recent milestone completions.

        Args:
            milestones: Project milestones
            all_issues: List of all issues
            window_weeks: Time window for velocity calculation

        Returns:
            Milestones completed per week, or None if insufficient data
        """
        cutoff_date = datetime.now(UTC) - timedelta(weeks=window_weeks)

        # Count milestones completed in the time window
        completed_in_window = 0
        for milestone in milestones:
            if (
                milestone.actual_end_date
                and milestone.actual_end_date >= cutoff_date
                and milestone.status == MilestoneStatus.CLOSED
            ):
                completed_in_window += 1

        if completed_in_window == 0:
            return None

        return completed_in_window / window_weeks

    def _calculate_projected_completion(
        self, project: Project, milestones: list[Milestone], all_issues: list[Issue]
    ) -> datetime | None:
        """Calculate projected completion date based on velocity and remaining work.

        Args:
            project: The project
            milestones: Project milestones
            all_issues: List of all issues

        Returns:
            Projected completion date, or None if cannot calculate
        """
        if not project.completion_velocity:
            return None

        # Count incomplete milestones
        incomplete_milestones = [
            m for m in milestones if m.status != MilestoneStatus.CLOSED
        ]

        if not incomplete_milestones:
            # All milestones complete
            return datetime.now(UTC)

        # Calculate weeks needed to complete remaining milestones
        weeks_needed = len(incomplete_milestones) / project.completion_velocity

        return datetime.now(UTC) + timedelta(weeks=weeks_needed)


class ProgressEventSystem:
    """Event system for tracking progress updates and triggering cascading updates."""

    def __init__(self, engine: ProgressCalculationEngine):
        """Initialize the event system.

        Args:
            engine: The progress calculation engine
        """
        self.engine = engine
        self.listeners = []

    def register_listener(self, callback):
        """Register a callback for progress update events.

        Args:
            callback: Function to call when progress updates occur
        """
        self.listeners.append(callback)

    def on_issue_updated(
        self,
        updated_issue: Issue,
        changes: dict[str, Any],
        all_issues: list[Issue],
        all_milestones: list[Milestone],
        all_projects: list[Project],
    ) -> dict[str, Any]:
        """Handle issue update events and trigger cascading updates.

        Args:
            updated_issue: The updated issue
            changes: Dictionary of changed fields
            all_issues: List of all issues
            all_milestones: List of all milestones
            all_projects: List of all projects

        Returns:
            Dictionary with update results
        """
        # Check if this change affects progress
        progress_affecting_changes = [
            "status",
            "progress_percentage",
            "milestone",
            "estimated_hours",
        ]

        if not any(field in changes for field in progress_affecting_changes):
            return {"milestones_updated": [], "projects_updated": []}

        # Update dependent milestones and projects
        updated_milestones, updated_projects = self.engine.update_issue_dependencies(
            updated_issue, all_issues, all_milestones, all_projects
        )

        # Notify listeners
        for listener in self.listeners:
            try:
                listener(
                    {
                        "event": "issue_updated",
                        "issue": updated_issue,
                        "changes": changes,
                        "updated_milestones": updated_milestones,
                        "updated_projects": updated_projects,
                    }
                )
            except Exception as e:
                logger.error(f"Error in progress event listener: {e}")

        return {
            "milestones_updated": updated_milestones,
            "projects_updated": updated_projects,
        }
