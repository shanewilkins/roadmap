"""Validation utilities for initialization workflow."""

from pathlib import Path
from typing import Any

from roadmap.common.console import get_console
from roadmap.infrastructure.core import RoadmapCore

console = get_console()


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
