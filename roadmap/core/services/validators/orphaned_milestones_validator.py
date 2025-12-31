"""Validator for orphaned milestones."""

from roadmap.common.logging import get_logger
from roadmap.core.services.base_validator import BaseValidator, HealthStatus
from roadmap.infrastructure.core import RoadmapCore

logger = get_logger(__name__)


class OrphanedMilestonesValidator(BaseValidator):
    """Validator for orphaned milestones (not assigned to any project)."""

    @staticmethod
    def get_check_name() -> str:
        """Get the name of this check.

        Returns:
            String identifier for the orphaned_milestones check.
        """
        return "orphaned_milestones"

    @staticmethod
    def scan_for_orphaned_milestones(core) -> list[dict]:
        """Scan for milestones not assigned to any project.

        Returns a list of orphaned milestone dicts with name, description, and details.
        """
        orphaned = []

        try:
            all_milestones = core.milestones.list()
            all_projects = core.projects.list()

            # Build set of milestone names assigned to projects
            assigned_milestone_names = set()
            for project in all_projects:
                assigned_milestone_names.update(project.milestones)

            # Find milestones not in any project
            for milestone in all_milestones:
                if milestone.name not in assigned_milestone_names:
                    orphaned.append(
                        {
                            "name": milestone.name,
                            "description": milestone.description or "(no description)",
                            "status": milestone.status.value,
                            "created": milestone.created.isoformat()
                            if milestone.created
                            else None,
                        }
                    )

        except Exception as e:
            logger.debug("scan_orphaned_milestones_error", error=str(e))

        return orphaned

    @staticmethod
    def perform_check() -> tuple[str, str]:
        """Check for orphaned milestones.

        Returns:
            Tuple of (status, message) describing the health check result
        """
        try:
            core = RoadmapCore()
            orphaned = OrphanedMilestonesValidator.scan_for_orphaned_milestones(core)

            if not orphaned:
                logger.debug("health_check_orphaned_milestones", status="none")
                return HealthStatus.HEALTHY, "No orphaned milestones found"

            count = len(orphaned)
            message = (
                f"⚠️ {count} orphaned milestone(s) found (not assigned to any project): "
                "These milestones should be assigned to a project or deleted"
            )
            logger.warning("health_check_orphaned_milestones", count=count)
            return HealthStatus.DEGRADED, message

        except Exception as e:
            logger.debug("health_check_orphaned_milestones_failed", error=str(e))
            return HealthStatus.HEALTHY, "Could not check for orphaned milestones"
