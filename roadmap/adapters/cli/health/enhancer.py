"""Health check result enhancement with details and recommendations.

This module provides infrastructure for enriching health check results with:
- Affected entities (which issues, milestones, etc. are affected)
- Fix recommendations (what can be done to resolve issues)
- Auto-fix commands (ready-to-run commands for common fixes)
"""

from dataclasses import dataclass, field
from typing import Any

from roadmap.core.domain.health import HealthStatus


@dataclass
class HealthCheckDetail:
    """Details about a specific health check result.

    Attributes:
        check_name: Name of the health check (e.g., "duplicate_issues")
        status: Health status (HEALTHY, DEGRADED, UNHEALTHY)
        message: Summary message about the check result
        affected_items: List of affected entity IDs or names
        recommendations: List of recommended fixes or actions
        fix_commands: List of ready-to-run CLI commands that can fix the issue
    """

    check_name: str
    status: HealthStatus
    message: str
    affected_items: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    fix_commands: list[dict[str, str]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "check_name": self.check_name,
            "status": self.status.value.upper(),
            "message": self.message,
            "affected_items": self.affected_items,
            "affected_count": len(self.affected_items),
            "recommendations": self.recommendations,
            "fix_commands": self.fix_commands,
        }


class HealthCheckEnhancer:
    """Enhances health check results with detailed information.

    This service enriches basic health check results (status + message) with:
    - Lists of affected entities
    - Specific recommendations for fixes
    - Ready-to-run CLI commands to fix issues

    Works with both infrastructure and data quality checks.
    """

    def __init__(self, core=None):
        """Initialize enhancer with optional core for entity lookups.

        Args:
            core: Optional core instance for accessing entities
        """
        self.core = core

    def enhance_check_result(
        self,
        check_name: str,
        status: HealthStatus,
        message: str,
    ) -> HealthCheckDetail:
        """Enhance a health check result with details.

        Args:
            check_name: Name of the health check
            status: Health status from the check
            message: Message from the check

        Returns:
            HealthCheckDetail with enhanced information
        """
        detail = HealthCheckDetail(
            check_name=check_name,
            status=status,
            message=message,
        )

        # Route to check-specific enhancement
        if check_name == "duplicate_issues":
            self._enhance_duplicate_issues(detail)
        elif check_name == "orphaned_issues":
            self._enhance_orphaned_issues(detail)
        elif check_name == "old_backups":
            self._enhance_old_backups(detail)
        elif check_name == "folder_structure":
            self._enhance_folder_structure(detail)
        elif check_name == "comment_integrity":
            self._enhance_comment_integrity(detail)
        else:
            # Generic enhancement for other checks
            self._enhance_generic(detail)

        return detail

    def _enhance_duplicate_issues(self, detail: HealthCheckDetail) -> None:
        """Add details for duplicate_issues check."""
        detail.recommendations = [
            "Review issues with identical titles and status",
            "Merge duplicates, keeping the older issue as primary",
            "Close/delete the newer duplicate issue",
        ]
        detail.fix_commands = [
            {
                "command": "roadmap health fix --fix-type duplicate_issues --dry-run",
                "description": "Preview duplicate issues that can be fixed",
            },
            {
                "command": "roadmap health fix --fix-type duplicate_issues",
                "description": "Automatically fix duplicate issues (requires review)",
            },
        ]

    def _enhance_orphaned_issues(self, detail: HealthCheckDetail) -> None:
        """Add details for orphaned_issues check."""
        detail.recommendations = [
            "Assign issues without milestones to 'Backlog'",
            "Review issues to ensure correct milestone assignment",
            "Use 'roadmap issue assign' to move to correct milestone",
        ]
        detail.fix_commands = [
            {
                "command": "roadmap health fix --fix-type orphaned_issues --dry-run",
                "description": "Preview issues to be assigned to Backlog",
            },
            {
                "command": "roadmap health fix --fix-type orphaned_issues",
                "description": "Automatically assign orphaned issues to Backlog",
            },
        ]

    def _enhance_old_backups(self, detail: HealthCheckDetail) -> None:
        """Add details for old_backups check."""
        detail.recommendations = [
            "Delete backup files older than 90 days to save storage",
            "Review archived backups to ensure data is safely stored",
            "Consider moving very old backups to external storage",
        ]
        detail.fix_commands = [
            {
                "command": "roadmap health fix --fix-type old_backups --dry-run",
                "description": "Preview old backups that can be deleted",
            },
            {
                "command": "roadmap health fix --fix-type old_backups",
                "description": "Delete old backup files (>90 days)",
            },
        ]

    def _enhance_folder_structure(self, detail: HealthCheckDetail) -> None:
        """Add details for folder_structure check."""
        detail.recommendations = [
            "Move issues to their correct milestone folders",
            "Verify milestone folder organization matches issue assignments",
            "Use 'roadmap issue move' to reorganize structure",
        ]
        detail.fix_commands = [
            {
                "command": "roadmap health fix --fix-type folder_structure --dry-run",
                "description": "Preview folder structure corrections",
            },
            {
                "command": "roadmap health fix --fix-type folder_structure",
                "description": "Automatically fix folder structure issues",
            },
        ]

    def _enhance_comment_integrity(self, detail: HealthCheckDetail) -> None:
        """Add details for comment_integrity check."""
        detail.recommendations = [
            "Review and sanitize malformed JSON in comments",
            "Check for corrupted comment threads",
            "Manually edit comments with formatting issues",
        ]
        detail.fix_commands = [
            {
                "command": "roadmap health fix --fix-type corrupted_comments --dry-run",
                "description": "Preview comments that can be sanitized",
            },
            {
                "command": "roadmap health fix --fix-type corrupted_comments",
                "description": "Automatically sanitize malformed comments (review first)",
            },
        ]

    def _enhance_generic(self, detail: HealthCheckDetail) -> None:
        """Generic enhancement for checks without specific handlers."""
        if detail.status == HealthStatus.HEALTHY:
            detail.recommendations = ["No action needed"]
        elif detail.status == HealthStatus.DEGRADED:
            detail.recommendations = [
                "Monitor this check in future health reports",
                "Take action when status becomes UNHEALTHY",
            ]
        else:  # UNHEALTHY
            detail.recommendations = [
                "Investigate the root cause immediately",
                "Review the detailed message for specific guidance",
                "Use 'roadmap health scan' for entity-level diagnostics",
            ]

    def enhance_all_checks(
        self, checks: dict[str, tuple[HealthStatus, str]]
    ) -> dict[str, HealthCheckDetail]:
        """Enhance all health check results.

        Args:
            checks: Dict mapping check names to (status, message) tuples

        Returns:
            Dict mapping check names to HealthCheckDetail objects
        """
        return {
            check_name: self.enhance_check_result(check_name, status, message)
            for check_name, (status, message) in checks.items()
        }
