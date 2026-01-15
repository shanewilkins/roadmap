"""Validator for data integrity."""

from pathlib import Path

from roadmap.common.logging import get_logger
from roadmap.core.services.validator_base import HealthStatus

logger = get_logger(__name__)


class DataIntegrityValidator:
    """Validator for data integrity."""

    @staticmethod
    def scan_for_data_integrity_issues(
        issues_dir: Path,
    ) -> dict[str, list[str]]:
        """Scan for data integrity issues (orphaned/missing files).

        Returns a dict with:
        - 'malformed_files': List of files that couldn't be parsed
        """
        result = {"malformed_files": []}

        if not issues_dir.exists():
            return result

        # Scan all issue files recursively
        for issue_file in issues_dir.rglob("*.md"):
            if ".backup" in issue_file.name:
                continue

            try:
                from roadmap.adapters.persistence.parser import IssueParser

                IssueParser.parse_issue_file(issue_file)
            except Exception:
                # File couldn't be parsed
                result["malformed_files"].append(
                    str(issue_file.relative_to(issues_dir))
                )

        return result

    @staticmethod
    def check_data_integrity() -> tuple[str, str]:
        """Check data integrity.

        Returns:
            Tuple of (status, message) describing the health check result
        """
        try:
            issues_dir = Path(".roadmap/issues")
            if not issues_dir.exists():
                return (
                    HealthStatus.HEALTHY,
                    "Issues directory not found (not initialized yet)",
                )

            integrity_issues = DataIntegrityValidator.scan_for_data_integrity_issues(
                issues_dir
            )

            if not integrity_issues["malformed_files"]:
                logger.debug("health_check_data_integrity", status="healthy")
                return HealthStatus.HEALTHY, "No data integrity issues found"

            message = (
                f"⚠️ {len(integrity_issues['malformed_files'])} malformed file(s) detected: "
                "These files couldn't be parsed - manual review required"
            )
            logger.warning(
                "health_check_data_integrity",
                count=len(integrity_issues["malformed_files"]),
            )
            return HealthStatus.DEGRADED, message

        except Exception as e:
            logger.error("health_check_data_integrity_failed", error=str(e))
            return HealthStatus.UNHEALTHY, f"Error checking data integrity: {e}"
