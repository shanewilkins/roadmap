"""Service for fetching and counting sync data from local and remote sources."""

from structlog import get_logger

from roadmap.core.interfaces.sync_backend import SyncBackendInterface
from roadmap.core.services.sync.sync_report import SyncReport
from roadmap.infrastructure.core import RoadmapCore

logger = get_logger(__name__)


class SyncDataFetchService:
    """Handles fetching issues and metadata from local and remote sources."""

    def __init__(self, core: RoadmapCore, backend: SyncBackendInterface):
        """Initialize data fetch service.

        Args:
            core: RoadmapCore instance
            backend: SyncBackendInterface implementation
        """
        self.core = core
        self.backend = backend

    def fetch_remote_issues(self, report: SyncReport):
        """Fetch remote issues from backend.

        Args:
            report: SyncReport to record any fetch errors

        Returns:
            Dict of remote issues or None if fetch failed
        """
        try:
            logger.debug("fetching_remote_issues")
            remote_issues_data = self.backend.get_issues()
            if remote_issues_data is None:
                report.error = "Failed to fetch remote issues"
                logger.error(
                    "remote_issues_fetch_returned_none",
                    operation="fetch_remote_issues",
                    suggested_action="check_backend_connectivity",
                )
                return None
            logger.info("remote_issues_fetched", remote_count=len(remote_issues_data))
            return remote_issues_data
        except (ConnectionError, TimeoutError) as e:
            report.error = f"Failed to fetch remote issues: {str(e)}"
            logger.error(
                "remote_issues_fetch_error",
                operation="fetch_remote_issues",
                error_type=type(e).__name__,
                error=str(e),
                is_recoverable=True,
                suggested_action="retry_after_delay",
            )
            return None
        except Exception as e:
            report.error = f"Failed to fetch remote issues: {str(e)}"
            logger.error(
                "remote_issues_fetch_error",
                operation="fetch_remote_issues",
                error_type=type(e).__name__,
                error=str(e),
                is_recoverable=False,
                suggested_action="check_backend_configuration",
            )
            return None

    def fetch_local_issues(self, report: SyncReport):
        """Fetch local issues from roadmap.

        Args:
            report: SyncReport to record any fetch errors

        Returns:
            List of local Issue objects or None if fetch failed
        """
        try:
            logger.debug("fetching_local_issues")
            local_issues = self.core.issues.list_all_including_archived() or []
            logger.info("local_issues_fetched", local_count=len(local_issues))
            return local_issues
        except OSError as e:
            report.error = f"Failed to fetch local issues: {str(e)}"
            logger.error(
                "local_issues_fetch_error",
                operation="fetch_local_issues",
                error_type=type(e).__name__,
                error=str(e),
                is_recoverable=False,
                suggested_action="check_file_permissions",
            )
            return None
        except Exception as e:
            report.error = f"Failed to fetch local issues: {str(e)}"
            logger.error(
                "local_issues_fetch_error",
                operation="fetch_local_issues",
                error_type=type(e).__name__,
                error=str(e),
                error_classification="sync_error",
            )
            return None

    def count_active_archived(self, local_issues):
        """Count active and archived issues.

        Args:
            local_issues: List of Issue objects

        Returns:
            Tuple of (active_count, archived_count)
        """
        active_issues_count = 0
        archived_issues_count = 0
        for issue in local_issues:
            if issue.file_path and "archive" in issue.file_path:
                archived_issues_count += 1
            else:
                active_issues_count += 1
        return active_issues_count, archived_issues_count

    def count_milestones(self):
        """Count active and archived milestones.

        Returns:
            Tuple of (all_milestones, active_count, archived_count)
        """
        try:
            all_milestones = self.core.milestones.list()
            active_milestones_count = 0
            archived_milestones_count = 0
            for milestone in all_milestones:
                if (
                    hasattr(milestone, "file_path")
                    and milestone.file_path
                    and "archive" in milestone.file_path
                ):
                    archived_milestones_count += 1
                else:
                    active_milestones_count += 1
            return all_milestones, active_milestones_count, archived_milestones_count
        except Exception as e:
            logger.debug("milestone_count_failed", error=str(e))
            return [], 0, 0

    def count_remote_stats(self, remote_issues_data):
        """Count remote issues and milestones statistics.

        Args:
            remote_issues_data: Dict of remote issues

        Returns:
            Tuple of (total_count, open_count, closed_count, milestones_count)
        """
        try:
            remote_issues_count = len(remote_issues_data) if remote_issues_data else 0
            remote_open_count = 0
            remote_closed_count = 0
            for issue_data in remote_issues_data.values() if remote_issues_data else []:
                state = getattr(issue_data, "state", None) or getattr(
                    issue_data, "status", "open"
                )
                if state and state.lower() == "closed":
                    remote_closed_count += 1
                else:
                    remote_open_count += 1

            remote_milestones = self.backend.get_milestones()
            remote_milestones_count = len(remote_milestones) if remote_milestones else 0
            logger.debug(
                "remote_items_counted",
                remote_issues=remote_issues_count,
                remote_open=remote_open_count,
                remote_closed=remote_closed_count,
                remote_milestones=remote_milestones_count,
            )
            return (
                remote_issues_count,
                remote_open_count,
                remote_closed_count,
                remote_milestones_count,
            )
        except Exception as e:
            logger.error("count_remote_stats_error", error=str(e))
            return 0, 0, 0, 0
