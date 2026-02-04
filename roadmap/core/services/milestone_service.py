"""Milestone service - handles all milestone-related operations.

The MilestoneService manages:
- Milestone creation with metadata
- Milestone listing and sorting
- Getting specific milestones by name
- Updating milestone properties
- Deleting milestones (with issue cleanup)
- Progress calculation
- Status tracking

Extracted from core.py to separate business logic.
"""

from datetime import datetime
from pathlib import Path
from typing import Any

import structlog

from roadmap.common.constants import MilestoneStatus, Status
from roadmap.common.errors import OperationType, safe_operation
from roadmap.common.logging import get_logger
from roadmap.common.logging.error_logging import (
    log_database_error,
    log_error_with_context,
)
from roadmap.common.observability.instrumentation import traced
from roadmap.common.services import log_entry, log_event, log_exit, log_metric
from roadmap.common.utils.timezone_utils import now_utc
from roadmap.core.domain.milestone import Milestone
from roadmap.core.repositories import IssueRepository, MilestoneRepository
from roadmap.infrastructure.persistence_gateway import PersistenceGateway
from roadmap.infrastructure.validation.file_enumeration import FileEnumerationService

logger = structlog.get_logger()

logger = get_logger(__name__)


class MilestoneService:
    """Service for managing milestones."""

    def __init__(
        self,
        repository: MilestoneRepository,
        issue_repository: IssueRepository | None = None,
        issues_dir: Path | None = None,
        milestones_dir: Path | None = None,
    ):
        """Initialize milestone service.

        Args:
            repository: Repository for milestone persistence
            issue_repository: Optional repository for issue persistence (for progress calculation)
            issues_dir: Optional path to issues directory (for deletion operations)
            milestones_dir: Optional path to milestones directory (for deletion operations)
        """
        self.repository = repository
        self.issue_repository = issue_repository
        self.issues_dir = issues_dir
        self.milestones_dir = milestones_dir

    @safe_operation(OperationType.CREATE, "Milestone", include_traceback=True)
    @traced("create_milestone")
    def create_milestone(
        self,
        name: str,
        headline: str = "",
        due_date: datetime | None = None,
        status: str | None = None,
    ) -> Milestone:
        """Create a new milestone.

        Args:
            name: Milestone name/title
            headline: Milestone headline (short summary)
            due_date: Target completion date
            status: Milestone status (optional, defaults to OPEN)

        Returns:
            Newly created Milestone object
        """
        log_entry(
            "create_milestone",
            name=name,
            has_due_date=due_date is not None,
            status=status,
        )
        logger.info(
            "creating_milestone",
            milestone_name=name,
            has_due_date=due_date is not None,
            status=status,
        )
        log_event("milestone_creation_started", milestone_name=name)

        # Map status string to MilestoneStatus enum if provided
        from roadmap.common.constants import MilestoneStatus

        milestone_status = MilestoneStatus(status) if status else MilestoneStatus.OPEN

        milestone = Milestone(
            name=name,
            headline=headline or "",
            content="",
            due_date=due_date,
            status=milestone_status,
        )

        # Persist using repository abstraction
        try:
            self.repository.save(milestone)
        except Exception as e:
            log_database_error(
                e,
                operation="create",
                entity_type="Milestone",
                entity_id=name,
            )
            raise

        log_event("milestone_created", milestone_name=milestone.name)
        log_exit("create_milestone", milestone_name=milestone.name)
        return milestone

    @traced("list_milestones")
    def list_milestones(self, status: MilestoneStatus | None = None) -> list[Milestone]:
        """List all milestones with optional status filter.

        Args:
            status: Optional status filter

        Returns:
            List of Milestone objects sorted by due date then name
        """
        log_entry("list_milestones", status_filter=status)
        try:
            milestones = self.repository.list()
        except Exception as e:
            log_database_error(
                e,
                operation="list",
                entity_type="Milestone",
            )
            logger.warning(
                "returning_empty_milestone_list_due_to_error", severity="operational"
            )
            return []

        # Filter by status if provided
        if status:
            try:
                milestones = [m for m in milestones if m.status == status]
            except Exception as e:
                log_error_with_context(
                    e,
                    operation="filter_milestones",
                    entity_type="Milestone",
                    additional_context={"status_filter": status},
                )
                return []

        log_metric("milestones_enumerated", len(milestones))

        # Sort by due date (earliest first), then by name
        def get_sortable_date(milestone):
            if milestone.due_date is None:
                return datetime.max
            # Convert timezone-aware to naive for comparison
            if milestone.due_date.tzinfo is not None:
                return milestone.due_date.replace(tzinfo=None)
            return milestone.due_date

        milestones.sort(key=lambda x: (get_sortable_date(x), x.name))
        log_exit("list_milestones", milestone_count=len(milestones))
        return milestones

    @traced("get_milestone")
    def get_milestone(self, name: str) -> Milestone | None:
        """Get a specific milestone by name.

        Args:
            name: Milestone name

        Returns:
            Milestone object if found, None otherwise
        """
        log_entry("get_milestone", milestone_name=name)

        milestone = self.repository.get(name)

        if milestone:
            log_event("milestone_found", milestone_name=name)
        else:
            log_event("milestone_not_found", milestone_name=name)
        log_exit("get_milestone", found=milestone is not None)
        return milestone

    @safe_operation(OperationType.UPDATE, "Milestone")
    @traced("update_milestone")
    def update_milestone(
        self,
        name: str,
        headline: str | None = None,
        due_date: datetime | None = None,
        clear_due_date: bool = False,
        status: str | None = None,
    ) -> Milestone | None:
        """Update a milestone's properties.

        Args:
            name: Milestone name
            headline: New headline (None to keep current)
            due_date: New due date (None to keep current)
            clear_due_date: If True, remove the due date
            status: New status

        Returns:
            Updated Milestone object if found, None otherwise
        """
        log_entry(
            "update_milestone",
            milestone_name=name,
            fields=["headline", "due_date", "status"],
        )
        logger.info(
            "updating_milestone",
            milestone_name=name,
            has_headline=headline is not None,
        )
        milestone = self.get_milestone(name)
        if not milestone:
            log_event("milestone_not_found", milestone_name=name)
            log_exit("update_milestone", success=False)
            return None

        # Update fields if provided
        if headline is not None:
            milestone.headline = headline
            log_event("milestone_field_updated", milestone_name=name, field="headline")

        if clear_due_date:
            milestone.due_date = None
            log_event(
                "milestone_field_updated",
                milestone_name=name,
                field="due_date",
                action="cleared",
            )
        elif due_date is not None:
            milestone.due_date = due_date
            log_event("milestone_field_updated", milestone_name=name, field="due_date")

        if status is not None:
            milestone.status = MilestoneStatus(status)
            log_event(
                "milestone_field_updated",
                milestone_name=name,
                field="status",
                value=status,
            )

        milestone.updated = now_utc()

        # Persist using repository
        self.repository.save(milestone)
        log_event("milestone_saved", milestone_name=name)
        log_exit("update_milestone", milestone_name=name, success=True)
        return milestone

    @safe_operation(OperationType.DELETE, "Milestone", include_traceback=True)
    @traced("delete_milestone")
    def delete_milestone(self, name: str) -> bool:
        """Delete a milestone and unassign all issues from it.

        Args:
            name: Milestone name

        Returns:
            True if deleted, False if not found
        """
        log_entry("delete_milestone", milestone_name=name)
        logger.info("deleting_milestone", milestone_name=name)
        # Check if milestone exists
        milestone = self.get_milestone(name)
        if not milestone:
            log_event("milestone_not_found", milestone_name=name)
            log_exit("delete_milestone", success=False)
            return False

        # Unassign all issues from this milestone
        if self.issues_dir:
            issues = FileEnumerationService.enumerate_and_parse(
                self.issues_dir,
                PersistenceGateway.parse_issue_file,
            )
            log_metric("issues_enumerated_for_unassignment", len(issues))

            unassigned_count = 0
            for issue in issues:
                if issue.milestone == name:
                    issue.milestone = None
                    issue.updated = now_utc()
                    # Find and save the issue file
                    for issue_file in self.issues_dir.rglob("*.md"):
                        try:
                            test_issue = PersistenceGateway.parse_issue_file(issue_file)
                            if test_issue.id == issue.id:
                                PersistenceGateway.save_issue_file(issue, issue_file)
                                unassigned_count += 1
                                break
                        except Exception as e:
                            logger.debug(
                                "issue_unassign_failed",
                                error=str(e),
                                action="unassign_issue",
                            )
                            continue

        log_metric("issues_unassigned", unassigned_count)
        # Delete the milestone file
        if self.milestones_dir:
            for milestone_file in self.milestones_dir.rglob("*.md"):
                try:
                    test_milestone = PersistenceGateway.parse_milestone_file(
                        milestone_file
                    )
                    if test_milestone.name == name:
                        milestone_file.unlink()
                        log_event(
                            "milestone_deleted",
                            milestone_name=name,
                            issues_unassigned=unassigned_count,
                        )
                        log_exit("delete_milestone", success=True)
                        return True
                except Exception as e:
                    logger.debug(
                        "milestone_delete_failed",
                        error=str(e),
                        action="delete_milestone",
                    )
                    continue
        log_exit("delete_milestone", success=False)
        return False

    @traced("get_milestone_progress")
    def get_milestone_progress(self, milestone_name: str) -> dict[str, Any]:
        """Get progress statistics for a milestone.

        Args:
            milestone_name: Milestone name

        Returns:
            Dict with total, completed, progress percentage, and status breakdown
        """
        log_entry("get_milestone_progress", milestone_name=milestone_name)

        # If no issue repository available, return empty progress
        if not self.issue_repository:
            log_exit("get_milestone_progress", total=0)
            return {"total": 0, "completed": 0, "progress": 0.0, "by_status": {}}

        issues = self.issue_repository.list()

        # Filter issues for this milestone
        milestone_issues = [i for i in issues if i.milestone == milestone_name]

        if not milestone_issues:
            log_metric("milestone_progress", 0, milestone=milestone_name)
            log_exit("get_milestone_progress", total=0)
            return {"total": 0, "completed": 0, "progress": 0.0, "by_status": {}}

        total = len(milestone_issues)
        completed = len([i for i in milestone_issues if i.status == Status.CLOSED])
        progress = (completed / total) * 100 if total > 0 else 0.0

        by_status = {}
        for status in Status:
            by_status[status.value] = len(
                [i for i in milestone_issues if i.status == status]
            )

        log_metric(
            "milestone_progress",
            progress,
            milestone=milestone_name,
            total=total,
            completed=completed,
        )
        log_exit("get_milestone_progress", total=total, completed=completed)
        return {
            "total": total,
            "completed": completed,
            "progress": progress,
            "by_status": by_status,
        }

    @safe_operation(OperationType.UPDATE, "Milestone")
    def close_milestone(self, name: str) -> Milestone | None:
        """Close/mark milestone as closed.

        Args:
            name: Milestone name

        Returns:
            Closed Milestone object if found, None otherwise
        """
        log_entry("close_milestone", milestone_name=name)
        logger.info("closing_milestone", milestone_name=name)
        result = self.update_milestone(name, status=MilestoneStatus.CLOSED.value)
        if result:
            log_event("milestone_closed", milestone_name=name)
        log_exit("close_milestone", success=result is not None)
        return result
