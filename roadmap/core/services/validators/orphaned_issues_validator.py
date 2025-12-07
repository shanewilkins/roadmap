"""Validator for orphaned issues."""

from pathlib import Path

from roadmap.common.logging import get_logger
from roadmap.core.services.base_validator import HealthStatus

logger = get_logger(__name__)


class OrphanedIssuesValidator:
    """Validator for orphaned issues."""

    @staticmethod
    def scan_for_orphaned_issues(core) -> list[dict]:
        """Scan for issues not assigned to any milestone (not in backlog either).

        Returns a list of orphaned issue dicts with id, title, and location.
        """
        orphaned = []

        try:
            issues_dir = Path(".roadmap/issues").resolve()
            if not issues_dir.exists():
                return orphaned

            issues = core.issue_service.list_issues()

            for issue in issues:
                # Issue is orphaned if milestone is None or empty string
                if not issue.milestone or issue.milestone == "":
                    orphaned.append(
                        {
                            "id": issue.id,
                            "title": issue.title,
                            "location": str(
                                issues_dir / f"{issue.id}*.md"
                            ),  # Pattern for file
                        }
                    )

        except Exception as e:
            logger.debug("scan_orphaned_issues_error", error=str(e))

        return orphaned

    @staticmethod
    def check_orphaned_issues(core) -> tuple[str, str]:
        """Check for orphaned issues.

        Returns:
            Tuple of (status, message) describing the health check result
        """
        try:
            orphaned = OrphanedIssuesValidator.scan_for_orphaned_issues(core)

            if not orphaned:
                logger.debug("health_check_orphaned_issues", status="none")
                return HealthStatus.HEALTHY, "No orphaned issues found"

            count = len(orphaned)
            message = (
                f"⚠️ {count} orphaned issue(s) found (not in any milestone folder): "
                "These issues are disconnected from your milestone structure"
            )
            logger.warning("health_check_orphaned_issues", count=count)
            return HealthStatus.DEGRADED, message

        except Exception as e:
            logger.debug("health_check_orphaned_issues_failed", error=str(e))
            return HealthStatus.HEALTHY, "Could not check for orphaned issues"
