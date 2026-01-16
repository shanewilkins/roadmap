"""
Service layer for milestone list command.

Handles all business logic related to:
- Filtering milestones (overdue, open/closed, etc.)
- Computing milestone progress
- Calculating time estimates
- Aggregating milestone data
"""

from datetime import UTC, datetime

from roadmap.common.logging import get_logger
from roadmap.infrastructure.coordination.core import RoadmapCore

logger = get_logger(__name__)


class MilestoneFilterService:
    """Service for filtering and selecting milestones."""

    @staticmethod
    def filter_overdue_milestones(milestones: list) -> list:
        """Filter to only overdue milestones.

        Args:
            milestones: List of milestone objects

        Returns:
            List of overdue milestones (past due date, status='open')
        """
        try:
            now = datetime.now(UTC).replace(tzinfo=None)
            filtered = []

            for ms in milestones:
                if ms.due_date:
                    ms_due_date = (
                        ms.due_date.replace(tzinfo=None)
                        if ms.due_date.tzinfo
                        else ms.due_date
                    )
                    if ms_due_date < now and ms.status.value == "open":
                        filtered.append(ms)

            return filtered
        except Exception as e:
            logger.error("failed_to_filter_overdue", error=str(e))
            return []

    @staticmethod
    def filter_milestones(milestones: list, overdue_only: bool = False) -> list:
        """Filter milestones based on criteria.

        Args:
            milestones: List of milestone objects
            overdue_only: If True, only return overdue milestones

        Returns:
            Filtered list of milestones
        """
        if overdue_only:
            return MilestoneFilterService.filter_overdue_milestones(milestones)
        return milestones


class MilestoneProgressService:
    """Service for computing milestone progress."""

    @staticmethod
    def get_milestone_progress(core: RoadmapCore, milestone_name: str) -> dict:
        """Get progress for a specific milestone.

        Args:
            core: RoadmapCore instance
            milestone_name: Name of the milestone

        Returns:
            Dictionary with progress data:
            {
                'total': total issues,
                'completed': completed issues,
                'percentage': completion percentage,
            }
        """
        try:
            progress = core.milestones.get_progress(milestone_name)
            return {
                "total": progress.get("total", 0),
                "completed": progress.get("completed", 0),
                "percentage": (
                    (progress.get("completed", 0) / progress.get("total", 1)) * 100
                    if progress.get("total", 0) > 0
                    else 0
                ),
            }
        except Exception as e:
            logger.error(
                "failed_to_get_milestone_progress",
                milestone=milestone_name,
                error=str(e),
            )
            return {"total": 0, "completed": 0, "percentage": 0}

    @staticmethod
    def get_all_milestones_progress(core: RoadmapCore, milestones: list) -> dict:
        """Get progress for all milestones.

        Args:
            core: RoadmapCore instance
            milestones: List of milestone objects

        Returns:
            Dictionary mapping milestone name to progress dict
        """
        progress_data = {}
        for ms in milestones:
            progress_data[ms.name] = MilestoneProgressService.get_milestone_progress(
                core, ms.name
            )
        return progress_data


class MilestoneTimeEstimateService:
    """Service for calculating time estimates."""

    @staticmethod
    def get_milestone_time_estimate(milestone, all_issues: list) -> str:
        """Get time estimate display string for a milestone.

        Args:
            milestone: Milestone object
            all_issues: List of all issues in roadmap

        Returns:
            Formatted time estimate string (e.g., "32 hours", "N/A")
        """
        try:
            estimate = milestone.get_estimated_time_display(all_issues)
            return estimate if estimate else "-"
        except Exception as e:
            logger.error(
                "failed_to_get_time_estimate",
                milestone=milestone.name,
                error=str(e),
            )
            return "-"


class MilestoneListService:
    """Service for gathering and processing milestone list data."""

    def __init__(self, core: RoadmapCore):
        """Initialize milestone list service.

        Args:
            core: RoadmapCore instance
        """
        self.core = core

    def get_milestones_list_data(self, overdue_only: bool = False) -> dict:
        """Get all data needed for milestone list display.

        Args:
            overdue_only: If True, only return overdue milestones

        Returns:
            Dictionary with milestone list data:
            {
                'milestones': list of milestone objects,
                'progress': dict mapping milestone name to progress,
                'estimates': dict mapping milestone name to estimate,
                'has_data': bool indicating if there are milestones,
                'count': number of milestones,
            }
        """
        try:
            # Get milestones
            milestones = self.core.milestones.list()

            # Apply filters
            milestones = MilestoneFilterService.filter_milestones(
                milestones, overdue_only=overdue_only
            )

            # Get all issues for estimates
            all_issues = self.core.issues.list()

            # Compute progress for each milestone
            progress = MilestoneProgressService.get_all_milestones_progress(
                self.core, milestones
            )

            # Compute time estimates
            estimates = {}
            for ms in milestones:
                estimates[ms.name] = (
                    MilestoneTimeEstimateService.get_milestone_time_estimate(
                        ms, all_issues
                    )
                )

            return {
                "milestones": milestones,
                "progress": progress,
                "estimates": estimates,
                "has_data": bool(milestones),
                "count": len(milestones),
            }
        except Exception as e:
            logger.error(
                "failed_to_get_milestones_list_data",
                error=str(e),
            )
            return {
                "milestones": [],
                "progress": {},
                "estimates": {},
                "has_data": False,
                "count": 0,
            }

    def get_milestone_due_date_status(self, milestone) -> tuple[str, str | None]:
        """Get due date string and styling for a milestone.

        Args:
            milestone: Milestone object

        Returns:
            Tuple of (due_date_string, style_markup or None)
            - style_markup is None for no special styling
            - style_markup is "bold red" for overdue
            - style_markup is "yellow" for due within 7 days
        """
        if not milestone.due_date:
            return ("-", None)

        try:
            now = datetime.now(UTC).replace(tzinfo=None)
            ms_due_date = (
                milestone.due_date.replace(tzinfo=None)
                if milestone.due_date.tzinfo
                else milestone.due_date
            )

            due_date_text = ms_due_date.strftime("%Y-%m-%d")

            # Determine styling based on due date and status
            if ms_due_date < now and milestone.status.value == "open":
                return (due_date_text, "bold red")
            elif (ms_due_date - now).days <= 7 and milestone.status.value == "open":
                return (due_date_text, "yellow")

            return (due_date_text, None)
        except Exception as e:
            logger.error(
                "failed_to_get_due_date_status",
                milestone=milestone.name,
                error=str(e),
            )
            return ("-", None)
