"""
Infrastructure validators for health checks.

Handles validation of:
- Roadmap directory structure
- State database file
- Issues and milestones directories
- Git repository status
- Database integrity
"""

from pathlib import Path

from roadmap.shared.logging import get_logger

logger = get_logger(__name__)


class HealthStatus:
    """Health status constants."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class RoadmapDirectoryValidator:
    """Validator for .roadmap directory."""

    @staticmethod
    def check_roadmap_directory() -> tuple[str, str]:
        """Check if .roadmap directory exists and is accessible.

        Returns:
            Tuple of (status, message) describing the health check result
        """
        try:
            roadmap_dir = Path(".roadmap")
            if not roadmap_dir.exists():
                return HealthStatus.DEGRADED, ".roadmap directory not initialized"

            if not roadmap_dir.is_dir():
                return (
                    HealthStatus.UNHEALTHY,
                    ".roadmap exists but is not a directory",
                )

            # Check if directory is writable
            test_file = roadmap_dir / ".health_check"
            try:
                test_file.touch()
                test_file.unlink()
            except OSError:
                return HealthStatus.DEGRADED, ".roadmap directory is not writable"

            logger.debug("health_check_roadmap_directory", status="healthy")
            return (
                HealthStatus.HEALTHY,
                ".roadmap directory is accessible and writable",
            )

        except Exception as e:
            logger.error("health_check_roadmap_directory_failed", error=str(e))
            return HealthStatus.UNHEALTHY, f"Error checking .roadmap directory: {e}"


class StateFileValidator:
    """Validator for state database file."""

    @staticmethod
    def check_state_file() -> tuple[str, str]:
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


class IssuesDirectoryValidator:
    """Validator for issues directory."""

    @staticmethod
    def check_issues_directory() -> tuple[str, str]:
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


class MilestonesDirectoryValidator:
    """Validator for milestones directory."""

    @staticmethod
    def check_milestones_directory() -> tuple[str, str]:
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
                return (
                    HealthStatus.UNHEALTHY,
                    f"Cannot read milestones directory: {e}",
                )

            logger.debug("health_check_milestones_directory", status="healthy")
            return HealthStatus.HEALTHY, "milestones directory is accessible"

        except Exception as e:
            logger.error("health_check_milestones_directory_failed", error=str(e))
            return HealthStatus.UNHEALTHY, f"Error checking milestones directory: {e}"


class GitRepositoryValidator:
    """Validator for Git repository."""

    @staticmethod
    def check_git_repository() -> tuple[str, str]:
        """Check if Git repository exists and is accessible.

        Returns:
            Tuple of (status, message) describing the health check result
        """
        try:
            git_dir = Path(".git")

            if not git_dir.exists():
                return (
                    HealthStatus.DEGRADED,
                    "not a Git repository (.git not found)",
                )

            if not git_dir.is_dir():
                return (
                    HealthStatus.UNHEALTHY,
                    ".git exists but is not a directory",
                )

            logger.debug("health_check_git_repository", status="healthy")
            return HealthStatus.HEALTHY, "Git repository is accessible"

        except Exception as e:
            logger.error("health_check_git_repository_failed", error=str(e))
            return HealthStatus.UNHEALTHY, f"Error checking Git repository: {e}"


class DatabaseIntegrityValidator:
    """Validator for database integrity."""

    @staticmethod
    def check_database_integrity() -> tuple[str, str]:
        """Check if database is accessible and can be queried.

        Returns:
            Tuple of (status, message) describing the health check result
        """
        try:
            # Import here to avoid circular imports
            from roadmap.infrastructure.storage import StateManager

            try:
                state_mgr = StateManager()
                # Try a simple query to verify DB is healthy
                conn = state_mgr._get_connection()
                conn.execute("SELECT 1")
                logger.debug("health_check_database_integrity", status="healthy")
                return HealthStatus.HEALTHY, "Database is accessible and responsive"
            except Exception as e:
                logger.error(
                    "health_check_database_integrity_query_failed",
                    error=str(e),
                )
                return (
                    HealthStatus.UNHEALTHY,
                    f"Database query failed: {e}",
                )

        except Exception as e:
            logger.error("health_check_database_integrity_failed", error=str(e))
            return (
                HealthStatus.UNHEALTHY,
                f"Error checking database integrity: {e}",
            )


class InfrastructureValidator:
    """Orchestrator for infrastructure validation checks."""

    def __init__(self):
        """Initialize infrastructure validator."""
        self.roadmap_dir_validator = RoadmapDirectoryValidator()
        self.state_file_validator = StateFileValidator()
        self.issues_dir_validator = IssuesDirectoryValidator()
        self.milestones_dir_validator = MilestonesDirectoryValidator()
        self.git_repo_validator = GitRepositoryValidator()
        self.db_integrity_validator = DatabaseIntegrityValidator()

    def run_all_infrastructure_checks(self) -> dict[str, tuple[str, str]]:
        """Run all infrastructure validators.

        Returns:
            Dictionary mapping check names to (status, message) tuples
        """
        checks = {}

        try:
            checks["roadmap_directory"] = (
                RoadmapDirectoryValidator.check_roadmap_directory()
            )
            checks["state_file"] = StateFileValidator.check_state_file()
            checks["issues_directory"] = (
                IssuesDirectoryValidator.check_issues_directory()
            )
            checks["milestones_directory"] = (
                MilestonesDirectoryValidator.check_milestones_directory()
            )
            checks["git_repository"] = GitRepositoryValidator.check_git_repository()
            checks["database_integrity"] = (
                DatabaseIntegrityValidator.check_database_integrity()
            )

            return checks
        except Exception as e:
            logger.error(
                "infrastructure_validation_failed",
                error=str(e),
            )
            return {
                "error": (
                    HealthStatus.UNHEALTHY,
                    f"Infrastructure validation failed: {e}",
                )
            }

    def get_overall_status(self, checks: dict) -> str:
        """Get overall status from all checks.

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
