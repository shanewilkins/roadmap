"""Validator for duplicate milestones."""

from collections import defaultdict
from pathlib import Path

import structlog

from roadmap.core.services.validator_base import BaseValidator, HealthStatus
from roadmap.infrastructure.coordination.core import RoadmapCore

logger = structlog.get_logger()


class DuplicateMilestonesValidator(BaseValidator):
    """Validator for duplicate milestones (by name and file)."""

    @staticmethod
    def get_check_name() -> str:
        """Get the name of this check.

        Returns:
            String identifier for the duplicate_milestones check.
        """
        return "duplicate_milestones"

    @staticmethod
    def scan_for_duplicate_files(milestones_dir: Path) -> dict[str, list[Path]]:
        """Scan all milestone files and identify duplicates by milestone name.

        Returns a dict mapping milestone_name -> list of file paths where duplicates exist (2+ occurrences).
        """
        milestones_by_name = defaultdict(list)

        # Scan all milestone markdown files
        for milestone_file in milestones_dir.glob("*.md"):
            # Skip backup files
            if ".backup" in milestone_file.name:
                continue

            # Extract milestone name from filename (remove .md extension)
            milestone_name = milestone_file.stem
            milestones_by_name[milestone_name].append(milestone_file)

        # Return only duplicates (2+ occurrences)
        duplicates = {
            name: files for name, files in milestones_by_name.items() if len(files) > 1
        }

        return duplicates

    @staticmethod
    def scan_for_duplicate_names(core) -> list[dict]:
        """Scan for duplicate milestone names in the database.

        Returns a list of duplicate milestone names with count.
        """
        duplicates = []

        try:
            all_milestones = core.milestones.list()

            # Count occurrences of each name
            name_counts = {}
            for milestone in all_milestones:
                name_counts[milestone.name] = name_counts.get(milestone.name, 0) + 1

            # Find duplicates
            for name, count in name_counts.items():
                if count > 1:
                    duplicates.append(
                        {
                            "name": name,
                            "count": count,
                        }
                    )

        except Exception as e:
            logger.debug(
                "scan_duplicate_names_failed",
                operation="scan_for_duplicate_names",
                error=str(e),
                action="Returning empty duplicates",
            )

        return duplicates

    @staticmethod
    def perform_check() -> tuple[str, str]:
        """Check for duplicate milestones (both file and name duplicates).

        Returns:
            Tuple of (status, message) describing the health check result
        """
        try:
            milestones_dir = Path(".roadmap/milestones")
            if not milestones_dir.exists():
                return (
                    HealthStatus.HEALTHY,
                    "Milestones directory not found (not initialized yet)",
                )

            # Check for file duplicates
            file_duplicates = DuplicateMilestonesValidator.scan_for_duplicate_files(
                milestones_dir
            )

            # Check for name duplicates in database
            core = RoadmapCore()
            name_duplicates = DuplicateMilestonesValidator.scan_for_duplicate_names(
                core
            )

            issues = []
            if file_duplicates:
                total_file_duplicates = sum(
                    len(files) - 1 for files in file_duplicates.values()
                )
                issues.append(
                    f"{len(file_duplicates)} milestone name(s) have duplicate files "
                    f"({total_file_duplicates} duplicate files total)"
                )

            if name_duplicates:
                issues.append(
                    f"{len(name_duplicates)} milestone name(s) appear multiple times in database"
                )

            if not issues:
                return HealthStatus.HEALTHY, "No duplicate milestones found"

            message = f"⚠️ {'; '.join(issues)}: Manual cleanup required"
            return HealthStatus.DEGRADED, message

        except Exception as e:
            logger.debug(
                "duplicate_milestones_check_failed",
                operation="perform_check",
                error=str(e),
                action="Returning healthy status",
            )
            return HealthStatus.HEALTHY, "Could not check for duplicate milestones"
