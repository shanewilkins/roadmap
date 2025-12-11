"""Data integrity validator service orchestrator.

Coordinates all data integrity validators and provides a unified interface
for running health checks across the system.
"""

from roadmap.common.logging import get_logger
from roadmap.core.services.base_validator import HealthStatus
from roadmap.core.services.validators.health_status_utils import (
    get_overall_status,
)
from roadmap.core.services.validators import (
    ArchivableIssuesValidator,
    ArchivableMilestonesValidator,
    BackupValidator,
    DataIntegrityValidator,
    DuplicateIssuesValidator,
    FolderStructureValidator,
    OrphanedIssuesValidator,
)

logger = get_logger(__name__)

# Re-export validators for backward compatibility - use same list as validators module
from roadmap.core.services.validators import __all__ as _validators_all

__all__ = ["DataIntegrityValidatorService"] + _validators_all


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
            checks["duplicate_issues"] = DuplicateIssuesValidator.perform_check()
            checks["folder_structure"] = FolderStructureValidator.perform_check()
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
        return get_overall_status(checks)
