"""Specialized health checkers split from HealthCheck class.

Organizes health checks by domain concern:
- DirectoryHealthChecker: File system structure checks
- DataHealthChecker: Database and data integrity checks
- EntityHealthChecker: Business entity validation checks
"""

from roadmap.core.domain.health import HealthStatus


class DirectoryHealthChecker:
    """Checks health of directory structure and files."""

    @staticmethod
    def check_roadmap_directory() -> tuple[HealthStatus, str]:
        """Check if .roadmap directory exists and is accessible."""
        from roadmap.core.services.infrastructure_validator_service import (
            RoadmapDirectoryValidator,
        )

        status_str, message = RoadmapDirectoryValidator.check()
        return HealthStatus(status_str), message

    @staticmethod
    def check_state_file() -> tuple[HealthStatus, str]:
        """Check if state database exists and is readable."""
        from roadmap.core.services.infrastructure_validator_service import (
            StateFileValidator,
        )

        status_str, message = StateFileValidator.check()
        return HealthStatus(status_str), message

    @staticmethod
    def check_issues_directory() -> tuple[HealthStatus, str]:
        """Check if issues directory exists and is accessible."""
        from roadmap.core.services.infrastructure_validator_service import (
            IssuesDirectoryValidator,
        )

        status_str, message = IssuesDirectoryValidator.check()
        return HealthStatus(status_str), message

    @staticmethod
    def check_milestones_directory() -> tuple[HealthStatus, str]:
        """Check if milestones directory exists and is accessible."""
        from roadmap.core.services.infrastructure_validator_service import (
            MilestonesDirectoryValidator,
        )

        status_str, message = MilestonesDirectoryValidator.check()
        return HealthStatus(status_str), message

    @staticmethod
    def check_folder_structure(core) -> tuple[HealthStatus, str]:
        """Check if issues are in correct milestone folders."""
        from roadmap.core.services.data_integrity_validator_service import (
            FolderStructureValidator,
        )

        status_str, message = FolderStructureValidator.check()
        return HealthStatus(status_str), message

    @staticmethod
    def check_old_backups() -> tuple[HealthStatus, str]:
        """Check for old backup files that could be cleaned up."""
        from roadmap.core.services.data_integrity_validator_service import (
            BackupValidator,
        )

        status_str, message = BackupValidator.check_old_backups()
        return HealthStatus(status_str), message


class DataHealthChecker:
    """Checks health of data integrity and database."""

    @staticmethod
    def check_git_repository() -> tuple[HealthStatus, str]:
        """Check if Git repository exists and is accessible."""
        from roadmap.core.services.infrastructure_validator_service import (
            GitRepositoryValidator,
        )

        status_str, message = GitRepositoryValidator.check()
        return HealthStatus(status_str), message

    @staticmethod
    def check_database_integrity() -> tuple[HealthStatus, str]:
        """Check SQLite database integrity."""
        from roadmap.core.services.infrastructure_validator_service import (
            DatabaseIntegrityValidator,
        )

        status_str, message = DatabaseIntegrityValidator.check()
        return HealthStatus(status_str), message

    @staticmethod
    def check_data_integrity() -> tuple[HealthStatus, str]:
        """Run comprehensive data integrity checks."""
        from roadmap.core.services.data_integrity_validator_service import (
            DataIntegrityValidator,
        )

        status_str, message = DataIntegrityValidator.check_data_integrity()
        return HealthStatus(status_str), message


class EntityHealthChecker:
    """Checks health of business entities (issues, milestones)."""

    @staticmethod
    def check_duplicate_issues(core) -> tuple[HealthStatus, str]:
        """Check for duplicate issues."""
        from roadmap.core.services.data_integrity_validator_service import (
            DuplicateIssuesValidator,
        )

        status_str, message = DuplicateIssuesValidator.check()
        return HealthStatus(status_str), message

    @staticmethod
    def check_archivable_issues(core) -> tuple[HealthStatus, str]:
        """Check for closed issues that could be archived."""
        from roadmap.core.services.data_integrity_validator_service import (
            ArchivableIssuesValidator,
        )

        status_str, message = ArchivableIssuesValidator.check_archivable_issues(core)
        return HealthStatus(status_str), message

    @staticmethod
    def check_archivable_milestones(core) -> tuple[HealthStatus, str]:
        """Check for closed milestones that could be archived."""
        from roadmap.core.services.data_integrity_validator_service import (
            ArchivableMilestonesValidator,
        )

        status_str, message = ArchivableMilestonesValidator.check_archivable_milestones(
            core
        )
        return HealthStatus(status_str), message

    @staticmethod
    def check_orphaned_issues(core) -> tuple[HealthStatus, str]:
        """Check for issues not assigned to any milestone."""
        from roadmap.core.services.data_integrity_validator_service import (
            OrphanedIssuesValidator,
        )

        status_str, message = OrphanedIssuesValidator.check_orphaned_issues(core)
        return HealthStatus(status_str), message

    @staticmethod
    def check_orphaned_milestones(core) -> tuple[HealthStatus, str]:
        """Check for empty milestones with no issues."""
        from roadmap.core.services.data_integrity_validator_service import (
            OrphanedMilestonesValidator,
        )

        status_str, message = OrphanedMilestonesValidator.check()
        return HealthStatus(status_str), message

    @staticmethod
    def check_duplicate_milestones(core) -> tuple[HealthStatus, str]:
        """Check for duplicate milestone names."""
        from roadmap.core.services.data_integrity_validator_service import (
            DuplicateMilestonesValidator,
        )

        status_str, message = DuplicateMilestonesValidator.check()
        return HealthStatus(status_str), message

    @staticmethod
    def check_unlinked_issues(core) -> tuple[HealthStatus, str]:
        """Check for remote issues not linked to local issues."""
        # Note: UnlinkedIssuesValidator may not exist - skip if not available
        try:
            from roadmap.core.services.data_integrity_validator_service import (
                UnlinkedIssuesValidator,  # type: ignore[attr-defined]
            )

            status_str, message = UnlinkedIssuesValidator.check_unlinked_issues(core)
        except (ImportError, AttributeError):
            # If validator not available, skip this check
            return HealthStatus.HEALTHY, "Unlinked issues check skipped"
        return HealthStatus(status_str), message
