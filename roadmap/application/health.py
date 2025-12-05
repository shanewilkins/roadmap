"""Health checks for monitoring application and infrastructure status."""

import re
from collections import defaultdict
from enum import Enum
from pathlib import Path

from ..shared.logging import get_logger
from .services.infrastructure_validator_service import (
    InfrastructureValidator,
)

logger = get_logger(__name__)


def extract_issue_id(filename: str) -> str | None:
    """Extract issue ID from filename (first part before the dashes and title).

    Issue IDs are 8 hex characters.
    """
    match = re.match(r"^([a-f0-9]{8})", filename)
    return match.group(1) if match else None


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
        issue_id: files for issue_id, files in issues_by_id.items() if len(files) > 1
    }

    return duplicates


def scan_for_folder_structure_issues(issues_dir: Path, core) -> dict[str, list[dict]]:
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
            if milestone_folder.is_dir() and not milestone_folder.name.startswith("."):
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
                        if issue:
                            if not issue.milestone:
                                # Issue in milestone folder but has no milestone assignment
                                potential_issues["orphaned"].append(
                                    {
                                        "issue_id": issue.id,
                                        "title": issue.title,
                                        "location": str(issue_file),
                                        "folder": milestone_folder.name,
                                    }
                                )
                            elif issue.milestone != milestone_folder.name:
                                # Issue in wrong milestone folder
                                potential_issues["misplaced"].append(
                                    {
                                        "issue_id": issue.id,
                                        "title": issue.title,
                                        "current_location": str(issue_file),
                                        "assigned_milestone": issue.milestone,
                                        "expected_location": str(
                                            issues_dir
                                            / issue.milestone
                                            / issue_file.name
                                        ),
                                    }
                                )
                    except Exception:
                        pass
    except Exception as e:
        logger.error("folder_structure_check_failed", error=str(e))

    return {k: v for k, v in potential_issues.items() if v}


def scan_for_old_backups(
    backups_dir: Path, keep: int = 10
) -> dict[str, list[dict] | int]:
    """Scan for old backup files that could be deleted.

    Returns a dict with:
    - 'files_to_delete': List of backup files that exceed the keep threshold
    - 'total_size_bytes': Total size of files that could be deleted
    """
    result = {"files_to_delete": [], "total_size_bytes": 0}

    if not backups_dir.exists():
        return result

    backup_files = list(backups_dir.glob("*.backup.md"))  # type: ignore[func-returns-value]
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
                result["files_to_delete"].append(
                    {
                        "path": backup["path"],
                        "size": backup["size"],
                    }
                )
                result["total_size_bytes"] += backup["size"]

    return result


def scan_for_archivable_issues(core, threshold_days: int = 30) -> list[dict]:
    """Scan for issues that should be archived (closed >threshold_days ago).

    Returns a list of issue dicts with id, title, status, closed date, and days_since_close.
    """
    archivable = []

    try:
        issues = core.issue_service.list_issues()
        from datetime import datetime

        from roadmap.shared.timezone_utils import now_utc

        now = now_utc()  # Use timezone-aware UTC time

        for issue in issues:
            # Check if issue is closed (by status or by completed_date)
            if issue.status == "closed" or issue.actual_end_date:
                # Use actual_end_date or completed_date for closure time
                closed_dt = None
                if issue.actual_end_date:
                    closed_dt = (
                        issue.actual_end_date
                        if isinstance(issue.actual_end_date, datetime)
                        else datetime.fromisoformat(str(issue.actual_end_date))
                    )
                elif issue.completed_date:
                    try:
                        closed_dt = datetime.fromisoformat(issue.completed_date)
                    except (ValueError, TypeError):
                        closed_dt = None

                if closed_dt:
                    try:
                        # Ensure both are timezone-aware for comparison
                        if closed_dt.tzinfo is None:
                            from datetime import timezone

                            closed_dt = closed_dt.replace(tzinfo=timezone.utc)
                        days_closed = (now - closed_dt).days
                        if days_closed > threshold_days:
                            archivable.append(
                                {
                                    "id": issue.id,
                                    "title": issue.title,
                                    "status": issue.status,
                                    "closed_at": closed_dt.isoformat(),
                                    "days_since_close": days_closed,
                                }
                            )
                    except TypeError:
                        # Skip if datetime arithmetic fails
                        continue
    except Exception as e:
        logger.debug("scan_archivable_issues_error", error=str(e))

    return archivable


