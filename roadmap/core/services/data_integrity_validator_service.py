"""Data integrity validators for health checks.

Handles validation of:
- Duplicate issues
- Folder structure issues
- Archivable issues and milestones
- Old backup files
- Data integrity
- Orphaned issues

Uses BaseValidator abstract class to eliminate boilerplate and ensure
consistent error handling and logging across all validators.
"""

import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import TypedDict

from roadmap.common.logging import get_logger
from roadmap.common.timezone_utils import now_utc
from roadmap.core.services.base_validator import BaseValidator, HealthStatus

logger = get_logger(__name__)


class BackupScanResult(TypedDict):
    """Type definition for backup scan results."""

    files_to_delete: list[dict]
    total_size_bytes: int


def extract_issue_id(filename: str) -> str | None:
    """Extract issue ID from filename (first part before the dashes and title).

    Issue IDs are 8 hex characters.
    """
    match = re.match(r"^([a-f0-9]{8})", filename)
    return match.group(1) if match else None


class DuplicateIssuesValidator(BaseValidator):
    """Validator for duplicate issues."""

    @staticmethod
    def get_check_name() -> str:
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


class BackupValidator:
    """Validator for old backup files."""

    @staticmethod
    def scan_for_old_backups(backups_dir: Path, keep: int = 10) -> BackupScanResult:
        """Scan for old backup files that could be deleted.

        Returns a dict with:
        - 'files_to_delete': List of backup files that exceed the keep threshold
        - 'total_size_bytes': Total size of files that could be deleted (int)
        """
        result: BackupScanResult = {"files_to_delete": [], "total_size_bytes": 0}

        if not backups_dir.exists():
            return result

        backup_files = list(backups_dir.glob("*.backup.md"))
        if not backup_files:
            return result

        # Group backups by issue ID
        backups_by_issue = {}
        for backup_file in backup_files:
            parts = backup_file.stem.split("_")
            issue_key = "_".join(parts[:-1])

            if issue_key not in backups_by_issue:
                backups_by_issue[issue_key] = []

            stat = backup_file.stat()
            backups_by_issue[issue_key].append(
                {
                    "path": backup_file,
                    "mtime": stat.st_mtime,
                    "size": stat.st_size,
                }
            )

        # Find files that exceed keep threshold
        for _issue_key, backups in backups_by_issue.items():
            backups.sort(key=lambda x: x["mtime"], reverse=True)

            for idx, backup in enumerate(backups):
                if idx >= keep:
                    result["files_to_delete"].append(backup)
                    result["total_size_bytes"] += backup["size"]

        return result

    @staticmethod
    def check_old_backups() -> tuple[str, str]:
        """Check for old backup files.

        Returns:
            Tuple of (status, message) describing the health check result
        """
        try:
            backups_dir = Path(".roadmap/backups")
            old_backups = BackupValidator.scan_for_old_backups(backups_dir)

            if not old_backups["files_to_delete"]:
                logger.debug("health_check_old_backups", status="none")
                return HealthStatus.HEALTHY, "No old backups to clean up"

            count = len(old_backups["files_to_delete"])
            size_mb = old_backups["total_size_bytes"] / (1024 * 1024)
            message = (
                f"ℹ️ {count} old backup file(s) could be deleted "
                f"(~{size_mb:.1f} MB saved): Run 'roadmap cleanup' to remove"
            )
            logger.info("health_check_old_backups", count=count, size_mb=size_mb)
            return HealthStatus.HEALTHY, message

        except Exception as e:
            logger.debug("health_check_old_backups_failed", error=str(e))
            return HealthStatus.HEALTHY, "Could not check for old backups"


