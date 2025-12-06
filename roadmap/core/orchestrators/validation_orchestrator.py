"""Data validation and consistency orchestrator.

Handles validation of roadmap data structure and consistency checks.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ...infrastructure.persistence.parser import MilestoneParser

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

    def validate_milestone_naming_consistency(self) -> list[dict[str, str]]:
        """Check for inconsistencies between milestone filenames and name fields.

        Returns:
            List of dictionaries with inconsistency details
        """
        inconsistencies = []

        for milestone_file in self.milestones_dir.rglob("*.md"):
            try:
                milestone = MilestoneParser.parse_milestone_file(milestone_file)
                expected_filename = milestone.filename
                actual_filename = milestone_file.name

                if expected_filename != actual_filename:
                    inconsistencies.append(
                        {
                            "file": actual_filename,
                            "name": milestone.name,
                            "expected_filename": expected_filename,
                            "type": "filename_mismatch",
                        }
                    )
            except Exception as e:
                inconsistencies.append(
                    {
                        "file": milestone_file.name,
                        "name": "PARSE_ERROR",
                        "expected_filename": "N/A",
                        "type": "parse_error",
                        "error": str(e),
                    }
                )

        return inconsistencies

    def fix_milestone_naming_consistency(self) -> dict[str, list[str]]:
        """Fix milestone filename inconsistencies by renaming files to match name fields.

        Returns:
            Dictionary with 'renamed' and 'errors' lists
        """
        results = {"renamed": [], "errors": []}
        inconsistencies = self.validate_milestone_naming_consistency()

        for issue in inconsistencies:
            if issue["type"] == "filename_mismatch":
                old_path = self.milestones_dir / issue["file"]
                new_path = self.milestones_dir / issue["expected_filename"]

                try:
                    # Check if target filename already exists
                    if new_path.exists():
                        results["errors"].append(
                            f"Cannot rename {issue['file']} -> {issue['expected_filename']}: target exists"
                        )
                        continue

                    old_path.rename(new_path)
                    results["renamed"].append(
                        f"{issue['file']} -> {issue['expected_filename']}"
                    )
                except Exception as e:
                    results["errors"].append(
                        f"Failed to rename {issue['file']}: {str(e)}"
                    )
            else:
                results["errors"].append(f"Cannot fix {issue['file']}: {issue['type']}")

        return results
