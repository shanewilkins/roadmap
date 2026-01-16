"""Milestone Consistency Validation Module

Handles validation and fixing of milestone filename and name field consistency.
Extracted from RoadmapCore to reduce god object complexity.
"""

from __future__ import annotations

from pathlib import Path

from roadmap.adapters.persistence.parser import MilestoneParser


class MilestoneConsistencyValidator:
    """Validates and fixes milestone naming consistency."""

    def __init__(self, milestones_dir: Path):
        """Initialize validator with milestones directory.

        Args:
            milestones_dir: Path to milestones directory
        """
        self.milestones_dir = milestones_dir

    def validate(self) -> list[dict[str, str]]:
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

    def fix(self) -> dict[str, list[str]]:
        """Fix milestone filename inconsistencies by renaming files to match name fields.

        Returns:
            Dictionary with 'renamed' and 'errors' lists
        """
        results = {"renamed": [], "errors": []}
        inconsistencies = self.validate()

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
