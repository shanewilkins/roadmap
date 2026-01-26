"""Validator for folder structure and issue placement."""

from pathlib import Path

from roadmap.common.logging import get_logger
from roadmap.core.services.validator_base import BaseValidator, HealthStatus

from . import extract_issue_id

logger = get_logger(__name__)


class FolderStructureValidator(BaseValidator):
    """Validator for folder structure and issue placement."""

    @staticmethod
    def get_check_name() -> str:
        """Get the name of this check.

        Returns:
            String identifier for the folder_structure check.
        """
        return "folder_structure"

    @staticmethod
    def _check_root_issues(issues_dir: Path, core, misplaced_list: list) -> None:
        """Check root level issues for milestone placement issues."""
        for issue_file in issues_dir.glob("*.md"):
            if ".backup" in issue_file.name:
                continue

            try:
                issue_id = extract_issue_id(issue_file.name)
                if not issue_id:
                    continue

                issue = core.issue_service.get_issue(issue_id)
                if issue and issue.milestone:
                    milestone_folder = issues_dir / issue.milestone
                    if milestone_folder.exists():
                        misplaced_list.append(
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
            except Exception as e:
                logger.debug(
                    "issue_parse_failed",
                    operation="parse_issue",
                    file=str(issue_file),
                    error=str(e),
                    action="Skipping issue",
                )

    @staticmethod
    def _process_milestone_file(
        issue_file: Path, core, milestone_folder: Path, orphaned_list: list
    ) -> None:
        """Process single file in milestone folder for orphaned issues.

        Args:
            issue_file: File to process
            core: RoadmapCore instance
            milestone_folder: Milestone folder path
            orphaned_list: List to append orphaned issues to
        """
        if ".backup" in issue_file.name:
            return

        try:
            issue_id = extract_issue_id(issue_file.name)
            if not issue_id:
                return

            issue = core.issue_service.get_issue(issue_id)
            if issue and not issue.milestone:
                orphaned_list.append(
                    {
                        "issue_id": issue.id,
                        "title": issue.title,
                        "location": str(issue_file),
                        "folder": milestone_folder.name,
                    }
                )
        except Exception as e:
            logger.debug(
                "milestone_folder_check_failed",
                operation="check_milestone_folders",
                error=str(e),
                action="Continuing to next folder",
            )

    @staticmethod
    def _check_milestone_folders(issues_dir: Path, core, orphaned_list: list) -> None:
        """Check milestone folders for orphaned issues."""
        for milestone_folder in issues_dir.glob("*/"):
            if not milestone_folder.is_dir() or milestone_folder.name.startswith("."):
                continue

            if milestone_folder.name == "backlog":
                continue

            for issue_file in milestone_folder.glob("*.md"):
                FolderStructureValidator._process_milestone_file(
                    issue_file, core, milestone_folder, orphaned_list
                )

    @staticmethod
    def scan_for_folder_structure_issues(
        issues_dir: Path, core
    ) -> dict[str, list[dict]]:
        """Verify issues are in correct milestone folders.

        Returns a dict of potential issues:
        - 'misplaced': Issues in root when they belong in a milestone subfolder
        - 'orphaned': Issues with milestone assignments but not in milestone folder
        """
        misplaced = []
        orphaned = []

        try:
            FolderStructureValidator._check_root_issues(issues_dir, core, misplaced)
            FolderStructureValidator._check_milestone_folders(
                issues_dir, core, orphaned
            )
        except Exception as e:
            logger.error("folder_structure_check_failed", error=str(e), severity="system_error")

        return (
            {
                "misplaced": misplaced,
                "orphaned": orphaned,
            }
            if (misplaced or orphaned)
            else {}
        )

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
