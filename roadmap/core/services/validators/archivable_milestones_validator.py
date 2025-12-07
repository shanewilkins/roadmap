"""Validator for archivable milestones."""

from datetime import datetime

from roadmap.common.logging import get_logger
from roadmap.core.services.base_validator import HealthStatus

logger = get_logger(__name__)


class ArchivableMilestonesValidator:
    """Validator for archivable milestones."""

    @staticmethod
    def scan_for_archivable_milestones(core, threshold_days: int = 14) -> list[dict]:
        """Scan for milestones that should be archived (completed >threshold_days ago).

        Returns a list of milestone dicts with name, status, closed date, issue count, and days_since_close.
        """
        archivable = []

        try:
            milestones = core.milestone_service.list_milestones()
            now = datetime.now()

            for milestone in milestones:
                if milestone.status.value == "closed" and milestone.closed_at:
                    days_since_close = (now - milestone.closed_at).days

                    if days_since_close > threshold_days:
                        archivable.append(
                            {
                                "name": milestone.name,
                                "status": milestone.status.value,
                                "closed_date": milestone.closed_at.isoformat(),
                                "days_since_close": days_since_close,
                            }
                        )
        except Exception as e:
            logger.debug("scan_archivable_milestones_error", error=str(e))

        return archivable

    @staticmethod
    def check_archivable_milestones(core) -> tuple[str, str]:
        """Check for archivable milestones.

        Returns:
            Tuple of (status, message) describing the health check result
        """
        try:
            archivable = ArchivableMilestonesValidator.scan_for_archivable_milestones(
                core
            )

            if not archivable:
                logger.debug("health_check_archivable_milestones", status="none")
                return HealthStatus.HEALTHY, "No milestones to archive"

            message = (
                f"ℹ️ {len(archivable)} milestone(s) eligible for archival "
                "(closed >14 days ago): Consider archiving old milestones"
            )
            logger.info("health_check_archivable_milestones", count=len(archivable))
            return HealthStatus.DEGRADED, message

        except Exception as e:
            logger.debug("health_check_archivable_milestones_failed", error=str(e))
            return HealthStatus.HEALTHY, "Could not check for archivable milestones"
