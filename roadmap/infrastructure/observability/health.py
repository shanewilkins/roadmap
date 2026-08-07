"""Health checks for monitoring application and infrastructure status.

This module orchestrates health checks by delegating to specialized checkers:
- DirectoryHealthChecker: File system structure checks
- DataHealthChecker: Database and data integrity checks
- EntityHealthChecker: Business entity validation checks

These replace the original monolithic HealthCheck class to improve separation of concerns.
"""

from collections.abc import Mapping

from roadmap.common.logging import get_logger
from roadmap.core.domain.health import HealthStatus
from roadmap.infrastructure.observability.specialized_health_checkers import (
    DataHealthChecker,
    DirectoryHealthChecker,
    EntityHealthChecker,
)

logger = get_logger(__name__)


class HealthCheck:
    """Application health checks orchestrator.

    Delegates to specialized health checkers organized by concern:
    - DirectoryHealthChecker: File system and directory checks
    - DataHealthChecker: Database and data integrity checks
    - EntityHealthChecker: Business entity validation checks

    This thin facade coordinates checks across multiple domain areas
    while keeping each area's logic properly separated.
    """

    def __init__(self):
        """Initialize HealthCheck with specialized checkers."""
        self.directory_checker = DirectoryHealthChecker()
        self.data_checker = DataHealthChecker()
        self.entity_checker = EntityHealthChecker()

    # Delegate to DirectoryHealthChecker
    @staticmethod
    def check_roadmap_directory() -> tuple[HealthStatus, str]:
        """Check if .roadmap directory exists and is accessible."""
        return DirectoryHealthChecker.check_roadmap_directory()

    @staticmethod
    def check_state_file() -> tuple[HealthStatus, str]:
        """Check if state database exists and is readable."""
        return DirectoryHealthChecker.check_state_file()

    @staticmethod
    def check_issues_directory() -> tuple[HealthStatus, str]:
        """Check if issues directory exists and is accessible."""
        return DirectoryHealthChecker.check_issues_directory()

    @staticmethod
    def check_milestones_directory() -> tuple[HealthStatus, str]:
        """Check if milestones directory exists and is accessible."""
        return DirectoryHealthChecker.check_milestones_directory()

    @staticmethod
    def check_folder_structure(core) -> tuple[HealthStatus, str]:
        """Check if issues are in correct milestone folders."""
        return DirectoryHealthChecker.check_folder_structure(core)

    @staticmethod
    def check_old_backups() -> tuple[HealthStatus, str]:
        """Check for old backup files that could be cleaned up."""
        return DirectoryHealthChecker.check_old_backups()

    # Delegate to DataHealthChecker
    @staticmethod
    def check_git_repository() -> tuple[HealthStatus, str]:
        """Check if Git repository exists and is accessible."""
        return DataHealthChecker.check_git_repository()

    @staticmethod
    def check_database_integrity() -> tuple[HealthStatus, str]:
        """Check SQLite database integrity."""
        return DataHealthChecker.check_database_integrity()

    @staticmethod
    def check_data_integrity() -> tuple[HealthStatus, str]:
        """Run comprehensive data integrity checks."""
        return DataHealthChecker.check_data_integrity()

    # Delegate to EntityHealthChecker
    @staticmethod
    def check_duplicate_issues(core) -> tuple[HealthStatus, str]:
        """Check for duplicate issues."""
        return EntityHealthChecker.check_duplicate_issues(core)

    @staticmethod
    def check_archivable_issues(core) -> tuple[HealthStatus, str]:
        """Check for closed issues that could be archived."""
        return EntityHealthChecker.check_archivable_issues(core)

    @staticmethod
    def check_archivable_milestones(core) -> tuple[HealthStatus, str]:
        """Check for closed milestones that could be archived."""
        return EntityHealthChecker.check_archivable_milestones(core)

    @staticmethod
    def check_orphaned_issues(core) -> tuple[HealthStatus, str]:
        """Check for issues not assigned to any milestone."""
        return EntityHealthChecker.check_orphaned_issues(core)

    @staticmethod
    def check_orphaned_milestones(core) -> tuple[HealthStatus, str]:
        """Check for empty milestones with no issues."""
        return EntityHealthChecker.check_orphaned_milestones(core)

    @staticmethod
    def check_duplicate_milestones(core) -> tuple[HealthStatus, str]:
        """Check for duplicate milestone names."""
        return EntityHealthChecker.check_duplicate_milestones(core)

    @staticmethod
    def check_unlinked_issues(core) -> tuple[HealthStatus, str]:
        """Check for remote issues not linked to local issues."""
        return EntityHealthChecker.check_unlinked_issues(core)

    @staticmethod
    def run_all_checks(core) -> dict[str, tuple[HealthStatus, str]]:
        """Run all health checks.

        Args:
            core: RoadmapCore instance for entity checks

        Returns:
            Dictionary mapping check names to (status, message) tuples
        """
        checks = {}

        # Directory checks
        checks["roadmap_directory"] = HealthCheck.check_roadmap_directory()
        checks["state_file"] = HealthCheck.check_state_file()
        checks["issues_directory"] = HealthCheck.check_issues_directory()
        checks["milestones_directory"] = HealthCheck.check_milestones_directory()

        # Data checks
        checks["git_repository"] = HealthCheck.check_git_repository()
        checks["database_integrity"] = HealthCheck.check_database_integrity()
        checks["data_integrity"] = HealthCheck.check_data_integrity()

        # Entity checks (require core)
        if core:
            checks["folder_structure"] = HealthCheck.check_folder_structure(core)
            checks["duplicate_issues"] = HealthCheck.check_duplicate_issues(core)
            checks["archivable_issues"] = HealthCheck.check_archivable_issues(core)
            checks["archivable_milestones"] = HealthCheck.check_archivable_milestones(
                core
            )
            checks["orphaned_issues"] = HealthCheck.check_orphaned_issues(core)
            checks["orphaned_milestones"] = HealthCheck.check_orphaned_milestones(core)
            checks["duplicate_milestones"] = HealthCheck.check_duplicate_milestones(
                core
            )
            checks["unlinked_issues"] = HealthCheck.check_unlinked_issues(core)

        checks["old_backups"] = HealthCheck.check_old_backups()

        return checks

    @staticmethod
    def get_overall_status(
        checks: Mapping[str, tuple[HealthStatus, str]],
    ) -> HealthStatus:
        """Get overall health status from check results.

        Args:
            checks: Dictionary of check results

        Returns:
            Overall HealthStatus (UNHEALTHY if any unhealthy, DEGRADED if any degraded, else HEALTHY)
        """
        if not checks:
            return HealthStatus.HEALTHY

        has_unhealthy = False
        has_degraded = False

        for status, _message in checks.values():
            if status == HealthStatus.UNHEALTHY:
                has_unhealthy = True
            elif status == HealthStatus.DEGRADED:
                has_degraded = True

        if has_unhealthy:
            return HealthStatus.UNHEALTHY
        elif has_degraded:
            return HealthStatus.DEGRADED
        else:
            return HealthStatus.HEALTHY
