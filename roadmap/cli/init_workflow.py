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

from roadmap.application.core import RoadmapCore
from roadmap.cli.utils import get_console

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

        if not force:
            return False, "Roadmap already initialized. Use --force to reinitialize."

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
