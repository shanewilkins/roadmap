"""Health checks for monitoring application and infrastructure status."""

import re
from collections import defaultdict
from enum import Enum
from pathlib import Path

from ..shared.logging import get_logger

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


class HealthStatus(Enum):
    """Health status levels for system components."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class HealthCheck:
    """Application health checks for monitoring system status.

    This class provides methods to check the health of various system
    components including file system, database, and Git repository.
    """

    @staticmethod
    def check_roadmap_directory() -> tuple[HealthStatus, str]:
        """Check if .roadmap directory exists and is accessible.

        Returns:
            Tuple of (status, message) describing the health check result
        """
        try:
            roadmap_dir = Path(".roadmap")
            if not roadmap_dir.exists():
                return HealthStatus.DEGRADED, ".roadmap directory not initialized"

            if not roadmap_dir.is_dir():
                return HealthStatus.UNHEALTHY, ".roadmap exists but is not a directory"

            # Check if directory is writable
            test_file = roadmap_dir / ".health_check"
            try:
                test_file.touch()
                test_file.unlink()
            except OSError:
                return HealthStatus.DEGRADED, ".roadmap directory is not writable"

            logger.debug("health_check_roadmap_directory", status="healthy")
            return HealthStatus.HEALTHY, ".roadmap directory is accessible and writable"

        except Exception as e:
            logger.error("health_check_roadmap_directory_failed", error=str(e))
            return HealthStatus.UNHEALTHY, f"Error checking .roadmap directory: {e}"

    @staticmethod
    def check_state_file() -> tuple[HealthStatus, str]:
        """Check if state database exists and is readable.

        Returns:
            Tuple of (status, message) describing the health check result
        """
        try:
            state_db = Path(".roadmap/db/state.db")

            if not state_db.exists():
                return (
                    HealthStatus.DEGRADED,
                    "state.db not found (project not initialized)",
                )

            # Check if file is readable and has content
            try:
                size = state_db.stat().st_size
                if size == 0:
                    return HealthStatus.DEGRADED, "state.db is empty"

                # Try to open it to verify it's accessible
                with open(state_db, "rb") as f:
                    f.read(16)  # Read SQLite header

            except OSError as e:
                return HealthStatus.UNHEALTHY, f"Cannot read state.db: {e}"

            logger.debug("health_check_state_file", status="healthy")
            return HealthStatus.HEALTHY, "state.db is accessible and readable"

        except Exception as e:
            logger.error("health_check_state_file_failed", error=str(e))
            return HealthStatus.UNHEALTHY, f"Error checking state.db: {e}"

    @staticmethod
    def check_issues_directory() -> tuple[HealthStatus, str]:
        """Check if issues directory exists and is accessible.

        Returns:
            Tuple of (status, message) describing the health check result
        """
        try:
            issues_dir = Path(".roadmap/issues")

            if not issues_dir.exists():
                return HealthStatus.DEGRADED, "issues directory not found"

            if not issues_dir.is_dir():
                return (
                    HealthStatus.UNHEALTHY,
                    "issues path exists but is not a directory",
                )

            # Check if directory is readable
            try:
                list(issues_dir.iterdir())
            except OSError as e:
                return HealthStatus.UNHEALTHY, f"Cannot read issues directory: {e}"

            logger.debug("health_check_issues_directory", status="healthy")
            return HealthStatus.HEALTHY, "issues directory is accessible"

        except Exception as e:
            logger.error("health_check_issues_directory_failed", error=str(e))
            return HealthStatus.UNHEALTHY, f"Error checking issues directory: {e}"

    @staticmethod
    def check_milestones_directory() -> tuple[HealthStatus, str]:
        """Check if milestones directory exists and is accessible.

        Returns:
            Tuple of (status, message) describing the health check result
        """
        try:
            milestones_dir = Path(".roadmap/milestones")

            if not milestones_dir.exists():
                return HealthStatus.DEGRADED, "milestones directory not found"

            if not milestones_dir.is_dir():
                return (
                    HealthStatus.UNHEALTHY,
                    "milestones path exists but is not a directory",
                )

            # Check if directory is readable
            try:
                list(milestones_dir.iterdir())
            except OSError as e:
                return HealthStatus.UNHEALTHY, f"Cannot read milestones directory: {e}"

            logger.debug("health_check_milestones_directory", status="healthy")
            return HealthStatus.HEALTHY, "milestones directory is accessible"

        except Exception as e:
            logger.error("health_check_milestones_directory_failed", error=str(e))
            return HealthStatus.UNHEALTHY, f"Error checking milestones directory: {e}"

    @staticmethod
    def check_git_repository() -> tuple[HealthStatus, str]:
        """Check if Git repository exists and is accessible.

        Returns:
            Tuple of (status, message) describing the health check result
        """
        try:
            git_dir = Path(".git")

            if not git_dir.exists():
                return HealthStatus.DEGRADED, "Git repository not initialized"

            if not git_dir.is_dir():
                return HealthStatus.UNHEALTHY, ".git exists but is not a directory"

            # Check if HEAD file exists (basic git repo validation)
            head_file = git_dir / "HEAD"
            if not head_file.exists():
                return (
                    HealthStatus.UNHEALTHY,
                    "Git repository appears corrupt (no HEAD)",
                )

            logger.debug("health_check_git_repository", status="healthy")
            return HealthStatus.HEALTHY, "Git repository is accessible"

        except Exception as e:
            logger.error("health_check_git_repository_failed", error=str(e))
            return HealthStatus.UNHEALTHY, f"Error checking Git repository: {e}"

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
            "duplicate_issues": cls.check_duplicate_issues(core),
            "folder_structure": cls.check_folder_structure(core),
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