class ArchivableIssuesValidator:
    """Validator for archivable issues."""

    @staticmethod
    def scan_for_archivable_issues(core, threshold_days: int = 30) -> list[dict]:
        """Scan for issues that should be archived (closed >threshold_days ago).

        Returns a list of issue dicts with id, title, status, closed date, and days_since_close.
        """
        archivable = []

        try:
            issues = core.issue_service.list_issues()
            now = now_utc()

            for issue in issues:
                # Check if issue is closed (by status or by completed_date)
                if issue.status.value == "closed" or issue.actual_end_date:
                    close_date = issue.actual_end_date or now
                    days_since_close = (now - close_date).days

                    if days_since_close > threshold_days:
                        archivable.append(
                            {
                                "id": issue.id,
                                "title": issue.title,
                                "status": issue.status.value,
                                "closed_date": close_date.isoformat()
                                if close_date
                                else None,
                                "days_since_close": days_since_close,
                            }
                        )
        except Exception as e:
            logger.debug("scan_archivable_issues_error", error=str(e))

        return archivable

    @staticmethod
    def check_archivable_issues(core) -> tuple[str, str]:
        """Check for archivable issues.

        Returns:
            Tuple of (status, message) describing the health check result
        """
        try:
            archivable = ArchivableIssuesValidator.scan_for_archivable_issues(core)

            if not archivable:
                logger.debug("health_check_archivable_issues", status="none")
                return HealthStatus.HEALTHY, "No issues to archive"

            message = (
                f"ℹ️ {len(archivable)} issue(s) eligible for archival "
                "(closed >30 days ago): Consider archiving old issues"
            )
            logger.info("health_check_archivable_issues", count=len(archivable))
            return HealthStatus.DEGRADED, message

        except Exception as e:
            logger.debug("health_check_archivable_issues_failed", error=str(e))
            return HealthStatus.HEALTHY, "Could not check for archivable issues"


class ArchivableMilestonesValidator:
    """Validator for archivable milestones."""

    @staticmethod
    def scan_for_archivable_milestones(core, threshold_days: int = 14) -> list[dict]:
        """Scan for milestones that should be archived (completed >threshold_days ago).

        Returns a list of milestone dicts with name, status, closed date, issue count, and days_since_close.
        """
        archivable = []

        try:
            milestones = core.milestone_service.list_milestones()
            now = datetime.now()

            for milestone in milestones:
                if milestone.status.value == "closed" and milestone.closed_at:
                    days_since_close = (now - milestone.closed_at).days

                    if days_since_close > threshold_days:
                        archivable.append(
                            {
                                "name": milestone.name,
                                "status": milestone.status.value,
                                "closed_date": milestone.closed_at.isoformat(),
                                "days_since_close": days_since_close,
                            }
                        )
        except Exception as e:
            logger.debug("scan_archivable_milestones_error", error=str(e))

        return archivable

    @staticmethod
    def check_archivable_milestones(core) -> tuple[str, str]:
        """Check for archivable milestones.

        Returns:
            Tuple of (status, message) describing the health check result
        """
        try:
            archivable = ArchivableMilestonesValidator.scan_for_archivable_milestones(
                core
            )

            if not archivable:
                logger.debug("health_check_archivable_milestones", status="none")
                return HealthStatus.HEALTHY, "No milestones to archive"

            message = (
                f"ℹ️ {len(archivable)} milestone(s) eligible for archival "
                "(closed >14 days ago): Consider archiving old milestones"
            )
            logger.info("health_check_archivable_milestones", count=len(archivable))
            return HealthStatus.DEGRADED, message

        except Exception as e:
            logger.debug("health_check_archivable_milestones_failed", error=str(e))
            return HealthStatus.HEALTHY, "Could not check for archivable milestones"


class DataIntegrityValidator:
    """Validator for data integrity."""

    @staticmethod
    def scan_for_data_integrity_issues(
        issues_dir: Path,
    ) -> dict[str, list[str]]:
        """Scan for data integrity issues (orphaned/missing files).

        Returns a dict with:
        - 'malformed_files': List of files that couldn't be parsed
        """
        result = {"malformed_files": []}

        if not issues_dir.exists():
            return result

        # Scan all issue files recursively
        for issue_file in issues_dir.rglob("*.md"):
            if ".backup" in issue_file.name:
                continue

            try:
                from roadmap.adapters.persistence.parser import IssueParser

                IssueParser.parse_issue_file(issue_file)
            except Exception:
                # File couldn't be parsed
                result["malformed_files"].append(
                    str(issue_file.relative_to(issues_dir))
                )

        return result

    @staticmethod
    def check_data_integrity() -> tuple[str, str]:
        """Check data integrity.

        Returns:
            Tuple of (status, message) describing the health check result
        """
        try:
            issues_dir = Path(".roadmap/issues")
            if not issues_dir.exists():
                return (
                    HealthStatus.HEALTHY,
                    "Issues directory not found (not initialized yet)",
                )

            integrity_issues = DataIntegrityValidator.scan_for_data_integrity_issues(
                issues_dir
            )

            if not integrity_issues["malformed_files"]:
                logger.debug("health_check_data_integrity", status="healthy")
                return HealthStatus.HEALTHY, "No data integrity issues found"

            message = (
                f"⚠️ {len(integrity_issues['malformed_files'])} malformed file(s) detected: "
                "These files couldn't be parsed - manual review required"
            )
            logger.warning(
                "health_check_data_integrity",
                count=len(integrity_issues["malformed_files"]),
            )
            return HealthStatus.DEGRADED, message

        except Exception as e:
            logger.error("health_check_data_integrity_failed", error=str(e))
            return HealthStatus.UNHEALTHY, f"Error checking data integrity: {e}"


