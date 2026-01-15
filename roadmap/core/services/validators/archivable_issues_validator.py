"""Validator for archivable issues."""

from roadmap.common.logging import get_logger
from roadmap.common.utils.timezone_utils import now_utc
from roadmap.core.services.validator_base import HealthStatus

logger = get_logger(__name__)


class ArchivableIssuesValidator:
    """Validator for archivable issues."""

    @staticmethod
    def scan_for_archivable_issues(core, threshold_days: int = 30) -> list[dict]:
        """Scan for issues that should be archived (closed >threshold_days ago).

        Returns a list of issue dicts with id, title, status, closed date, and days_since_close.
        """
        archivable = []

        try:
            issues = core.issue_service.list_issues()
            now = now_utc()

            for issue in issues:
                # Check if issue is closed (by status or by completed_date)
                if issue.status.value == "closed" or issue.actual_end_date:
                    close_date = issue.actual_end_date or now
                    days_since_close = (now - close_date).days

                    if days_since_close > threshold_days:
                        archivable.append(
                            {
                                "id": issue.id,
                                "title": issue.title,
                                "status": issue.status.value,
                                "closed_date": close_date.isoformat()
                                if close_date
                                else None,
                                "days_since_close": days_since_close,
                            }
                        )
        except Exception as e:
            logger.debug("scan_archivable_issues_error", error=str(e))

        return archivable

    @staticmethod
    def check_archivable_issues(core) -> tuple[str, str]:
        """Check for archivable issues.

        Returns:
            Tuple of (status, message) describing the health check result
        """
        try:
            archivable = ArchivableIssuesValidator.scan_for_archivable_issues(core)

            if not archivable:
                logger.debug("health_check_archivable_issues", status="none")
                return HealthStatus.HEALTHY, "No issues to archive"

            message = (
                f"ℹ️ {len(archivable)} issue(s) eligible for archival "
                "(closed >30 days ago): Consider archiving old issues"
            )
            logger.info("health_check_archivable_issues", count=len(archivable))
            return HealthStatus.DEGRADED, message

        except Exception as e:
            logger.debug("health_check_archivable_issues_failed", error=str(e))
            return HealthStatus.HEALTHY, "Could not check for archivable issues"
