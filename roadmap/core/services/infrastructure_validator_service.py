"""
Infrastructure validators for health checks.

Handles validation of:
- Roadmap directory structure
- State database file
- Issues and milestones directories
- Git repository status
- Database integrity

Uses BaseValidator abstract class to eliminate boilerplate and ensure
consistent error handling and logging across all validators.
"""

from pathlib import Path

from roadmap.common.logging import get_logger
from roadmap.core.services.base_validator import BaseValidator, HealthStatus

logger = get_logger(__name__)


class RoadmapDirectoryValidator(BaseValidator):
    """Validator for .roadmap directory."""

    @staticmethod
    def get_check_name() -> str:
        return "roadmap_directory"

    @staticmethod
    def perform_check() -> tuple[str, str]:
        """Check if .roadmap directory exists and is accessible.

        Returns:
            Tuple of (status, message) describing the health check result
        """
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

        return (
            HealthStatus.HEALTHY,
            ".roadmap directory is accessible and writable",
        )


class StateFileValidator(BaseValidator):
    """Validator for state database file."""

    @staticmethod
    def get_check_name() -> str:
        return "state_file"

    @staticmethod
    def perform_check() -> tuple[str, str]:
        """Check if state database exists and is readable.

        Returns:
            Tuple of (status, message) describing the health check result
        """
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

        return HealthStatus.HEALTHY, "state.db is accessible and readable"


class IssuesDirectoryValidator(BaseValidator):
    """Validator for issues directory."""

    @staticmethod
    def get_check_name() -> str:
        return "issues_directory"

    @staticmethod
    def perform_check() -> tuple[str, str]:
        """Check if issues directory exists and is accessible.

        Returns:
            Tuple of (status, message) describing the health check result
        """
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

        return HealthStatus.HEALTHY, "issues directory is accessible"


class MilestonesDirectoryValidator(BaseValidator):
    """Validator for milestones directory."""

    @staticmethod
    def get_check_name() -> str:
        return "milestones_directory"

    @staticmethod
    def perform_check() -> tuple[str, str]:
        """Check if milestones directory exists and is accessible.

        Returns:
            Tuple of (status, message) describing the health check result
        """
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

        return HealthStatus.HEALTHY, "milestones directory is accessible"


class GitRepositoryValidator(BaseValidator):
    """Validator for Git repository."""

    @staticmethod
    def get_check_name() -> str:
        return "git_repository"

    @staticmethod
    def perform_check() -> tuple[str, str]:
        """Check if Git repository exists and is accessible.

        Returns:
            Tuple of (status, message) describing the health check result
        """
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

        return HealthStatus.HEALTHY, "Git repository is accessible"


class DatabaseIntegrityValidator(BaseValidator):
    """Validator for database integrity."""

    @staticmethod
    def get_check_name() -> str:
        return "database_integrity"

    @staticmethod
    def perform_check() -> tuple[str, str]:
        """Check if database is accessible and can be queried.

        Returns:
            Tuple of (status, message) describing the health check result
        """
        # Import here to avoid circular imports
        from roadmap.adapters.persistence.storage import StateManager

        try:
            state_mgr = StateManager()
            # Try a simple query to verify DB is healthy
            conn = state_mgr._get_connection()
            conn.execute("SELECT 1")
            return HealthStatus.HEALTHY, "Database is accessible and responsive"
        except Exception as e:
            return (
                HealthStatus.UNHEALTHY,
                f"Database query failed: {e}",
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
            checks["roadmap_directory"] = RoadmapDirectoryValidator.check()
            checks["state_file"] = StateFileValidator.check()
            checks["issues_directory"] = IssuesDirectoryValidator.check()
            checks["milestones_directory"] = MilestonesDirectoryValidator.check()
            checks["git_repository"] = GitRepositoryValidator.check()
            checks["database_integrity"] = DatabaseIntegrityValidator.check()

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
