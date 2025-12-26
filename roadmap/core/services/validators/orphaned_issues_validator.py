"""Validator for orphaned issues."""

from pathlib import Path

from roadmap.common.logging import get_logger
from roadmap.core.domain.issue import Status
from roadmap.core.services.base_validator import HealthStatus

logger = get_logger(__name__)


class OrphanedIssuesValidator:
    """Validator for orphaned issues (in wrong folder based on milestone)."""

    @staticmethod
    def scan_for_orphaned_issues(core) -> list[dict]:
        """Scan for issues in wrong folder (not matching their milestone).

        Returns a list of misplaced issue dicts with id, title, and details.
        """
        misplaced = []

        try:
            issues_dir = Path(".roadmap/issues").resolve()
            archive_dir = Path(".roadmap/archive/issues").resolve()

            if not issues_dir.exists():
                return misplaced

            # Scan all issues
            for issue in core.issues.list():
                # Determine expected folder
                expected_folder = OrphanedIssuesValidator._get_expected_folder(issue)

                # Find actual folder
                actual_folder = OrphanedIssuesValidator._find_issue_folder(
                    issue.id, issues_dir, archive_dir
                )

                # Issue is misplaced if:
                # 1. It's at root level (actual_folder == issues_dir)
                # 2. Or it's in wrong folder (actual_folder != expected_folder)
                if actual_folder:
                    if actual_folder == issues_dir or actual_folder != expected_folder:
                        misplaced.append(
                            {
                                "id": issue.id,
                                "title": issue.title,
                                "milestone": issue.milestone or "(none)",
                                "current_folder": str(actual_folder),
                                "expected_folder": str(expected_folder),
                            }
                        )

        except Exception as e:
            logger.debug("scan_orphaned_issues_error", error=str(e))

        return misplaced

    @staticmethod
    def check_orphaned_issues(core) -> tuple[str, str]:
        """Check for orphaned issues.

        Returns:
            Tuple of (status, message) describing the health check result
        """
        try:
            misplaced = OrphanedIssuesValidator.scan_for_orphaned_issues(core)

            if not misplaced:
                logger.debug("health_check_orphaned_issues", status="none")
                return HealthStatus.HEALTHY, "No orphaned issues found"

            count = len(misplaced)
            message = (
                f"⚠️ {count} orphaned issue(s) found (in wrong folder): "
                "These issues are not in the folder matching their milestone"
            )
            logger.warning("health_check_orphaned_issues", count=count)
            return HealthStatus.DEGRADED, message

        except Exception as e:
            logger.debug("health_check_orphaned_issues_failed", error=str(e))
            return HealthStatus.HEALTHY, "Could not check for orphaned issues"

    @staticmethod
    def _get_expected_folder(issue) -> Path:
        """Determine expected folder for an issue.

        Args:
            issue: Issue object

        Returns:
            Path to expected folder
        """
        # Closed issues go to archive
        base_path = (
            Path(".roadmap/archive/issues").resolve()
            if issue.status == Status.CLOSED
            else Path(".roadmap/issues").resolve()
        )

        # If no milestone, assign to backlog
        milestone = issue.milestone or "backlog"

        return base_path / milestone

    @staticmethod
    def _find_issue_folder(
        issue_id: str, issues_dir: Path, archive_dir: Path
    ) -> Path | None:
        """Find the actual folder containing an issue.

        Args:
            issue_id: Issue ID to find
            issues_dir: Path to .roadmap/issues
            archive_dir: Path to .roadmap/archive/issues

        Returns:
            Path to folder containing the issue, or None if at root level
        """
        # Check if file is at root level (loose file)
        for file in issues_dir.glob(f"{issue_id}*.md"):
            if file.is_file():
                return issues_dir  # Return root to indicate it's loose

        # Check main issues directory subfolders
        for folder in issues_dir.iterdir():
            if folder.is_dir():
                for _ in folder.glob(f"{issue_id}*.md"):
                    return folder

        # Check archive directory
        if archive_dir.exists():
            for folder in archive_dir.iterdir():
                if folder.is_dir():
                    for _ in folder.glob(f"{issue_id}*.md"):
                        return folder

        return None
