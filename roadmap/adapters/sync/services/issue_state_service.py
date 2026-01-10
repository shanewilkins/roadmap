"""Service for converting between SyncIssue and local Issue domain objects."""

from datetime import datetime, timezone
from typing import Any

from structlog import get_logger

from roadmap.common.constants import Priority, Status
from roadmap.core.domain.issue import Issue
from roadmap.core.models.sync_models import SyncIssue

logger = get_logger(__name__)


class IssueStateService:
    """Handles conversion between SyncIssue (remote) and Issue (local) domain objects.
    
    Centralizes field mapping, normalization, and type conversions to eliminate
    duplication between pull_issue() and push_issue() methods.
    """

    @staticmethod
    def sync_issue_to_issue(issue_id: str, sync_issue: SyncIssue) -> Issue:
        """Convert a SyncIssue (from backend) to a local Issue domain object.
        
        Args:
            issue_id: Local issue ID to assign
            sync_issue: Remote SyncIssue with backend data
            
        Returns:
            Issue object ready for local storage/update
            
        Raises:
            ValueError: If required fields are missing
        """
        if not issue_id or not issue_id.strip():
            logger.error("cannot_convert_sync_issue_empty_issue_id")
            raise ValueError("issue_id cannot be empty")

        if not sync_issue:
            logger.error("cannot_convert_none_sync_issue")
            raise ValueError("sync_issue cannot be None")

        if not sync_issue.title or not sync_issue.title.strip():
            logger.warning(
                "sync_issue_missing_title",
                issue_id=issue_id,
                backend_name=sync_issue.backend_name,
                backend_id=sync_issue.backend_id,
            )

        try:
            # Parse timestamps
            created_at = sync_issue.created_at or datetime.now(timezone.utc)
            updated_at = sync_issue.updated_at or datetime.now(timezone.utc)

            # Normalize status
            status = IssueStateService.normalize_status(sync_issue.status)

            # Prepare content
            content = ""
            if sync_issue.headline and sync_issue.headline.strip():
                content = sync_issue.headline

            # Create Issue object
            issue = Issue(
                id=issue_id,
                title=sync_issue.title or "Untitled",
                content=content,
                status=status,
                priority=Priority.MEDIUM,  # Default priority (not in SyncIssue)
                labels=sync_issue.labels or [],
                assignee=sync_issue.assignee,
                milestone=sync_issue.milestone,
                created=created_at,
                updated=updated_at,
            )

            # Set remote_ids from sync_issue for tracking
            if sync_issue.remote_ids:
                issue.remote_ids = sync_issue.remote_ids.copy()
            
            # Track backend info in github_sync_metadata
            issue.github_sync_metadata = {
                "backend_name": sync_issue.backend_name,
                "backend_id": sync_issue.backend_id,
                **(sync_issue.metadata or {}),
            }

            logger.info(
                "converted_sync_issue_to_issue",
                issue_id=issue_id,
                title=issue.title,
                status=status.value,
                from_backend=sync_issue.backend_name,
            )

            return issue
        except ValueError as e:
            logger.error(
                "sync_issue_conversion_validation_error",
                issue_id=issue_id,
                error=str(e),
            )
            raise
        except Exception as e:
            logger.error(
                "sync_issue_conversion_failed",
                issue_id=issue_id,
                backend_name=sync_issue.backend_name,
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True,
            )
            raise

    @staticmethod
    def issue_to_push_payload(issue: Issue) -> dict[str, Any]:
        """Convert a local Issue to a push payload for remote backend.
        
        Extracts fields that are relevant for pushing to GitHub/remote.
        
        Args:
            issue: Local Issue to convert
            
        Returns:
            Dictionary with fields safe for remote API
            
        Raises:
            ValueError: If issue is invalid or missing required fields
        """
        if not issue:
            logger.error("cannot_build_push_payload_none_issue")
            raise ValueError("issue cannot be None")

        if not issue.title or not issue.title.strip():
            logger.error(
                "cannot_build_push_payload_empty_title",
                issue_id=issue.id,
            )
            raise ValueError("issue.title cannot be empty")

        try:
            # Normalize status to backend format
            state = "open"
            if issue.status == Status.CLOSED:
                state = "closed"

            payload: dict[str, Any] = {
                "title": issue.title,
                "body": issue.content or "",
                "state": state,
            }

            # Handle labels - may be comma-separated strings
            if issue.labels:
                labels_list: list[str] = []
                for label in issue.labels:
                    if isinstance(label, str):
                        labels_list.extend(
                            [
                                label_item.strip()
                                for label_item in label.split(",")
                                if label_item.strip()
                            ]
                        )
                    else:
                        labels_list.append(str(label).strip())

                if labels_list:
                    payload["labels"] = labels_list

            logger.info(
                "issue_converted_to_push_payload",
                issue_id=issue.id,
                title=issue.title,
                state=state,
                has_labels=bool(payload.get("labels")),
            )

            return payload
        except ValueError as e:
            logger.error(
                "push_payload_validation_error",
                issue_id=issue.id,
                error=str(e),
            )
            raise
        except Exception as e:
            logger.error(
                "push_payload_creation_failed",
                issue_id=issue.id,
                title=issue.title,
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True,
            )
            raise

    @staticmethod
    def normalize_status(status_value: str | None) -> Status:
        """Normalize a status string from any backend to local Status enum.
        
        Args:
            status_value: Status string from backend
            
        Returns:
            Normalized Status enum value
        """
        if not status_value:
            return Status.TODO

        status_lower = status_value.lower()

        if status_lower in ("closed", "done", "completed", "resolved"):
            return Status.CLOSED
        elif status_lower in ("in_progress", "in progress", "active", "started"):
            return Status.IN_PROGRESS
        elif status_lower in ("on_hold", "on hold", "blocked", "paused"):
            return Status.BLOCKED
        else:
            return Status.TODO
