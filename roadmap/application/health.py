"""Health checks for monitoring application and infrastructure status."""

from enum import Enum
from pathlib import Path

from ..shared.logging import get_logger

logger = get_logger(__name__)


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
            state_db = Path(".roadmap/state.db")

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

    @classmethod
    def run_all_checks(cls) -> dict[str, tuple[HealthStatus, str]]:
        """Run all health checks and return results.

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
