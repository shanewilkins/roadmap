"""Initialization service for roadmap CLI.

This module handles project initialization workflow including
project detection, creation, GitHub setup, and validation.
"""

from pathlib import Path
from typing import Any

from roadmap.common.logging import get_logger
from roadmap.common.logging.error_logging import (
    log_error_with_context,
)
from roadmap.common.observability.instrumentation import traced
from roadmap.core.services.initialization import (
    InitializationValidator,
    InitializationWorkflow,
)
from roadmap.core.services.project_init.detection import ProjectDetectionService
from roadmap.infrastructure.coordination.core import RoadmapCore

logger = get_logger(__name__)


class ProjectInitializationService:
    """Orchestrates project initialization workflow."""

    def __init__(self, core: RoadmapCore):
        """Initialize the service.

        Args:
            core: RoadmapCore instance for this initialization
        """
        self.core = core
        self.workflow = InitializationWorkflow(core)

    @traced("validate_prerequisites")
    def validate_prerequisites(self, force: bool = False) -> tuple[bool, str]:
        """Validate initialization prerequisites.

        Args:
            force: Whether force re-initialization is requested

        Returns:
            Tuple of (is_valid, error_message)
        """
        lock_path = Path.cwd() / ".roadmap_init.lock"
        is_valid, error_msg = InitializationValidator.validate_lockfile(lock_path)
        if not is_valid:
            return is_valid, error_msg or ""

        is_valid, error_msg = InitializationValidator.check_existing_roadmap(
            self.core, force
        )
        return is_valid, error_msg or ""

    @traced("handle_force_reinitialization")
    def handle_force_reinitialization(self) -> bool:
        """Handle force re-initialization when roadmap already exists.

        Returns:
            True if successful
        """
        try:
            return self.workflow.cleanup_existing()
        except Exception as e:
            log_error_with_context(
                e,
                operation="cleanup_existing",
                entity_type="Roadmap",
            )
            logger.error(
                "Failed to cleanup existing roadmap",
                error=str(e),
                severity="operational",
            )
            return False

    @traced("detect_existing_projects")
    def detect_existing_projects(self) -> list[dict[str, Any]]:
        """Detect existing projects in the roadmap.

        Returns:
            List of project info dictionaries
        """
        projects_dir = self.core.roadmap_dir / "projects"
        return ProjectDetectionService.detect_existing_projects(projects_dir)

    @traced("validate_finalization")
    def validate_finalization(self, project_info: dict[str, Any] | None = None) -> bool:
        """Validate the initialized roadmap and finalize.

        Args:
            project_info: Project info dict if project was created

        Returns:
            True if validation passes
        """
        try:
            return InitializationValidator.post_init_validate(
                self.core, self.core.roadmap_dir.name, project_info
            )
        except Exception as e:
            log_error_with_context(
                e,
                operation="post_init_validate",
                entity_type="Roadmap",
                additional_context={"project_info": project_info},
            )
            logger.error("Validation failed", error=str(e), severity="operational")
            return False
