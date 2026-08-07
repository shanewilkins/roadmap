"""GitHub conflict detection service."""

from datetime import datetime
from typing import Any

from roadmap.common.datetime_parser import UnifiedDateTimeParser
from roadmap.core.domain.issue import Issue
from roadmap.core.services.github.github_integration_service import (
    GitHubIntegrationService,
)
from roadmap.core.services.github.github_issue_client import GitHubIssueClient


class GitHubConflictDetector:
    """Detects conflicts between local and GitHub issues."""

    def __init__(self, integration_service: GitHubIntegrationService):
        """Initialize conflict detector.

        Args:
            integration_service: GitHub integration service instance
        """
        self.service = integration_service
        token, owner, repo = integration_service.get_github_config()
        self.owner = owner
        self.repo = repo
        self.client = GitHubIssueClient(token)

    def detect_conflicts(
        self, local_issue: Issue, github_number: int
    ) -> dict[str, Any]:
        """Detect conflicts between local and GitHub versions.

        Args:
            local_issue: Local issue entity
            github_number: GitHub issue number

        Returns:
            Dict with conflict information:
            {
                'has_conflicts': bool,
                'local_modified': bool,
                'github_modified': bool,
                'last_sync': datetime | None,
                'warnings': List[str]
            }
        """
        conflicts = {
            "has_conflicts": False,
            "local_modified": False,
            "github_modified": False,
            "last_sync": None,
            "warnings": [],
        }

        # Get last sync time from issue metadata if available
        last_sync = self._get_last_sync_time(local_issue)
        conflicts["last_sync"] = last_sync

        # If no last sync recorded, can't detect conflicts
        if not last_sync:
            conflicts["warnings"].append(
                "No sync history available. First sync will update all fields."
            )
            return conflicts

        # Check if we have required GitHub config
        if not self.owner or not self.repo:
            conflicts["warnings"].append(
                "GitHub configuration missing. Cannot check for GitHub changes."
            )
            return conflicts

        # Check if GitHub issue was modified after last sync
        try:
            github_issue = self.client.fetch_issue(self.owner, self.repo, github_number)
            github_updated_at = self._parse_github_timestamp(
                github_issue.get("updated_at")
            )

            if github_updated_at and github_updated_at > last_sync:
                conflicts["github_modified"] = True
                conflicts["warnings"].append(
                    "GitHub issue was modified after last sync"
                )
        except Exception as e:
            conflicts["warnings"].append(
                f"Could not check GitHub for changes: {str(e)}"
            )

        # Check if local issue was modified after last sync
        if self._is_local_modified_after_sync(local_issue, last_sync):
            conflicts["local_modified"] = True
            conflicts["warnings"].append("Local issue was modified after last sync")

        # Set has_conflicts flag if both were modified
        if conflicts["local_modified"] and conflicts["github_modified"]:
            conflicts["has_conflicts"] = True
            conflicts["warnings"].append(
                "⚠️  Both local and GitHub versions have changes. Review carefully before syncing."
            )

        return conflicts

    def _get_last_sync_time(self, issue: Issue) -> datetime | None:
        """Get last sync timestamp from issue.

        Args:
            issue: Issue entity

        Returns:
            Last sync datetime or None
        """
        # Check if issue has sync metadata with sync timestamp
        if (
            issue.github_sync_metadata
            and "sync_timestamp" in issue.github_sync_metadata
        ):
            return issue.github_sync_metadata["sync_timestamp"]

        # Check issue updated_at as fallback
        if issue.updated:
            return issue.updated

        return None

    def _is_local_modified_after_sync(self, issue: Issue, last_sync: datetime) -> bool:
        """Check if local issue was modified after sync time.

        Args:
            issue: Issue entity
            last_sync: Last sync timestamp

        Returns:
            True if modified after sync
        """
        if not issue.updated:
            return False

        updated_at = issue.updated
        return updated_at > last_sync

    def _parse_github_timestamp(self, timestamp: str | None) -> datetime | None:
        """Parse GitHub API timestamp.

        Args:
            timestamp: GitHub timestamp string

        Returns:
            Parsed datetime or None
        """
        if not timestamp:
            return None

        try:
            return UnifiedDateTimeParser.parse_github_timestamp(timestamp)
        except (ValueError, AttributeError):
            return None

    def get_conflict_summary(self, conflicts: dict[str, Any]) -> str:
        """Get human-readable conflict summary.

        Args:
            conflicts: Conflicts dict from detect_conflicts()

        Returns:
            Summary string
        """
        if not conflicts["warnings"]:
            return "No conflicts detected. Safe to sync."

        summary = "Conflict Detection Summary:\n"
        for warning in conflicts["warnings"]:
            summary += f"  • {warning}\n"

        if conflicts["has_conflicts"]:
            summary += "\nRecommendation: Review changes manually before syncing."

        return summary