def scan_for_archivable_milestones(core, threshold_days: int = 14) -> list[dict]:
    """Scan for milestones that should be archived (completed >threshold_days ago).

    Returns a list of milestone dicts with name, status, closed date, issue count, and days_since_close.
    """
    archivable = []

    try:
        milestones = core.milestone_service.list_milestones()
        from datetime import datetime

        now = datetime.now()

        for milestone in milestones:
            if milestone.status == "closed" and milestone.closed_at:
                # Parse closed_at if it's a string
                if isinstance(milestone.closed_at, str):
                    closed_dt = datetime.fromisoformat(milestone.closed_at)
                else:
                    closed_dt = milestone.closed_at

                days_closed = (now - closed_dt).days
                if days_closed > threshold_days:
                    # Count issues in this milestone
                    issues = core.issue_service.list_issues(milestone=milestone.name)
                    issue_count = len(issues)

                    archivable.append(
                        {
                            "name": milestone.name,
                            "status": milestone.status,
                            "closed_at": milestone.closed_at,
                            "days_since_close": days_closed,
                            "issue_count": issue_count,
                        }
                    )
    except Exception as e:
        logger.debug("scan_archivable_milestones_error", error=str(e))

    return archivable


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
            from roadmap.infrastructure.persistence.parser import IssueParser

            IssueParser.parse_issue_file(issue_file)
        except Exception:
            # File couldn't be parsed
            result["malformed_files"].append(str(issue_file.relative_to(issues_dir)))

    return result


def scan_for_orphaned_issues(core) -> list[dict]:
    """Scan for issues not assigned to any milestone (not in backlog either).

    Returns a list of orphaned issue dicts with id, title, and location.
    """
    orphaned = []

    try:
        issues_dir = Path(".roadmap/issues").resolve()  # Convert to absolute path
        if not issues_dir.exists():
            return orphaned

        issues = core.issue_service.list_issues()

        for issue in issues:
            # Issue is orphaned if milestone is None or empty string
            if not issue.milestone or issue.milestone == "":
                # Check if it's actually in the backlog folder or another location
                if issue.file_path:
                    try:
                        file_path = Path(
                            issue.file_path
                        ).resolve()  # Ensure absolute path
                        # If it's in a milestone-specific folder but milestone is not set, it's orphaned
                        relative_path = file_path.relative_to(issues_dir)
                        parts = relative_path.parts

                        # Check if in a subfolder (not root or backlog)
                        if len(parts) > 1 and parts[0] not in ("backlog", "."):
                            orphaned.append(
                                {
                                    "id": issue.id,
                                    "title": issue.title,
                                    "location": str(file_path),
                                    "folder": parts[0],
                                }
                            )
                    except (ValueError, RuntimeError):
                        # File path is not relative to issues_dir, skip it
                        continue

    except Exception as e:
        logger.debug("scan_orphaned_issues_error", error=str(e))

    return orphaned


