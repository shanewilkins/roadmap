"""Validator for missing headlines in issues, milestones, and projects."""

from roadmap.common.logging import get_logger
from roadmap.core.services.validator_base import BaseValidator, HealthStatus

logger = get_logger(__name__)


class MissingHeadlinesValidator(BaseValidator):
    """Validator for missing headlines in entities."""

    @staticmethod
    def get_check_name() -> str:
        """Get the name of this check.

        Returns:
            String identifier for the missing_headlines check.
        """
        return "missing_headlines"

    @staticmethod
    def _collect_missing_headline_ids(list_callable, missing_list: list) -> None:
        """Append IDs of entities with empty headlines to *missing_list*."""
        try:
            for entity in list_callable():
                if not entity.headline or entity.headline.strip() == "":
                    missing_list.append(entity.id)
        except (AttributeError, TypeError):
            pass

    @staticmethod
    def check_missing_headlines(core) -> tuple[str, str]:
        """Check for entities with missing or empty headlines.

        Returns:
            Tuple of (status, message) describing the health check result
        """
        missing_entities: dict[str, list] = {
            "issues": [],
            "milestones": [],
            "projects": [],
        }

        try:
            MissingHeadlinesValidator._collect_missing_headline_ids(
                core.issue_service.list_issues, missing_entities["issues"]
            )
            MissingHeadlinesValidator._collect_missing_headline_ids(
                core.milestone_service.list_milestones, missing_entities["milestones"]
            )
            MissingHeadlinesValidator._collect_missing_headline_ids(
                core.project_service.list_projects, missing_entities["projects"]
            )
        except Exception as e:
            logger.debug("error_checking_headlines", error=str(e))
            return (
                HealthStatus.DEGRADED,
                f"Error checking headlines: {str(e)}",
            )

        # Count missing headlines
        total_missing = (
            len(missing_entities["issues"])
            + len(missing_entities["milestones"])
            + len(missing_entities["projects"])
        )

        if total_missing == 0:
            return HealthStatus.HEALTHY, "All entities have headlines"

        # Build detailed message
        parts = []
        if missing_entities["issues"]:
            parts.append(f"{len(missing_entities['issues'])} issue(s)")
        if missing_entities["milestones"]:
            parts.append(f"{len(missing_entities['milestones'])} milestone(s)")
        if missing_entities["projects"]:
            parts.append(f"{len(missing_entities['projects'])} project(s)")

        message = (
            f"⚠️ {total_missing} entity(ies) missing headlines: {', '.join(parts)}. "
            "Run 'roadmap fix missing-headlines' to auto-populate from content"
        )
        return HealthStatus.DEGRADED, message

    @staticmethod
    def perform_check(core=None) -> tuple[str, str]:
        """Check for missing headlines.

        Args:
            core: RoadmapCore instance (optional, for backward compatibility)

        Returns:
            Tuple of (status, message) describing the health check result
        """
        # For now, return healthy - actual implementation will use core
        return HealthStatus.HEALTHY, "Headlines validation not yet fully integrated"
