"""Service layer for project status computation and aggregation.

Handles all business logic related to:
- Computing milestone progress
- Aggregating issue statistics
- Computing status summaries
- Gathering roadmap metrics
"""

from collections import Counter
from pathlib import Path

from roadmap.adapters.persistence.parser import MilestoneParser, ProjectParser
from roadmap.common.logging import get_logger
from roadmap.common.models import ColumnDef, ColumnType, TableData
from roadmap.core.domain import MilestoneStatus, ProjectStatus, Status
from roadmap.infrastructure.coordination.core import RoadmapCore
from roadmap.infrastructure.validation.file_enumeration import FileEnumerationService

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
            logger.error(
                "failed_to_gather_status_data", error=str(e), severity="operational"
            )
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
                severity="operational",
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


class StatusSnapshotService:
    """Service for building a snapshot of entity status counts."""

    @staticmethod
    def build_snapshot_tables(core: RoadmapCore) -> dict[str, TableData]:
        """Build status snapshot tables for entities and issue status.

        Args:
            core: RoadmapCore instance

        Returns:
            Dictionary with TableData objects for snapshot output.
        """
        projects = list(core.projects.list())
        milestones = list(core.milestones.list())
        issues = list(core.issues.list_all_including_archived())

        archived_projects = StatusSnapshotService._list_archived_projects(core)
        archived_milestones = StatusSnapshotService._list_archived_milestones(core)

        project_counts = StatusSnapshotService._count_projects(projects)
        milestone_counts = StatusSnapshotService._count_milestones(milestones)
        issue_counts = StatusSnapshotService._count_issues(issues)

        entities_table = StatusSnapshotService._build_entities_table(
            project_counts=project_counts,
            milestone_counts=milestone_counts,
            issue_counts=issue_counts,
            archived_projects=len(archived_projects),
            archived_milestones=len(archived_milestones),
        )
        issue_status_table = StatusSnapshotService._build_issue_status_table(
            issue_counts=issue_counts
        )

        return {
            "entities": entities_table,
            "issue_status": issue_status_table,
        }

    @staticmethod
    def _list_archived_projects(core: RoadmapCore) -> list:
        archive_dir = core.projects_dir.parent / "archive" / "projects"
        return FileEnumerationService.enumerate_and_parse(
            archive_dir, ProjectParser.parse_project_file
        )

    @staticmethod
    def _list_archived_milestones(core: RoadmapCore) -> list:
        archive_dir = core.milestones_dir.parent / "archive" / "milestones"
        return FileEnumerationService.enumerate_and_parse(
            archive_dir, MilestoneParser.parse_milestone_file
        )

    @staticmethod
    def _is_archived_issue(issue) -> bool:
        if getattr(issue, "archived", False):
            return True
        if getattr(issue, "status", None) == Status.ARCHIVED:
            return True
        file_path = getattr(issue, "file_path", "") or ""
        return "archive" in Path(file_path).parts

    @staticmethod
    def _count_projects(projects: list) -> dict[ProjectStatus, int]:
        counts = dict.fromkeys(ProjectStatus, 0)
        for project in projects:
            if project.status in counts:
                counts[project.status] += 1
        return counts

    @staticmethod
    def _count_milestones(milestones: list) -> dict[MilestoneStatus, int]:
        counts = dict.fromkeys(MilestoneStatus, 0)
        for milestone in milestones:
            if milestone.status in counts:
                counts[milestone.status] += 1
        return counts

    @staticmethod
    def _count_issues(issues: list) -> dict[Status, int]:
        counts = dict.fromkeys(Status, 0)
        for issue in issues:
            if StatusSnapshotService._is_archived_issue(issue):
                counts[Status.ARCHIVED] += 1
            else:
                counts[issue.status] = counts.get(issue.status, 0) + 1
        return counts

    @staticmethod
    def _build_entities_table(
        project_counts: dict[ProjectStatus, int],
        milestone_counts: dict[MilestoneStatus, int],
        issue_counts: dict[Status, int],
        archived_projects: int,
        archived_milestones: int,
    ) -> TableData:
        columns = [
            ColumnDef("entity", "Entity", ColumnType.STRING, width=12),
            ColumnDef("open", "Open", ColumnType.INTEGER, width=6),
            ColumnDef("closed", "Closed", ColumnType.INTEGER, width=7),
            ColumnDef("archived", "Archived", ColumnType.INTEGER, width=9),
            ColumnDef("total", "Total", ColumnType.INTEGER, width=6),
        ]

        project_open = sum(
            project_counts.get(status, 0)
            for status in (
                ProjectStatus.PLANNING,
                ProjectStatus.ACTIVE,
                ProjectStatus.ON_HOLD,
            )
        )
        project_closed = sum(
            project_counts.get(status, 0)
            for status in (ProjectStatus.COMPLETED, ProjectStatus.CANCELLED)
        )
        project_total = project_open + project_closed + archived_projects

        milestone_open = milestone_counts.get(MilestoneStatus.OPEN, 0)
        milestone_closed = milestone_counts.get(MilestoneStatus.CLOSED, 0)
        milestone_total = milestone_open + milestone_closed + archived_milestones

        issue_open = sum(
            issue_counts.get(status, 0)
            for status in (
                Status.TODO,
                Status.IN_PROGRESS,
                Status.BLOCKED,
                Status.REVIEW,
            )
        )
        issue_closed = issue_counts.get(Status.CLOSED, 0)
        issue_archived = issue_counts.get(Status.ARCHIVED, 0)
        issue_total = issue_open + issue_closed + issue_archived

        rows = [
            [
                "Projects",
                project_open,
                project_closed,
                archived_projects,
                project_total,
            ],
            [
                "Milestones",
                milestone_open,
                milestone_closed,
                archived_milestones,
                milestone_total,
            ],
            ["Issues", issue_open, issue_closed, issue_archived, issue_total],
        ]

        totals = [
            "Total",
            project_open + milestone_open + issue_open,
            project_closed + milestone_closed + issue_closed,
            archived_projects + archived_milestones + issue_archived,
            project_total + milestone_total + issue_total,
        ]
        rows.append(totals)

        return TableData(columns=columns, rows=rows, title="Entities")

    @staticmethod
    def _build_issue_status_table(issue_counts: dict[Status, int]) -> TableData:
        columns = [
            ColumnDef("status", "Status", ColumnType.STRING, width=14),
            ColumnDef("count", "Count", ColumnType.INTEGER, width=7),
        ]
        rows = []
        total = 0
        for status in Status:
            count = issue_counts.get(status, 0)
            total += count
            rows.append([status.value, count])

        rows.append(["Total", total])

        return TableData(columns=columns, rows=rows, title="Issue Status")


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
            logger.error(
                "failed_to_compute_roadmap_summary",
                error=str(e),
                severity="operational",
            )
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
