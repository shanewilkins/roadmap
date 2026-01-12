"""Project service - handles all project-related operations.

The ProjectService manages:
- Project listing and retrieval
- Project saving/persistence
- Milestone-based progress calculation
- Project completion tracking

Extracted from core.py to separate business logic.
"""

import time
from pathlib import Path
from typing import Any

from roadmap.adapters.persistence.parser import MilestoneParser
from roadmap.common.constants import MilestoneStatus, ProjectStatus
from roadmap.common.errors import OperationType, safe_operation
from roadmap.common.logging import get_logger
from roadmap.common.logging_utils import (
    log_collection_operation,
    log_event,
    log_metric,
)
from roadmap.common.timezone_utils import now_utc
from roadmap.core.domain.project import Project
from roadmap.core.repositories import ProjectRepository
from roadmap.infrastructure.file_enumeration import FileEnumerationService
from roadmap.infrastructure.logging.error_logging import (
    log_database_error,
)
from roadmap.shared.instrumentation import traced

logger = get_logger(__name__)


class ProjectService:
    """Service for managing projects."""

    def __init__(
        self, repository: ProjectRepository, milestones_dir: Path | None = None
    ):
        """Initialize project service.

        Args:
            repository: Repository for project persistence
            milestones_dir: Path to milestones directory (for progress calc, optional)
        """
        self.repository = repository
        self.milestones_dir = milestones_dir

    @traced("list_projects")
    def list_projects(self) -> list[Project]:
        """List all projects.

        Returns:
            List of Project objects sorted by creation date
        """
        start_time = time.time()
        logger.debug("listing_projects_start")

        try:
            projects = self.repository.list()
        except Exception as e:
            log_database_error(
                e,
                operation="list",
                entity_type="Project",
            )
            logger.warning("returning_empty_project_list_due_to_error")
            return []

        elapsed = time.time() - start_time

        log_collection_operation("projects", len(projects), "retrieved", level="debug")
        log_metric("list_projects_duration", elapsed, unit="seconds", level="debug")
        logger.debug(
            "listing_projects_complete",
            count=len(projects),
            elapsed_seconds=round(elapsed, 3),
        )

        return projects

    @traced("get_project")
    def get_project(self, project_id: str) -> Project | None:
        """Get a specific project by ID.

        Args:
            project_id: Project identifier

        Returns:
            Project object if found, None otherwise
        """
        start_time = time.time()
        logger.debug("get_project_start", project_id=project_id)

        try:
            result = self.repository.get(project_id)
        except Exception as e:
            log_database_error(
                e,
                operation="read",
                entity_type="Project",
                entity_id=project_id,
            )
            return None

        elapsed = time.time() - start_time

        if result:
            logger.debug(
                "get_project_found",
                project_id=project_id,
                project_name=result.name,
                elapsed_seconds=round(elapsed, 3),
            )
        else:
            logger.debug(
                "get_project_not_found",
                project_id=project_id,
                elapsed_seconds=round(elapsed, 3),
            )

        return result

    @safe_operation(OperationType.UPDATE, "Project")
    def save_project(self, project: Project) -> bool:
        """Save an updated project to disk.

        Args:
            project: Project object to save

        Returns:
            True if saved, False on error
        """
        start_time = time.time()
        logger.debug(
            "saving_project_start", project_id=project.id, project_name=project.name
        )

        project.updated = now_utc()
        try:
            self.repository.save(project)
        except Exception as e:
            log_database_error(
                e,
                operation="update",
                entity_type="Project",
                entity_id=project.id,
            )
            raise

        elapsed = time.time() - start_time
        log_event("project_saved", project_id=project.id)
        logger.info(
            "saving_project_complete",
            project_id=project.id,
            elapsed_seconds=round(elapsed, 3),
        )
        return True

    @safe_operation(OperationType.CREATE, "Project", include_traceback=True)
    @traced("create_project")
    def create_project(
        self,
        name: str,
        headline: str = "",
        milestones: list | None = None,
        status: str | None = None,
    ) -> Project:
        """Create a new project.

        Args:
            name: Project name
            headline: Project headline (short summary)
            milestones: List of associated milestone names
            status: Project status (optional)

        Returns:
            Newly created Project object
        """
        start_time = time.time()
        logger.info(
            "creating_project_start",
            project_name=name,
            milestones_count=len(milestones or []),
            status=status,
        )

        # Map status string to ProjectStatus enum if provided

        status_str = status if status else "planning"
        # Ensure static type checkers understand this is a ProjectStatus
        project_status: ProjectStatus = ProjectStatus(status_str)

        project = Project(
            name=name,
            headline=headline or "",
            content="",
            milestones=milestones or [],
            status=project_status,
        )

        self.save_project(project)
        elapsed = time.time() - start_time

        log_event("project_created", project_id=project.id, project_name=name)
        logger.info(
            "creating_project_complete",
            project_id=project.id,
            project_name=name,
            elapsed_seconds=round(elapsed, 3),
        )

        return project

    @safe_operation(OperationType.UPDATE, "Project")
    @traced("update_project")
    def update_project(self, project_id: str, **updates) -> Project | None:
        """Update a project.

        Args:
            project_id: Project identifier
            **updates: Fields to update

        Returns:
            Updated Project object if found, None otherwise
        """
        start_time = time.time()
        logger.info(
            "updating_project_start",
            project_id=project_id,
            field_count=len(updates),
            fields=list(updates.keys()),
        )

        project = self.get_project(project_id)
        if not project:
            logger.warning("updating_project_not_found", project_id=project_id)
            return None

        # Capture old state for change logging
        old_state = {k: getattr(project, k, None) for k in updates.keys()}

        # Update fields
        for field, value in updates.items():
            if hasattr(project, field):
                setattr(project, field, value)

        self.save_project(project)
        elapsed = time.time() - start_time

        # Log state changes
        new_state = {k: getattr(project, k, None) for k in updates.keys()}
        changed_fields = [
            k for k in updates.keys() if old_state.get(k) != new_state.get(k)
        ]

        log_event(
            "project_updated", project_id=project_id, updated_fields=changed_fields
        )
        logger.info(
            "updating_project_complete",
            project_id=project_id,
            field_count=len(updates),
            changed_count=len(changed_fields),
            elapsed_seconds=round(elapsed, 3),
        )

        return project

    @safe_operation(OperationType.DELETE, "Project", include_traceback=True)
    def delete_project(self, project_id: str) -> bool:
        """Delete a project.

        Args:
            project_id: Project identifier

        Returns:
            True if deleted, False if not found
        """
        start_time = time.time()
        logger.info("deleting_project_start", project_id=project_id)

        project = self.get_project(project_id)
        if not project:
            elapsed = time.time() - start_time
            logger.warning(
                "deleting_project_not_found",
                project_id=project_id,
                elapsed_seconds=round(elapsed, 3),
            )
            return False

        project_name = project.name
        success = self.repository.delete(project_id)
        elapsed = time.time() - start_time

        if success:
            log_event(
                "project_deleted",
                project_id=project_id,
                project_name=project_name,
            )
            logger.info(
                "deleting_project_complete",
                project_id=project_id,
                project_name=project_name,
                elapsed_seconds=round(elapsed, 3),
            )
        return success

    def calculate_progress(self, project_id: str) -> dict[str, Any]:
        """Calculate project progress based on associated milestones.

        Returns dict with:
        - total_milestones: Total milestones in project
        - completed_milestones: Completed milestones
        - progress: Percentage complete
        - milestone_status: Status breakdown by milestone

        Args:
            project_id: Project identifier

        Returns:
            Dict with progress metrics
        """
        start_time = time.time()
        logger.debug("calculate_progress_start", project_id=project_id)

        project = self.get_project(project_id)
        if not project:
            logger.warning(
                "calculate_progress_project_not_found", project_id=project_id
            )
            return {
                "total_milestones": 0,
                "completed_milestones": 0,
                "progress": 0.0,
                "milestone_status": {},
            }

        # Get milestones for this project
        if not self.milestones_dir:
            return {
                "total_milestones": len(project.milestones),
                "completed_milestones": 0,
                "progress": 0.0,
                "milestone_status": {},
            }

        milestones = FileEnumerationService.enumerate_and_parse(
            self.milestones_dir,
            MilestoneParser.parse_milestone_file,
        )

        # Build lookup for project's milestones
        milestone_statuses = {}
        completed_count = 0

        for milestone_name in project.milestones:
            for milestone in milestones:
                if milestone.name == milestone_name:
                    milestone_statuses[milestone_name] = milestone.status.value
                    if milestone.status == MilestoneStatus.CLOSED:
                        completed_count += 1
                    break

        total = len(project.milestones)
        progress = (completed_count / total * 100) if total > 0 else 0.0
        elapsed = time.time() - start_time

        result = {
            "total_milestones": total,
            "completed_milestones": completed_count,
            "progress": progress,
            "milestone_status": milestone_statuses,
        }

        log_metric(
            "project_progress",
            progress,
            unit="percent",
            project_id=project_id,
            level="debug",
        )
        logger.debug(
            "calculate_progress_complete",
            project_id=project_id,
            total_milestones=total,
            completed_milestones=completed_count,
            progress_percent=round(progress, 1),
            elapsed_seconds=round(elapsed, 3),
        )

        return result

    def complete_project(self, project_id: str) -> Project | None:
        """Mark a project as completed.

        Args:
            project_id: Project identifier

        Returns:
            Completed Project object if found, None otherwise
        """
        from roadmap.core.domain.project import ProjectStatus

        logger.info("completing_project_start", project_id=project_id)
        result = self.update_project(project_id, status=ProjectStatus.COMPLETED)

        if result:
            log_event(
                "project_completed", project_id=project_id, project_name=result.name
            )
            logger.info("completing_project_complete", project_id=project_id)
        else:
            logger.warning("completing_project_not_found", project_id=project_id)

        return result
