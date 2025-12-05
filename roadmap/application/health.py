"""Health checks for monitoring application and infrastructure status.

This module orchestrates health checks from dedicated validator services:
- InfrastructureValidator: Directory, file, database, and repository checks
- DataIntegrityValidatorService: Data quality and consistency checks

The HealthCheck class delegates to these services rather than implementing checks directly.
"""

from enum import Enum

from ..shared.logging import get_logger
from .services.data_integrity_validator_service import (
    DataIntegrityValidatorService,
)
from .services.infrastructure_validator_service import (
    InfrastructureValidator,
    HealthStatus as InfrastructureHealthStatus,
)

logger = get_logger(__name__)


class HealthStatus(Enum):
    """Health status levels for system components."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"



class HealthCheck:
    """Application health checks orchestrator.

    Delegates to specialized validator services:
    - InfrastructureValidator: Infrastructure and system checks
    - DataIntegrityValidatorService: Data quality and consistency checks

    This class acts as a thin facade, coordinating checks from multiple services.
    """

    def __init__(self):
        """Initialize HealthCheck with validator services."""
        self.infrastructure_validator = InfrastructureValidator()
        self.data_integrity_service = DataIntegrityValidatorService()

    @staticmethod
    def check_roadmap_directory() -> tuple[HealthStatus, str]:
        """Check if .roadmap directory exists and is accessible.

        Delegates to InfrastructureValidator.

        Returns:
            Tuple of (status, message) describing the health check result
        """
        validator = InfrastructureValidator()
        status_str, message = validator.roadmap_dir_validator.check_roadmap_directory()
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
    def check_duplicate_issues(core) -> tuple[HealthStatus, str]:
        """Check for duplicate issues.

        Delegates to DataIntegrityValidatorService.

        Returns:
            Tuple of (status, message) describing the health check result
        """
        from .services.data_integrity_validator_service import (
            DuplicateIssuesValidator,
        )

        status_str, message = DuplicateIssuesValidator.check_duplicate_issues(core)
        return HealthStatus(status_str), message

    @staticmethod
    def check_folder_structure(core) -> tuple[HealthStatus, str]:
        """Check if issues are in correct milestone folders.

        Delegates to DataIntegrityValidatorService.

        Returns:
            Tuple of (status, message) describing the health check result
        """
        from .services.data_integrity_validator_service import (
            FolderStructureValidator,
        )

        status_str, message = FolderStructureValidator.check_folder_structure(core)
        return HealthStatus(status_str), message

    @staticmethod
    def check_old_backups() -> tuple[HealthStatus, str]:
        """Check for old backup files that could be cleaned up.

        Delegates to DataIntegrityValidatorService.

        Returns:
            Tuple of (HEALTHY status, informational message) - never degrades health
        """
        from .services.data_integrity_validator_service import BackupValidator

        status_str, message = BackupValidator.check_old_backups()
        return HealthStatus(status_str), message

    @staticmethod
    def check_archivable_issues(core) -> tuple[HealthStatus, str]:
        """Check for closed issues that could be archived.

        Delegates to DataIntegrityValidatorService.

        Returns:
            Tuple of (HEALTHY status, informational message) - never degrades health
        """
        from .services.data_integrity_validator_service import (
            ArchivableIssuesValidator,
        )

        status_str, message = ArchivableIssuesValidator.check_archivable_issues(core)
        return HealthStatus(status_str), message

    @staticmethod
    def check_archivable_milestones(core) -> tuple[HealthStatus, str]:
        """Check for closed milestones that could be archived.

        Delegates to DataIntegrityValidatorService.

        Returns:
            Tuple of (HEALTHY status, informational message) - never degrades health
        """
        from .services.data_integrity_validator_service import (
            ArchivableMilestonesValidator,
        )

        status_str, message = (
            ArchivableMilestonesValidator.check_archivable_milestones(core)
        )
        return HealthStatus(status_str), message

    @staticmethod
    def check_data_integrity() -> tuple[HealthStatus, str]:
        """Check for malformed or corrupted files in the roadmap.

        Delegates to DataIntegrityValidatorService.

        Returns:
            Tuple of (status, message) - DEGRADED if issues found, HEALTHY otherwise
        """
        from .services.data_integrity_validator_service import (
            DataIntegrityValidator,
        )

        status_str, message = DataIntegrityValidator.check_data_integrity()
        return HealthStatus(status_str), message

    @staticmethod
    def check_orphaned_issues(core) -> tuple[HealthStatus, str]:
        """Check for issues not assigned to any milestone.

        Delegates to DataIntegrityValidatorService.

        Returns:
            Tuple of (DEGRADED status, informational message) if issues found
        """
        from .services.data_integrity_validator_service import (
            OrphanedIssuesValidator,
        )

        status_str, message = OrphanedIssuesValidator.check_orphaned_issues(core)
        return HealthStatus(status_str), message

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
            "duplicate_issues": cls.check_duplicate_issues(core),
            "folder_structure": cls.check_folder_structure(core),
            "data_integrity": cls.check_data_integrity(),
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
