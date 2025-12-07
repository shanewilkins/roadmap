"""Service for orchestrating the initialization workflow."""

from pathlib import Path
from typing import Any

from roadmap.adapters.cli.services.project_initialization_service import (
    ProjectCreationService,
    ProjectDetectionService,
)
from roadmap.core.services.initialization import (
    InitializationLock,
    InitializationManifest,
    InitializationValidator,
    InitializationWorkflow,
)
from roadmap.infrastructure.core import RoadmapCore


class InitializationOrchestrationService:
    """Orchestrates the initialization workflow."""

    @staticmethod
    def validate_prerequisites(
        custom_core: RoadmapCore, force: bool
    ) -> tuple[bool, str | None]:
        """Validate initialization prerequisites.

        Returns:
            (is_valid, error_message)
        """
        lock_path = Path.cwd() / ".roadmap_init.lock"
        is_valid, error_msg = InitializationValidator.validate_lockfile(lock_path)
        if not is_valid:
            return False, error_msg

        is_valid, error_msg = InitializationValidator.check_existing_roadmap(
            custom_core, force
        )
        if not is_valid:
            return False, error_msg

        return True, None

    @staticmethod
    def acquire_lock() -> tuple[InitializationLock | None, str | None]:
        """Acquire initialization lock.

        Returns:
            (lock_object, error_message)
        """
        lock_path = Path.cwd() / ".roadmap_init.lock"
        lock = InitializationLock(lock_path)
        if not lock.acquire():
            return None, "Initialization already in progress. Try again later."
        return lock, None

    @staticmethod
    def handle_force_reinitialization(custom_core: RoadmapCore, force: bool) -> bool:
        """Handle force re-initialization cleanup.

        Returns:
            Success status
        """
        if custom_core.is_initialized() and force:
            workflow = InitializationWorkflow(custom_core)
            return workflow.cleanup_existing()
        return True

    @staticmethod
    def create_structure(
        custom_core: RoadmapCore,
    ) -> tuple[bool, InitializationManifest]:
        """Create roadmap structure and config.

        Returns:
            (success, manifest)
        """
        manifest = InitializationManifest(
            custom_core.roadmap_dir / ".init_manifest.json"
        )
        workflow = InitializationWorkflow(custom_core)

        if not workflow.create_structure_preserve_data():
            return False, manifest

        workflow.generate_config_file()
        workflow.record_created_paths(manifest)
        workflow.ensure_gitignore_entry()

        return True, manifest

    @staticmethod
    def detect_or_create_project(
        custom_core: RoadmapCore,
        manifest: InitializationManifest,
        project_name: str | None,
        description: str | None,
        detected_info: dict,
        skip_project: bool,
        interactive: bool,
        template: str,
        yes: bool,
        template_path: str | None,
    ) -> dict[str, Any] | None:
        """Detect existing projects or create new main project.

        Returns:
            Project info dict or None
        """
        if skip_project:
            return None

        # Check for existing projects
        existing_projects = ProjectDetectionService.detect_existing_projects(
            custom_core.projects_dir
        )

        if existing_projects:
            # Return info about first existing project
            return {
                "name": existing_projects[0]["name"],
                "id": existing_projects[0]["id"],
                "action": "joined",
                "count": len(existing_projects),
            }

        # Create new project
        project_info = ProjectCreationService.create_project(
            custom_core,
            project_name or detected_info.get("project_name", Path.cwd().name),
            description or "A project managed with Roadmap CLI",
            detected_info,
            template,
            template_path,
        )

        if project_info and "filename" in project_info:
            project_file = (
                custom_core.roadmap_dir / "projects" / project_info["filename"]
            )
            manifest.add_path(project_file)
            project_info["action"] = "created"

        return project_info

    @staticmethod
    def validate_and_return_status(
        custom_core: RoadmapCore, name: str, project_info: dict | None
    ) -> bool:
        """Validate post-initialization state.

        Returns:
            Validation success status
        """
        return InitializationValidator.post_init_validate(
            custom_core, name, project_info
        )

    @staticmethod
    def cleanup_on_error(
        manifest: InitializationManifest, custom_core: RoadmapCore
    ) -> None:
        """Rollback changes on error."""
        manifest.rollback()
        workflow = InitializationWorkflow(custom_core)
        workflow.rollback_on_error()
