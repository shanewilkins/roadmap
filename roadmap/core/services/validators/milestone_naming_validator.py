"""Validator for milestone naming conventions."""

import re
from pathlib import Path


class MilestoneNamingValidator:
    """Validates milestone names against naming conventions.

    Convention:
    - Display names should match safe filenames (no conversion needed)
    - Allowed characters: alphanumeric, hyphens, underscores
    - Must start with alphanumeric
    - Recommended patterns:
      - Versions: v0.7.0, v0.8.0, v1.0.0 (no conversion needed)
      - Sprints: sprint-1, sprint-q1-2025
      - Phases: phase-1, phase-beta
      - Releases: release-dec-2025, release-2025-q1
      - Backlog: backlog
    """

    # Pattern: alphanumeric, hyphens, underscores. Can contain dots only in version pattern
    # Examples: v0.7.0, v080, sprint-1, phase-beta, backlog
    VALID_PATTERN = re.compile(
        r"^[a-zA-Z0-9][a-zA-Z0-9._\-]*[a-zA-Z0-9]$|^[a-zA-Z0-9]$"
    )

    @staticmethod
    def is_valid_name(name: str) -> bool:
        """Check if a milestone name is valid.

        Args:
            name: The milestone name to validate

        Returns:
            True if valid, False otherwise
        """
        if not name or len(name) == 0:
            return False

        # Must match pattern
        if not MilestoneNamingValidator.VALID_PATTERN.match(name):
            return False

        # Should not have consecutive hyphens or underscores
        if "--" in name or "__" in name:
            return False

        return True

    @staticmethod
    def get_safe_name(name: str) -> str:
        """Convert a milestone name to safe filename format.

        Args:
            name: The milestone name

        Returns:
            Safe filename version (lowercase, spaces→hyphens, etc.)
        """
        # Remove/replace invalid chars
        safe = "".join(c for c in name if c.isalnum() or c in (".", "-", "_")).strip()

        # Replace spaces with hyphens
        safe = safe.replace(" ", "-")

        # Lowercase
        safe = safe.lower()

        return safe

    @staticmethod
    def validate_with_feedback(name: str) -> tuple[bool, str | None]:
        """Validate a name and provide feedback.

        Args:
            name: The milestone name to validate

        Returns:
            Tuple of (is_valid, error_message)
            If valid, error_message is None
        """
        if not name:
            return False, "Milestone name cannot be empty"

        if len(name) > 100:
            return False, "Milestone name must be 100 characters or less"

        if not MilestoneNamingValidator.VALID_PATTERN.match(name):
            return False, (
                "Milestone name must contain only alphanumeric characters, "
                "hyphens, underscores, and dots. "
                f"Got: '{name}'. "
                "Examples: v0.7.0, sprint-1, phase-beta, backlog"
            )

        if "--" in name or "__" in name:
            return (
                False,
                "Milestone name cannot contain consecutive hyphens or underscores",
            )

        # Warn if safe name differs from display name (lossy conversion)
        safe = MilestoneNamingValidator.get_safe_name(name)
        if safe != name:
            return False, (
                f"Milestone name will be converted to '{safe}' for filesystem. "
                "To avoid confusion, use the filesystem name directly. "
                f"Suggested: '{safe}'"
            )

        return True, None

    @staticmethod
    def find_naming_conflicts(milestones_dir: Path) -> list[tuple[str, str]]:
        """Find milestone names that could create naming conflicts.

        Args:
            milestones_dir: Path to .roadmap/milestones/

        Returns:
            List of (display_name, safe_name) pairs that might conflict
        """
        conflicts = []
        safe_name_to_display = {}

        if not milestones_dir.exists():
            return conflicts

        for f in milestones_dir.glob("*.md"):
            display_name = f.stem
            safe_name = MilestoneNamingValidator.get_safe_name(display_name)

            if safe_name != display_name:
                conflicts.append((display_name, safe_name))

            # Check for collision (two different display names → same safe name)
            if safe_name in safe_name_to_display:
                other = safe_name_to_display[safe_name]
                if other != display_name:
                    conflicts.append((display_name, safe_name))
            else:
                safe_name_to_display[safe_name] = display_name

        return conflicts
