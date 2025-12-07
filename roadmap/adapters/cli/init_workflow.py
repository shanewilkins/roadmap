"""
Initialization workflow service for roadmap CLI.
Orchestrates the core initialization workflow steps.
"""

import shutil
from pathlib import Path

from roadmap.common.console import get_console
from roadmap.common.security import create_secure_directory
from roadmap.infrastructure.core import RoadmapCore

from .init_utils import InitializationManifest

console = get_console()


class InitializationWorkflow:
    """Orchestrates the initialization workflow steps."""

    def __init__(self, core: RoadmapCore):
        self.core = core

    def cleanup_existing(self) -> bool:
        """
        Remove existing roadmap directory.

        Returns:
            True if successful, False otherwise
        """
        try:
            if self.core.roadmap_dir.exists():
                shutil.rmtree(self.core.roadmap_dir)
            return True
        except Exception as e:
            console.print(
                f"❌ Failed to remove existing roadmap: {e}", style="bold red"
            )
            return False

    def create_structure(self) -> None:
        """Create the basic roadmap structure."""
        self.core.initialize()

    def create_structure_preserve_data(self) -> bool:
        """Create roadmap structure while preserving existing data.

        If roadmap already exists, creates only missing directories and templates.
        Returns True if successful, False otherwise.
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
            console.print(f"❌ Failed to create structure: {e}", style="bold red")
            return False

    def _create_missing_templates(self) -> None:
        """Create template files only if they don't exist."""
        templates_dir = self.core.templates_dir

        # Check if templates already exist
        if list(templates_dir.glob("*.md")):
            return  # Templates already exist, skip

        # Otherwise create them via initialization manager
        self.core._init_manager._create_default_templates()

    def generate_config_file(self, user_name: str | None = None) -> None:
        """Generate the config file with user information.

        Args:
            user_name: User name to store in config, auto-detected if None
        """
        from roadmap.common.config_manager import ConfigManager

        # Auto-detect user if not provided
        if not user_name:
            user_name = ConfigManager.auto_detect_user()
            if not user_name:
                user_name = "unknown"

        # Auto-detect GitHub info
        github_owner = ConfigManager.auto_detect_github_username()

        # Create default config
        config = ConfigManager.create_default_config(
            user_name=user_name,
            github_owner=github_owner,
            github_repo=None,  # User would configure repo separately
            github_enabled=False,  # Disabled by default
        )

        # Save config
        manager = ConfigManager(self.core.config_file)
        manager.save(config)

    def ensure_gitignore_entry(self) -> None:
        """Ensure config.yaml is in .gitignore to prevent accidental commits."""
        gitignore_path = Path.cwd() / ".gitignore"
        config_entry = ".roadmap/config.yaml"
        config_entry_with_comment = (
            ".roadmap/config.yaml  # Local user configuration (not to be shared)"
        )

        # If .gitignore doesn't exist, create it
        if not gitignore_path.exists():
            gitignore_path.write_text(
                f"{config_entry_with_comment}\n" ".env.local\n" ".env.*.local\n"
            )
            return

        # Read existing .gitignore
        content = gitignore_path.read_text()

        # Check if entry already exists (with or without comment)
        if config_entry in content:
            return  # Already there

        # Append entry to .gitignore
        if not content.endswith("\n"):
            content += "\n"

        content += f"\n{config_entry_with_comment}\n"
        gitignore_path.write_text(content)

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
            except Exception:
                pass
