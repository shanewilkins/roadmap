"""Data validation and consistency orchestrator.

Handles validation of roadmap data structure and consistency checks.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ...infrastructure.milestone_consistency_validator import (
    MilestoneConsistencyValidator,
)

if TYPE_CHECKING:
    from ..core import RoadmapCore


class ValidationOrchestrator:
    """Orchestrates validation and consistency checking operations."""

    def __init__(self, core: RoadmapCore):
        """Initialize with reference to parent RoadmapCore.

        Args:
            core: Parent RoadmapCore instance
        """
        self.core = core
        self.milestones_dir = core.milestones_dir
        self._consistency_validator = MilestoneConsistencyValidator(self.milestones_dir)

    def validate_milestone_naming_consistency(self) -> list[dict[str, str]]:
        """Check for inconsistencies between milestone filenames and name fields.

        Returns:
            List of dictionaries with inconsistency details
        """
        return self._consistency_validator.validate()

    def fix_milestone_naming_consistency(self) -> dict[str, list[str]]:
        """Fix milestone filename inconsistencies by renaming files to match name fields.

        Returns:
            Dictionary with 'renamed' and 'errors' lists
        """
        return self._consistency_validator.fix()