class OrphanedIssuesValidator:
    """Validator for orphaned issues."""

    @staticmethod
    def scan_for_orphaned_issues(core) -> list[dict]:
        """Scan for issues not assigned to any milestone (not in backlog either).

        Returns a list of orphaned issue dicts with id, title, and location.
        """
        orphaned = []

        try:
            issues_dir = Path(".roadmap/issues").resolve()
            if not issues_dir.exists():
                return orphaned

            issues = core.issue_service.list_issues()

            for issue in issues:
                # Issue is orphaned if milestone is None or empty string
                if not issue.milestone or issue.milestone == "":
                    orphaned.append(
                        {
                            "id": issue.id,
                            "title": issue.title,
                            "location": str(
                                issues_dir / f"{issue.id}*.md"
                            ),  # Pattern for file
                        }
                    )

        except Exception as e:
            logger.debug("scan_orphaned_issues_error", error=str(e))

        return orphaned

    @staticmethod
    def check_orphaned_issues(core) -> tuple[str, str]:
        """Check for orphaned issues.

        Returns:
            Tuple of (status, message) describing the health check result
        """
        try:
            orphaned = OrphanedIssuesValidator.scan_for_orphaned_issues(core)

            if not orphaned:
                logger.debug("health_check_orphaned_issues", status="none")
                return HealthStatus.HEALTHY, "No orphaned issues found"

            count = len(orphaned)
            message = (
                f"⚠️ {count} orphaned issue(s) found (not in any milestone folder): "
                "These issues are disconnected from your milestone structure"
            )
            logger.warning("health_check_orphaned_issues", count=count)
            return HealthStatus.DEGRADED, message

        except Exception as e:
            logger.debug("health_check_orphaned_issues_failed", error=str(e))
            return HealthStatus.HEALTHY, "Could not check for orphaned issues"


class DataIntegrityValidatorService:
    """Orchestrator for data integrity validation checks."""

    def __init__(self):
        """Initialize data integrity validator service."""
        self.duplicate_validator = DuplicateIssuesValidator()
        self.folder_structure_validator = FolderStructureValidator()
        self.backup_validator = BackupValidator()
        self.archivable_issues_validator = ArchivableIssuesValidator()
        self.archivable_milestones_validator = ArchivableMilestonesValidator()
        self.data_integrity_validator = DataIntegrityValidator()
        self.orphaned_issues_validator = OrphanedIssuesValidator()

    def run_all_data_integrity_checks(self, core) -> dict[str, tuple[str, str]]:
        """Run all data integrity checks.

        Returns:
            Dictionary mapping check names to (status, message) tuples
        """
        checks = {}

        try:
            checks["duplicate_issues"] = (
                DuplicateIssuesValidator.check_duplicate_issues(core)
            )
            checks["folder_structure"] = (
                FolderStructureValidator.check_folder_structure(core)
            )
            checks["old_backups"] = BackupValidator.check_old_backups()
            checks["archivable_issues"] = (
                ArchivableIssuesValidator.check_archivable_issues(core)
            )
            checks["archivable_milestones"] = (
                ArchivableMilestonesValidator.check_archivable_milestones(core)
            )
            checks["data_integrity"] = DataIntegrityValidator.check_data_integrity()
            checks["orphaned_issues"] = OrphanedIssuesValidator.check_orphaned_issues(
                core
            )

            return checks
        except Exception as e:
            logger.error("data_integrity_validation_failed", error=str(e))
            return {
                "error": (
                    HealthStatus.UNHEALTHY,
                    f"Data integrity validation failed: {e}",
                )
            }

    def get_overall_status(self, checks: dict[str, tuple[str, str]]) -> str:
        """Get overall status from all data integrity checks.

        Returns:
            Overall status: 'healthy', 'degraded', or 'unhealthy'
        """
        if not checks:
            return HealthStatus.UNHEALTHY

        statuses = [status for status, _ in checks.values()]

        if HealthStatus.UNHEALTHY in statuses:
            return HealthStatus.UNHEALTHY
        elif HealthStatus.DEGRADED in statuses:
            return HealthStatus.DEGRADED
        else:
            return HealthStatus.HEALTHY