def scan_for_malformed_files(issues_dir: Path) -> dict[str, list[str]]:
    """Scan for malformed YAML files that can't be parsed.

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
            from roadmap.infrastructure.persistence.parser import IssueParser

            IssueParser.parse_issue_file(issue_file)
        except Exception:
            # File couldn't be parsed
            result["malformed_files"].append(str(issue_file.relative_to(issues_dir)))

    return result

    return result


class HealthStatus(Enum):
    """Health status levels for system components."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class HealthCheck:
    """Application health checks for monitoring system status.

    This class provides methods to check the health of various system
    components including file system, database, and Git repository.

    Infrastructure validators are delegated to InfrastructureValidator.
    """

    def __init__(self):
        """Initialize HealthCheck with infrastructure validator."""
        self.infrastructure_validator = InfrastructureValidator()

    @staticmethod
    def check_roadmap_directory() -> tuple[HealthStatus, str]:
        """Check if .roadmap directory exists and is accessible.

        Delegates to InfrastructureValidator.

        Returns:
            Tuple of (status, message) describing the health check result
        """
        validator = InfrastructureValidator()
        status_str, message = validator.roadmap_dir_validator.check_roadmap_directory()
        # Convert ValidatorHealthStatus strings to HealthStatus enum
        return HealthStatus(status_str), message

    @staticmethod
    def check_state_file() -> tuple[HealthStatus, str]:
        """Check if state database exists and is readable.

        Delegates to InfrastructureValidator.

        Returns:
            Tuple of (status, message) describing the health check result
        """
        validator = InfrastructureValidator()
        status_str, message = validator.state_file_validator.check_state_file()
        return HealthStatus(status_str), message

    @staticmethod
    def check_issues_directory() -> tuple[HealthStatus, str]:
        """Check if issues directory exists and is accessible.

        Delegates to InfrastructureValidator.

        Returns:
            Tuple of (status, message) describing the health check result
        """
        validator = InfrastructureValidator()
        status_str, message = validator.issues_dir_validator.check_issues_directory()
        return HealthStatus(status_str), message

    @staticmethod
    def check_milestones_directory() -> tuple[HealthStatus, str]:
        """Check if milestones directory exists and is accessible.

        Delegates to InfrastructureValidator.

        Returns:
            Tuple of (status, message) describing the health check result
        """
        validator = InfrastructureValidator()
        status_str, message = (
            validator.milestones_dir_validator.check_milestones_directory()
        )
        return HealthStatus(status_str), message

    @staticmethod
    def check_git_repository() -> tuple[HealthStatus, str]:
        """Check if Git repository exists and is accessible.

        Delegates to InfrastructureValidator.

        Returns:
            Tuple of (status, message) describing the health check result
        """
        validator = InfrastructureValidator()
        status_str, message = validator.git_repo_validator.check_git_repository()
        return HealthStatus(status_str), message

    @staticmethod
    def check_duplicate_issues(core) -> tuple[HealthStatus, str]:
        """Check for duplicate issues (same ID in multiple folders).

        Returns:
            Tuple of (status, message) describing the health check result
        """
        try:
            issues_dir = Path(".roadmap/issues")
            if not issues_dir.exists():
                return HealthStatus.HEALTHY, "No issues directory to check"

            duplicates = scan_for_duplicate_issues(issues_dir)

            if not duplicates:
                logger.debug("health_check_duplicate_issues", status="healthy")
                return HealthStatus.HEALTHY, "No duplicate issues found"

            count = len(duplicates)
            logger.warning(
                "health_check_duplicate_issues", status="degraded", duplicates=count
            )
            return (
                HealthStatus.DEGRADED,
                f"{count} issue(s) with multiple copies across folders",
            )
        except Exception as e:
            logger.error("health_check_duplicate_issues_failed", error=str(e))
            return HealthStatus.UNHEALTHY, f"Error checking for duplicates: {e}"

    @staticmethod
    def check_folder_structure(core) -> tuple[HealthStatus, str]:
        """Check if issues are in correct milestone folders.

        Returns:
            Tuple of (status, message) describing the health check result
        """
        try:
            issues_dir = Path(".roadmap/issues")
            if not issues_dir.exists():
                return HealthStatus.HEALTHY, "No issues directory to check"

            issues = scan_for_folder_structure_issues(issues_dir, core)

            if not issues:
                logger.debug("health_check_folder_structure", status="healthy")
                return HealthStatus.HEALTHY, "All issues in correct folders"

            misplaced_count = len(issues.get("misplaced", []))
            orphaned_count = len(issues.get("orphaned", []))
            total = misplaced_count + orphaned_count

            problems = []
            if misplaced_count:
                problems.append(f"{misplaced_count} in root with milestone assignments")
            if orphaned_count:
                problems.append(
                    f"{orphaned_count} in milestone folders without assignments"
                )

            message = f"{total} issue(s) with folder structure issues: " + "; ".join(
                problems
            )
            logger.warning(
                "health_check_folder_structure", status="degraded", issues_dict=issues
            )
            return HealthStatus.DEGRADED, message
        except Exception as e:
            logger.error("health_check_folder_structure_failed", error=str(e))
            return HealthStatus.UNHEALTHY, f"Error checking folder structure: {e}"

    @staticmethod
    def check_old_backups() -> tuple[HealthStatus, str]:
        """Check for old backup files that could be cleaned up.

        Returns:
            Tuple of (HEALTHY status, informational message) - never degrades health
        """
        try:
            backups_dir = Path(".roadmap/backups")
            result = scan_for_old_backups(backups_dir, keep=10)

            if not result["files_to_delete"]:
                logger.debug("health_check_old_backups", status="clean")
                return (
                    HealthStatus.HEALTHY,
                    "Backups are well-maintained",
                )

            total_size = result["total_size_bytes"]
            if isinstance(total_size, int):
                size_mb = total_size / (1024 * 1024)
            else:
                size_mb = 0.0

            files_to_delete = result["files_to_delete"]
            if isinstance(files_to_delete, list):
                count = len(files_to_delete)
            else:
                count = 0

            message = (
                f"ℹ️  {count} old backup(s) could be deleted (~{size_mb:.2f} MB) - "
                "Run 'roadmap cleanup' to remove them"
            )
            logger.debug(
                "health_check_old_backups",
                count=count,
                size_mb=size_mb,
            )
            return HealthStatus.HEALTHY, message

        except Exception as e:
            logger.debug("health_check_old_backups_failed", error=str(e))
            return HealthStatus.HEALTHY, "Could not check backups"

    @staticmethod
    def check_archivable_issues(core) -> tuple[HealthStatus, str]:
        """Check for closed issues that could be archived.

        Returns:
            Tuple of (HEALTHY status, informational message) - never degrades health
        """
        try:
            archivable = scan_for_archivable_issues(core, threshold_days=30)

            if not archivable:
                logger.debug("health_check_archivable_issues", status="none")
                return HealthStatus.HEALTHY, "No issues need archiving"

            count = len(archivable)
            message = (
                f"ℹ️  {count} issue(s) closed >30 days ago could be archived - "
                "Run 'roadmap archive' to archive them"
            )
            logger.debug("health_check_archivable_issues", count=count)
            return HealthStatus.HEALTHY, message

        except Exception as e:
            logger.debug("health_check_archivable_issues_failed", error=str(e))
            return HealthStatus.HEALTHY, "Could not check archivable issues"

    @staticmethod
    def check_archivable_milestones(core) -> tuple[HealthStatus, str]:
        """Check for closed milestones that could be archived.

        Returns:
            Tuple of (HEALTHY status, informational message) - never degrades health
        """
        try:
            archivable = scan_for_archivable_milestones(core, threshold_days=14)

            if not archivable:
                logger.debug("health_check_archivable_milestones", status="none")
                return HealthStatus.HEALTHY, "No milestones need archiving"

            count = len(archivable)
            message = (
                f"ℹ️  {count} milestone(s) closed >14 days ago could be archived - "
                "Run 'roadmap archive' to archive them"
            )
            logger.debug("health_check_archivable_milestones", count=count)
            return HealthStatus.HEALTHY, message

        except Exception as e:
            logger.debug("health_check_archivable_milestones_failed", error=str(e))
            return HealthStatus.HEALTHY, "Could not check archivable milestones"

    @staticmethod
    def check_database_integrity() -> tuple[HealthStatus, str]:
        """Check SQLite database integrity.

        Delegates to InfrastructureValidator.

        Returns:
            Tuple of (status, message) - DEGRADED if issues found, HEALTHY otherwise
        """
        validator = InfrastructureValidator()
        status_str, message = (
            validator.db_integrity_validator.check_database_integrity()
        )
        return HealthStatus(status_str), message

    @staticmethod
    def check_data_integrity() -> tuple[HealthStatus, str]:
        """Check for malformed or corrupted files in the roadmap.

        Returns:
            Tuple of (status, message) - DEGRADED if issues found, HEALTHY otherwise
        """
        try:
            issues_dir = Path(".roadmap/issues")

            if not issues_dir.exists():
                return HealthStatus.HEALTHY, "No issues directory to check"

            result = scan_for_data_integrity_issues(issues_dir)

            if not result["malformed_files"]:
                logger.debug("health_check_data_integrity", status="healthy")
                return HealthStatus.HEALTHY, "All files are properly formatted"

            count = len(result["malformed_files"])
            files_list = ", ".join(result["malformed_files"][:3])
            if count > 3:
                files_list += f", +{count - 3} more"

            message = (
                f"⚠️ {count} malformed file(s) found (cannot be parsed): {files_list}"
            )
            logger.warning("health_check_data_integrity", count=count)
            return HealthStatus.DEGRADED, message

        except Exception as e:
            logger.error("health_check_data_integrity_failed", error=str(e))
            return HealthStatus.UNHEALTHY, f"Error checking data integrity: {e}"

    @staticmethod
    def check_orphaned_issues(core) -> tuple[HealthStatus, str]:
        """Check for issues not assigned to any milestone.

        Returns:
            Tuple of (DEGRADED status, informational message) if issues found
        """
        try:
            orphaned = scan_for_orphaned_issues(core)

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

    @classmethod
    def run_all_checks(cls, core) -> dict[str, tuple[HealthStatus, str]]:
        """Run all health checks and return results.

        Args:
            core: Core application instance for accessing services

        Returns:
            Dictionary mapping check names to (status, message) tuples
        """
        logger.info("running_health_checks")

        checks = {
            "roadmap_directory": cls.check_roadmap_directory(),
            "state_file": cls.check_state_file(),
            "issues_directory": cls.check_issues_directory(),
            "milestones_directory": cls.check_milestones_directory(),
            "git_repository": cls.check_git_repository(),
            "database_integrity": cls.check_database_integrity(),
            "data_integrity": cls.check_data_integrity(),
            "duplicate_issues": cls.check_duplicate_issues(core),
            "folder_structure": cls.check_folder_structure(core),
            "orphaned_issues": cls.check_orphaned_issues(core),
            "old_backups": cls.check_old_backups(),
            "archivable_issues": cls.check_archivable_issues(core),
            "archivable_milestones": cls.check_archivable_milestones(core),
        }

        # Count statuses
        status_counts = {
            HealthStatus.HEALTHY: 0,
            HealthStatus.DEGRADED: 0,
            HealthStatus.UNHEALTHY: 0,
        }

        for status, _ in checks.values():
            status_counts[status] += 1

        logger.info(
            "health_checks_completed",
            healthy=status_counts[HealthStatus.HEALTHY],
            degraded=status_counts[HealthStatus.DEGRADED],
            unhealthy=status_counts[HealthStatus.UNHEALTHY],
        )

        return checks

    @staticmethod
    def get_overall_status(checks: dict[str, tuple[HealthStatus, str]]) -> HealthStatus:
        """Determine overall health status from individual checks.

        Args:
            checks: Dictionary of check results from run_all_checks()

        Returns:
            Overall health status (worst status from all checks)
        """
        statuses = [status for status, _ in checks.values()]

        # Return worst status
        if HealthStatus.UNHEALTHY in statuses:
            return HealthStatus.UNHEALTHY
        if HealthStatus.DEGRADED in statuses:
            return HealthStatus.DEGRADED
        return HealthStatus.HEALTHY
