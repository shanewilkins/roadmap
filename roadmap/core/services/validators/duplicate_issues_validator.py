"""Validator for duplicate issues."""

from collections import defaultdict
from pathlib import Path

from roadmap.core.services.base_validator import BaseValidator, HealthStatus

from . import extract_issue_id


class DuplicateIssuesValidator(BaseValidator):
    """Validator for duplicate issues."""

    @staticmethod
    def get_check_name() -> str:
        """Get the name of this check.

        Returns:
            String identifier for the duplicate_issues check.
        """
        return "duplicate_issues"

    @staticmethod
    def scan_for_duplicate_issues(issues_dir: Path) -> dict[str, list[Path]]:
        """Scan all issue files and identify duplicates by issue ID.

        Returns a dict mapping issue_id -> list of file paths where duplicates exist (2+ occurrences).
        """
        issues_by_id = defaultdict(list)

        # Scan all issue markdown files recursively
        for issue_file in issues_dir.glob("**/*.md"):
            # Skip backup files
            if ".backup" in issue_file.name:
                continue

            issue_id = extract_issue_id(issue_file.name)
            if issue_id:
                issues_by_id[issue_id].append(issue_file)

        # Return only duplicates (2+ occurrences)
        duplicates = {
            issue_id: files
            for issue_id, files in issues_by_id.items()
            if len(files) > 1
        }

        return duplicates

    @staticmethod
    def perform_check() -> tuple[str, str]:
        """Check for duplicate issues.

        Returns:
            Tuple of (status, message) describing the health check result
        """
        issues_dir = Path(".roadmap/issues")
        if not issues_dir.exists():
            return (
                HealthStatus.HEALTHY,
                "Issues directory not found (not initialized yet)",
            )

        duplicates = DuplicateIssuesValidator.scan_for_duplicate_issues(issues_dir)

        if not duplicates:
            return HealthStatus.HEALTHY, "No duplicate issues found"

        total_duplicates = sum(len(files) - 1 for files in duplicates.values())
        message = (
            f"⚠️ {len(duplicates)} issue ID(s) have duplicates "
            f"({total_duplicates} duplicate files total): "
            "Manual cleanup required"
        )
        return HealthStatus.DEGRADED, message
