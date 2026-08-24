"""Initialization workflow service for roadmap CLI.

Orchestrates the core initialization workflow steps.
"""

import shutil

import structlog

from roadmap.common.console import get_console
from roadmap.common.errors.exceptions import OperationError
from roadmap.common.security import create_secure_directory
from roadmap.infrastructure.coordination.core import RoadmapCore

from .utils import InitializationManifest

logger = structlog.get_logger()

console = get_console()


class InitializationWorkflow:
    """Orchestrates the initialization workflow steps."""

    def __init__(self, core: RoadmapCore):
        """Initialize InitializationWorkflow.

        Args:
            core: Core roadmap instance.
        """
        self.core = core

    def cleanup_existing(self) -> bool:
        """Remove existing roadmap directory.

        Returns:
            True if successful, False otherwise

        Raises:
            OperationError: If removal fails
        """
        try:
            if self.core.roadmap_dir.exists():
                shutil.rmtree(self.core.roadmap_dir)
            return True
        except Exception as e:
            raise OperationError(
                operation="remove existing roadmap", reason=str(e)
            ) from e

    def create_structure(self) -> None:
        """Create the basic roadmap structure."""
        self.core.initialize()

    def create_structure_preserve_data(self) -> bool:
        """Create roadmap structure while preserving existing data.

        If roadmap already exists, creates only missing directories and templates.
        Returns True if successful, raises OperationError otherwise.

        Raises:
            OperationError: If creation fails
        """
        try:
            roadmap_dir = self.core.roadmap_dir

            # If directory doesn't exist, just do normal init
            if not roadmap_dir.exists():
                self.core.initialize()
                return True

            # Roadmap exists - create only missing parts
            # Ensure subdirectories exist
            for subdir in [
                self.core.issues_dir,
                self.core.milestones_dir,
                self.core.projects_dir,
                self.core.templates_dir,
                self.core.artifacts_dir,
            ]:
                create_secure_directory(subdir, 0o755)

            # Create templates only if missing
            self._create_missing_templates()

            # Update .gitignore (safe to call multiple times)
            self.core._init_manager._update_gitignore()

            return True
        except Exception as e:
            raise OperationError(
                operation="create roadmap structure", reason=str(e)
            ) from e

    def _create_missing_templates(self) -> None:
        """Create template files only if they don't exist."""
        templates_dir = self.core.templates_dir

        # Check if templates already exist
        if list(templates_dir.glob("*.md")):
            return  # Templates already exist, skip

        # Otherwise create them via initialization manager
        self.core._init_manager._create_default_templates()

    def generate_config_file(self, user_name: str | None = None) -> None:
        """Generate scoped project and user configuration.

        Args:
            user_name: User name to store in config, auto-detected if None
        """
        from roadmap.common.configuration import ConfigManager

        # Auto-detect user if not provided
        if not user_name:
            user_name = ConfigManager.auto_detect_user()
            if not user_name:
                user_name = "unknown"

        self.core.configuration.initialize(user_name)

    def ensure_gitignore_entry(self) -> None:
        """Project configuration is canonical and remains commit-visible."""

    def record_created_paths(self, manifest: InitializationManifest) -> None:
        """Record all created paths in the manifest."""
        manifest.add_path(self.core.roadmap_dir)
        manifest.add_path(self.core.projects_dir)
        manifest.add_path(self.core.templates_dir)
        manifest.add_path(self.core.config_file)

    def rollback_on_error(self) -> None:
        """Remove created roadmap directory on error."""
        if self.core.roadmap_dir.exists():
            try:
                shutil.rmtree(self.core.roadmap_dir)
            except Exception as e:
                logger.debug(
                    "roadmap_dir_cleanup_failed",
                    error=str(e),
                    action="cleanup_roadmap_dir",
                )
