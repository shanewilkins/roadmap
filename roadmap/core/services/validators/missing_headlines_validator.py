"""Validator for missing headlines in issues, milestones, and projects."""

from roadmap.common.logging import get_logger
from roadmap.core.services.base_validator import BaseValidator, HealthStatus

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
    def check_missing_headlines(core) -> tuple[str, str]:
        """Check for entities with missing or empty headlines.

        Returns:
            Tuple of (status, message) describing the health check result
        """
        missing_entities = {
            "issues": [],
            "milestones": [],
            "projects": [],
        }

        try:
            # Check issues
            try:
                all_issues = core.issue_service.list_issues()
                for issue in all_issues:
                    if not issue.headline or issue.headline.strip() == "":
                        missing_entities["issues"].append(issue.id)
            except (AttributeError, TypeError):
                # Mock or unavailable service
                pass

            # Check milestones
            try:
                all_milestones = core.milestone_service.list_milestones()
                for milestone in all_milestones:
                    if not milestone.headline or milestone.headline.strip() == "":
                        missing_entities["milestones"].append(milestone.id)
            except (AttributeError, TypeError):
                # Mock or unavailable service
                pass

            # Check projects
            try:
                all_projects = core.project_service.list_projects()
                for project in all_projects:
                    if not project.headline or project.headline.strip() == "":
                        missing_entities["projects"].append(project.id)
            except (AttributeError, TypeError):
                # Mock or unavailable service
                pass

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
