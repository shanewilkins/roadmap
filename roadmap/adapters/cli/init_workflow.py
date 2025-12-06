"""
Initialization workflow service for roadmap CLI.
Extracts complex initialization logic from the init command.
"""

import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from roadmap.common.console import get_console
from roadmap.common.security import create_secure_directory
from roadmap.infrastructure.core import RoadmapCore

console = get_console()


class InitializationLock:
    """Manages initialization lockfile to prevent concurrent inits."""

    def __init__(self, lock_path: Path):
        self.lock_path = lock_path

    def acquire(self) -> bool:
        """Acquire the lock. Returns False if already locked."""
        if self.lock_path.exists():
            return False
        try:
            self.lock_path.write_text(
                f"pid:{os.getpid()}\nstarted:{datetime.now().isoformat()}\n"
            )
            return True
        except Exception:
            console.print(
                "⚠️  Could not create init lockfile; proceeding with care",
                style="yellow",
            )
            return True  # Continue anyway

    def release(self) -> None:
        """Release the lock."""
        try:
            if self.lock_path.exists():
                self.lock_path.unlink()
        except Exception:
            pass


class InitializationManifest:
    """Tracks created files/directories for potential rollback."""

    def __init__(self, manifest_file: Path):
        self.manifest_file = manifest_file
        self.data: dict[str, list] = {"created": []}

    def add_path(self, path: Path) -> None:
        """Add a path to the manifest."""
        if path.exists():
            self.data["created"].append(str(path))
            self._save()

    def _save(self) -> None:
        """Save manifest to disk (best effort)."""
        try:
            self.manifest_file.write_text(json.dumps(self.data))
        except Exception:
            pass

    def rollback(self) -> None:
        """Remove all paths tracked in the manifest."""
        if not self.manifest_file.exists():
            return

        try:
            data = json.loads(self.manifest_file.read_text())
            for p in data.get("created", []):
                try:
                    ppath = Path(p)
                    if ppath.is_file():
                        ppath.unlink()
                    elif ppath.is_dir():
                        shutil.rmtree(ppath)
                except Exception:
                    pass
        except Exception:
            pass


class InitializationValidator:
    """Validates initialization prerequisites and results."""

    @staticmethod
    def check_existing_roadmap(
        core: RoadmapCore, force: bool
    ) -> tuple[bool, str | None]:
        """
        Check if roadmap already exists.

        Returns:
            Tuple of (should_continue, error_message)
        """
        if not core.is_initialized():
            return True, None

        # If force is true, we'll be doing a full reset
        if force:
            return True, None

        # If roadmap exists but force is not specified, we allow init to continue
        # to update config/metadata without destroying existing data
        return True, None

    @staticmethod
    def validate_lockfile(lock_path: Path) -> tuple[bool, str | None]:
        """Check for concurrent initialization."""
        if lock_path.exists():
            return (
                False,
                "Initialization already in progress (lockfile present). Try again later.",
            )
        return True, None

    @staticmethod
    def post_init_validate(
        core: RoadmapCore, name: str, project_info: dict[str, Any] | None
    ) -> bool:
        """
        Validate initialization results.

        Returns:
            True if validation passed, False if warnings were found
        """
        warnings = []

        # Check core directories
        if not core.roadmap_dir.exists():
            warnings.append(f"Roadmap directory {name}/ not found")
        if not core.config_file.exists():
            warnings.append("Config file not created")

        # Check project if one was supposed to be created
        if project_info and not core.projects_dir.exists():
            warnings.append("Projects directory not created")

        if warnings:
            console.print("⚠️  Validation warnings:", style="yellow")
            for warning in warnings:
                console.print(f"  - {warning}", style="yellow")
            return False

        return True


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
            self.core._update_gitignore()

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

        # Otherwise create them
        self.core._create_default_templates()

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


def show_dry_run_info(
    name: str, is_initialized: bool, force: bool, skip_project: bool, skip_github: bool
) -> None:
    """Display dry-run information without making changes."""
    console.print("🚀 Roadmap CLI Initialization", style="bold cyan")
    console.print()
    console.print("ℹ️  Dry run mode enabled - no changes will be made.", style="yellow")

    if is_initialized and force:
        console.print(
            f"🟡 Would remove existing {name}/ and reinitialize", style="yellow"
        )
    elif is_initialized:
        console.print(
            f"❌ Roadmap already initialized in {name}/ directory", style="bold red"
        )
        console.print("Tip: use --force to reinitialize", style="yellow")
    else:
        actions = [
            f"Create roadmap directory: {name}/",
            "Create default templates and config",
        ]
        if not skip_project:
            actions.append("Create main project")
        if not skip_github:
            actions.append("Optionally configure GitHub")

        console.print("Planned actions:")
        for action in actions:
            console.print(f" - {action}")
