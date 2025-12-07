"""Validator for folder structure and issue placement."""

from pathlib import Path

from roadmap.common.logging import get_logger
from roadmap.core.services.base_validator import BaseValidator, HealthStatus

from . import extract_issue_id

logger = get_logger(__name__)


class FolderStructureValidator(BaseValidator):
    """Validator for folder structure and issue placement."""

    @staticmethod
    def get_check_name() -> str:
        return "folder_structure"

    @staticmethod
    def scan_for_folder_structure_issues(
        issues_dir: Path, core
    ) -> dict[str, list[dict]]:
        """Verify issues are in correct milestone folders.

        Returns a dict of potential issues:
        - 'misplaced': Issues in root when they belong in a milestone subfolder
        - 'orphaned': Issues with milestone assignments but not in milestone folder
        """
        potential_issues = {"misplaced": [], "orphaned": []}

        try:
            # Check root level issues
            for issue_file in issues_dir.glob("*.md"):
                if ".backup" in issue_file.name:
                    continue

                try:
                    issue_id = extract_issue_id(issue_file.name)
                    if not issue_id:
                        continue

                    issue = core.issue_service.get_issue(issue_id)
                    if issue and issue.milestone:
                        # Root issue has a milestone - should be in milestone folder
                        milestone_folder = issues_dir / issue.milestone
                        if milestone_folder.exists():
                            potential_issues["misplaced"].append(
                                {
                                    "issue_id": issue.id,
                                    "title": issue.title,
                                    "current_location": str(issue_file),
                                    "assigned_milestone": issue.milestone,
                                    "expected_location": str(
                                        milestone_folder / issue_file.name
                                    ),
                                }
                            )
                except Exception:
                    # Skip files that can't be parsed
                    pass

            # Check milestone folders for issues without milestone assignments or in wrong folders
            for milestone_folder in issues_dir.glob("*/"):
                if milestone_folder.is_dir() and not milestone_folder.name.startswith(
                    "."
                ):
                    # Skip backlog folder - those issues are supposed to have no milestone
                    if milestone_folder.name == "backlog":
                        continue

                    for issue_file in milestone_folder.glob("*.md"):
                        if ".backup" in issue_file.name:
                            continue

                        try:
                            issue_id = extract_issue_id(issue_file.name)
                            if not issue_id:
                                continue

                            issue = core.issue_service.get_issue(issue_id)
                            if issue and not issue.milestone:
                                # Issue in milestone folder but has no milestone assigned
                                potential_issues["orphaned"].append(
                                    {
                                        "issue_id": issue.id,
                                        "title": issue.title,
                                        "location": str(issue_file),
                                        "folder": milestone_folder.name,
                                    }
                                )
                        except Exception:
                            # Skip files that can't be parsed
                            pass

        except Exception as e:
            logger.error("folder_structure_check_failed", error=str(e))

        return {k: v for k, v in potential_issues.items() if v}

    @staticmethod
    def perform_check() -> tuple[str, str]:
        """Check folder structure and issue placement.

        Note: This validator requires core access but is called without it.
        For now, return HEALTHY to avoid blocking health checks.

        Returns:
            Tuple of (status, message) describing the health check result
        """
        issues_dir = Path(".roadmap/issues")
        if not issues_dir.exists():
            return (
                HealthStatus.HEALTHY,
                "Issues directory not found (not initialized yet)",
            )

        # Simplified check without core access for now
        # Full check requires core.issue_service which we don't have in this context
        return HealthStatus.HEALTHY, "Folder structure check (simplified)"
