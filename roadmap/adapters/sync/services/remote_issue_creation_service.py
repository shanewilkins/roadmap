"""Service for creating local issues from remote data."""

from structlog import get_logger

from roadmap.core.domain.issue import Issue, Status
from roadmap.core.models.sync_models import SyncIssue
from roadmap.infrastructure.coordination.core import RoadmapCore

logger = get_logger()


class RemoteIssueCreationService:
    """Handles creating local issues from remote issue data."""

    def __init__(self, core: RoadmapCore):
        """Initialize creation service.

        Args:
            core: RoadmapCore instance
        """
        self.core = core

    def create_issue_from_remote(
        self, remote_id: str | int, remote_issue: SyncIssue
    ) -> Issue:
        """Create a local Issue from remote SyncIssue data.

        Extracts relevant fields from remote issue and creates a local Issue object.
        Adds "synced:from-github" label to mark as synced from remote.
        Uses remote milestone if available, otherwise defaults to backlog.

        Args:
            remote_id: Remote issue ID (number)
            remote_issue: SyncIssue object with remote data including:
                - title: Issue title
                - headline: Short description
                - status: 'open', 'closed', etc.
                - labels: List of label names
                - assignee: Assignee login
                - milestone: Milestone title or None
                - backend_id: GitHub issue number

        Returns:
            New Issue object ready to be created
        """
        try:
            # Normalize status
            issue_status = self._normalize_status(remote_issue.status)

            # Prepare labels with synced marker
            labels = list(remote_issue.labels or [])
            if "synced:from-github" not in labels:
                labels.append("synced:from-github")

            # Create the issue
            new_issue = Issue(
                title=remote_issue.title or f"Remote Issue {remote_id}",
                content=remote_issue.headline or "",
                status=issue_status,
                labels=labels,
                assignee=remote_issue.assignee,
                milestone=remote_issue.milestone or "backlog",
            )

            # Link to remote
            if remote_issue.backend_id:
                new_issue.remote_ids["github"] = remote_issue.backend_id

            logger.info(
                "remote_issue_created_locally",
                remote_id=remote_id,
                title=remote_issue.title,
                local_status=issue_status,
            )

            return new_issue

        except Exception as e:
            logger.error(
                "remote_issue_creation_failed",
                remote_id=remote_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

    @staticmethod
    def _normalize_status(remote_status: str | None) -> Status:
        """Normalize remote status to local Status enum.

        Args:
            remote_status: Remote status string (e.g., 'open', 'closed')

        Returns:
            Local Status enum value
        """
        if not remote_status:
            return Status.TODO

        remote_lower = remote_status.lower()

        # Map common remote statuses to local statuses
        status_map = {
            "open": Status.TODO,
            "in_progress": Status.IN_PROGRESS,
            "in progress": Status.IN_PROGRESS,
            "done": Status.CLOSED,
            "closed": Status.CLOSED,
            "blocked": Status.BLOCKED,
        }

        return status_map.get(remote_lower, Status.TODO)
