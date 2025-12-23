"""
Service layer for project status computation and aggregation.

Handles all business logic related to:
- Computing milestone progress
- Aggregating issue statistics
- Computing status summaries
- Gathering roadmap metrics
"""

from collections import Counter

from roadmap.common.logging import get_logger
from roadmap.core.domain import Status
from roadmap.infrastructure.core import RoadmapCore

logger = get_logger(__name__)


class StatusDataService:
    """Service for gathering and computing status data."""

    @staticmethod
    def gather_status_data(core: RoadmapCore) -> dict:
        """Gather all status data from roadmap.

        Args:
            core: RoadmapCore instance

        Returns:
            Dictionary with status_data:
            {
                'issues': list of issues,
                'milestones': list of milestones,
                'has_data': bool,
                'issue_count': int,
                'milestone_count': int,
            }
        """
        try:
            issues = core.issues.list()
            milestones = core.milestones.list()

            return {
                "issues": issues,
                "milestones": milestones,
                "has_data": bool(issues or milestones),
                "issue_count": len(issues),
                "milestone_count": len(milestones),
            }
        except Exception as e:
            logger.error("failed_to_gather_status_data", error=str(e))
            return {
                "issues": [],
                "milestones": [],
                "has_data": False,
                "issue_count": 0,
                "milestone_count": 0,
            }


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
                'total': total issues in milestone,
                'completed': completed issues in milestone,
                'percentage': completion percentage,
            }
        """
        try:
            progress = core.db.get_milestone_progress(milestone_name)
            if progress and progress["total"] > 0:
                percentage = (progress["completed"] / progress["total"]) * 100
            else:
                percentage = 0

            return {
                "total": progress.get("total", 0),
                "completed": progress.get("completed", 0),
                "percentage": percentage,
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
        for milestone in milestones:
            progress_data[milestone.name] = (
                MilestoneProgressService.get_milestone_progress(core, milestone.name)
            )
        return progress_data


class IssueStatisticsService:
    """Service for computing issue statistics."""

    @staticmethod
    def get_issue_status_counts(issues: list) -> dict:
        """Count issues by status.

        Args:
            issues: List of issue objects

        Returns:
            Dictionary mapping Status enum to count
        """
        status_counts = Counter(issue.status for issue in issues)
        return dict(status_counts)

    @staticmethod
    def get_status_styling() -> dict:
        """Get color styling for each status.

        Returns:
            Dictionary mapping Status enum to style string
        """
        return {
            Status.TODO: "white",
            Status.IN_PROGRESS: "yellow",
            Status.BLOCKED: "red",
            Status.REVIEW: "blue",
            Status.CLOSED: "green",
        }

    @staticmethod
    def get_all_status_counts(issues: list) -> dict:
        """Get counts for all status values, including zeros.

        Args:
            issues: List of issue objects

        Returns:
            Dictionary with all Status enum values and their counts
        """
        status_counts = IssueStatisticsService.get_issue_status_counts(issues)

        # Ensure all statuses are represented
        all_counts = {}
        for status in Status:
            all_counts[status] = status_counts.get(status, 0)

        return all_counts

    @staticmethod
    def get_active_issue_count(issues: list) -> int:
        """Count non-closed issues.

        Args:
            issues: List of issue objects

        Returns:
            Count of active (non-closed) issues
        """
        return sum(1 for issue in issues if issue.status != Status.CLOSED)

    @staticmethod
    def get_blocked_issue_count(issues: list) -> int:
        """Count blocked issues.

        Args:
            issues: List of issue objects

        Returns:
            Count of blocked issues
        """
        return sum(1 for issue in issues if issue.status == Status.BLOCKED)


class RoadmapSummaryService:
    """Service for computing high-level roadmap summaries."""

    @staticmethod
    def compute_roadmap_summary(
        core: RoadmapCore, issues: list, milestones: list
    ) -> dict:
        """Compute comprehensive roadmap summary.

        Args:
            core: RoadmapCore instance
            issues: List of issue objects
            milestones: List of milestone objects

        Returns:
            Dictionary with summary data:
            {
                'total_issues': int,
                'active_issues': int,
                'blocked_issues': int,
                'total_milestones': int,
                'completed_milestones': int,
                'milestone_progress': dict,
                'issue_status_counts': dict,
                'milestone_details': list,
            }
        """
        try:
            milestone_progress = MilestoneProgressService.get_all_milestones_progress(
                core, milestones
            )

            completed_milestones = sum(
                1
                for progress in milestone_progress.values()
                if progress["percentage"] == 100 and progress["total"] > 0
            )

            milestone_details = []
            for milestone in milestones:
                progress = milestone_progress.get(milestone.name, {})
                milestone_details.append(
                    {
                        "name": milestone.name,
                        "progress": progress,
                        "due_date": getattr(milestone, "due_date", None),
                    }
                )

            return {
                "total_issues": len(issues),
                "active_issues": IssueStatisticsService.get_active_issue_count(issues),
                "blocked_issues": IssueStatisticsService.get_blocked_issue_count(
                    issues
                ),
                "total_milestones": len(milestones),
                "completed_milestones": completed_milestones,
                "milestone_progress": milestone_progress,
                "issue_status_counts": IssueStatisticsService.get_all_status_counts(
                    issues
                ),
                "milestone_details": milestone_details,
            }
        except Exception as e:
            logger.error("failed_to_compute_roadmap_summary", error=str(e))
            return {
                "total_issues": len(issues),
                "active_issues": 0,
                "blocked_issues": 0,
                "total_milestones": len(milestones),
                "completed_milestones": 0,
                "milestone_progress": {},
                "issue_status_counts": {},
                "milestone_details": [],
            }
