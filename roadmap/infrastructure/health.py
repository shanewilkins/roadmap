"""Health checks for monitoring application and infrastructure status.

This module orchestrates health checks from dedicated validator services:
- InfrastructureValidator: Directory, file, database, and repository checks
- DataIntegrityValidatorService: Data quality and consistency checks

The HealthCheck class delegates to these services rather than implementing checks directly.
"""

from roadmap.common.logging import get_logger
from roadmap.core.domain.health import HealthStatus
from roadmap.core.services.data_integrity_validator_service import (
    DataIntegrityValidatorService,
)
from roadmap.core.services.infrastructure_validator_service import (
    InfrastructureValidator,
)

logger = get_logger(__name__)


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

        Delegates to RoadmapDirectoryValidator.

        Returns:
            Tuple of (status, message) describing the health check result
        """
        from roadmap.core.services.infrastructure_validator_service import (
            RoadmapDirectoryValidator,
        )

        status_str, message = RoadmapDirectoryValidator.check()
        return HealthStatus(status_str), message

    @staticmethod
    def check_state_file() -> tuple[HealthStatus, str]:
        """Check if state database exists and is readable.

        Delegates to StateFileValidator.

        Returns:
            Tuple of (status, message) describing the health check result
        """
        from roadmap.core.services.infrastructure_validator_service import (
            StateFileValidator,
        )

        status_str, message = StateFileValidator.check()
        return HealthStatus(status_str), message

    @staticmethod
    def check_issues_directory() -> tuple[HealthStatus, str]:
        """Check if issues directory exists and is accessible.

        Delegates to IssuesDirectoryValidator.

        Returns:
            Tuple of (status, message) describing the health check result
        """
        from roadmap.core.services.infrastructure_validator_service import (
            IssuesDirectoryValidator,
        )

        status_str, message = IssuesDirectoryValidator.check()
        return HealthStatus(status_str), message

    @staticmethod
    def check_milestones_directory() -> tuple[HealthStatus, str]:
        """Check if milestones directory exists and is accessible.

        Delegates to MilestonesDirectoryValidator.

        Returns:
            Tuple of (status, message) describing the health check result
        """
        from roadmap.core.services.infrastructure_validator_service import (
            MilestonesDirectoryValidator,
        )

        status_str, message = MilestonesDirectoryValidator.check()
        return HealthStatus(status_str), message

    @staticmethod
    def check_git_repository() -> tuple[HealthStatus, str]:
        """Check if Git repository exists and is accessible.

        Delegates to GitRepositoryValidator.

        Returns:
            Tuple of (status, message) describing the health check result
        """
        from roadmap.core.services.infrastructure_validator_service import (
            GitRepositoryValidator,
        )

        status_str, message = GitRepositoryValidator.check()
        return HealthStatus(status_str), message

    @staticmethod
    def check_database_integrity() -> tuple[HealthStatus, str]:
        """Check SQLite database integrity.

        Delegates to DatabaseIntegrityValidator.

        Returns:
            Tuple of (status, message) - DEGRADED if issues found, HEALTHY otherwise
        """
        from roadmap.core.services.infrastructure_validator_service import (
            DatabaseIntegrityValidator,
        )

        status_str, message = DatabaseIntegrityValidator.check()
        return HealthStatus(status_str), message

    @staticmethod
    def check_duplicate_issues(core) -> tuple[HealthStatus, str]:
        """Check for duplicate issues.

        Delegates to DuplicateIssuesValidator.

        Returns:
            Tuple of (status, message) describing the health check result
        """
        from roadmap.core.services.data_integrity_validator_service import (
            DuplicateIssuesValidator,
        )

        status_str, message = DuplicateIssuesValidator.check()
        return HealthStatus(status_str), message

    @staticmethod
    def check_folder_structure(core) -> tuple[HealthStatus, str]:
        """Check if issues are in correct milestone folders.

        Delegates to FolderStructureValidator.

        Returns:
            Tuple of (status, message) describing the health check result
        """
        from roadmap.core.services.data_integrity_validator_service import (
            FolderStructureValidator,
        )

        status_str, message = FolderStructureValidator.check()
        return HealthStatus(status_str), message

    @staticmethod
    def check_old_backups() -> tuple[HealthStatus, str]:
        """Check for old backup files that could be cleaned up.

        Delegates to DataIntegrityValidatorService.

        Returns:
            Tuple of (HEALTHY status, informational message) - never degrades health
        """
        from roadmap.core.services.data_integrity_validator_service import (
            BackupValidator,
        )

        status_str, message = BackupValidator.check_old_backups()
        return HealthStatus(status_str), message

    @staticmethod
    def check_archivable_issues(core) -> tuple[HealthStatus, str]:
        """Check for closed issues that could be archived.

        Delegates to DataIntegrityValidatorService.

        Returns:
            Tuple of (HEALTHY status, informational message) - never degrades health
        """
        from roadmap.core.services.data_integrity_validator_service import (
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
        from roadmap.core.services.data_integrity_validator_service import (
            ArchivableMilestonesValidator,
        )

        status_str, message = ArchivableMilestonesValidator.check_archivable_milestones(
            core
        )
        return HealthStatus(status_str), message

    @staticmethod
    @staticmethod
    def _check_entity_comments(
        entity_list,
        entity_type_name: str,
        id_field: str = "id",
        name_field: str = "name",
    ) -> tuple[int, list[str]]:
        """Check comments on a collection of entities.

        Args:
            entity_list: List of entities to check
            entity_type_name: Name of entity type for error messages
            id_field: Field name containing entity ID/name
            name_field: Field name for display (defaults to 'name')

        Returns:
            Tuple of (total_comment_count, error_list)
        """
        from roadmap.core.services.comment_service import CommentService

        errors = []
        total_comments = 0

        try:
            for entity in entity_list:
                if hasattr(entity, "comments") and entity.comments:
                    total_comments += len(entity.comments)
                    entity_errors = CommentService.validate_comment_thread(
                        entity.comments
                    )
                    if entity_errors:
                        entity_id = getattr(entity, id_field, "Unknown")
                        errors.extend(
                            [
                                f"{entity_type_name} {entity_id}: {error}"
                                for error in entity_errors
                            ]
                        )
        except Exception as e:
            logger.warning(
                f"error_checking_{entity_type_name.lower()}_comments",
                error=str(e),
            )

        return total_comments, errors

    @staticmethod
    @staticmethod
    def _aggregate_comment_checks(
        checks: list[tuple[int, list[str]]],
    ) -> tuple[int, list[str]]:
        """Aggregate results from multiple comment check operations.

        Args:
            checks: List of (comment_count, error_list) tuples

        Returns:
            Tuple of (total_count, aggregated_errors)
        """
        total_count = sum(check[0] for check in checks)
        all_errors = []
        for _, errors in checks:
            all_errors.extend(errors)
        return total_count, all_errors

    @staticmethod
    def _format_comment_integrity_message(
        all_errors: list[str], total_comments: int
    ) -> str:
        """Format the comment integrity check message.

        Args:
            all_errors: List of validation errors found
            total_comments: Total number of comments checked

        Returns:
            Formatted message string
        """
        if all_errors:
            message = f"Found {len(all_errors)} comment validation error(s). Details: {'; '.join(all_errors[:3])}"
            if len(all_errors) > 3:
                message += f"... and {len(all_errors) - 3} more"
            return message

        return (
            f"All {total_comments} comment(s) are well-formed"
            if total_comments > 0
            else "No comments to validate"
        )

    def check_comment_integrity(core) -> tuple[HealthStatus, str]:
        """Check for malformed comments in issues, milestones, and projects.

        Returns:
            Tuple of (status, message) describing comment validation results
        """
        # Check comments across all entity types
        checks = [
            HealthCheck._check_entity_comments(
                core.issues.list(), "Issue", id_field="id"
            ),
            HealthCheck._check_entity_comments(
                core.milestones.list(), "Milestone", id_field="name", name_field="name"
            ),
            HealthCheck._check_entity_comments(
                core.projects.list(), "Project", id_field="name", name_field="name"
            ),
        ]

        total_comments, all_errors = HealthCheck._aggregate_comment_checks(checks)

        message = HealthCheck._format_comment_integrity_message(
            all_errors, total_comments
        )

        status = HealthStatus.UNHEALTHY if all_errors else HealthStatus.HEALTHY

        return status, message

    @staticmethod
    def check_data_integrity() -> tuple[HealthStatus, str]:
        """Check for malformed or corrupted files in the roadmap.

        Delegates to DataIntegrityValidatorService.

        Returns:
            Tuple of (status, message) - DEGRADED if issues found, HEALTHY otherwise
        """
        from roadmap.core.services.data_integrity_validator_service import (
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
        from roadmap.core.services.data_integrity_validator_service import (
            OrphanedIssuesValidator,
        )

        status_str, message = OrphanedIssuesValidator.check_orphaned_issues(core)
        return HealthStatus(status_str), message

    @staticmethod
    def check_orphaned_milestones(core) -> tuple[HealthStatus, str]:
        """Check for milestones not assigned to any project.

        Delegates to DataIntegrityValidatorService.

        Returns:
            Tuple of (DEGRADED status, informational message) if milestones found
        """
        from roadmap.core.services.data_integrity_validator_service import (
            OrphanedMilestonesValidator,
        )

        status_str, message = OrphanedMilestonesValidator.perform_check()
        return HealthStatus(status_str), message

    @staticmethod
    def check_duplicate_milestones(core) -> tuple[HealthStatus, str]:
        """Check for duplicate milestones (by file and name).

        Delegates to DataIntegrityValidatorService.

        Returns:
            Tuple of (DEGRADED status, informational message) if duplicates found
        """
        from roadmap.core.services.data_integrity_validator_service import (
            DuplicateMilestonesValidator,
        )

        status_str, message = DuplicateMilestonesValidator.perform_check()
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
            "duplicate_milestones": cls.check_duplicate_milestones(core),
            "folder_structure": cls.check_folder_structure(core),
            "data_integrity": cls.check_data_integrity(),
            "orphaned_issues": cls.check_orphaned_issues(core),
            "orphaned_milestones": cls.check_orphaned_milestones(core),
            "old_backups": cls.check_old_backups(),
            "archivable_issues": cls.check_archivable_issues(core),
            "archivable_milestones": cls.check_archivable_milestones(core),
            "comment_integrity": cls.check_comment_integrity(core),
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
