"""Detects changes for GitHub linked entities."""

from datetime import datetime
from typing import Any

from roadmap.core.domain import Issue
from roadmap.core.services.github_issue_client import GitHubIssueClient
from roadmap.core.services.sync_report import IssueChange


class GitHubChangeDetector:
    """Detects what has changed for GitHub-linked entities."""

    def __init__(self, github_client: GitHubIssueClient):
        """Initialize detector with GitHub client.

        Args:
            github_client: Client for fetching GitHub issues
        """
        self.github_client = github_client

    def detect_issue_changes(
        self,
        local_issue: Issue,
        owner: str,
        repo: str,
        last_sync_time: datetime | None = None,
    ) -> IssueChange:
        """Detect changes for a single linked issue.

        Args:
            local_issue: Local issue to check
            owner: GitHub repository owner
            repo: GitHub repository name
            last_sync_time: When the issue was last synced

        Returns:
            IssueChange with detected changes
        """
        change = IssueChange(
            issue_id=local_issue.id,
            title=local_issue.title,
            last_sync_time=last_sync_time,
        )

        try:
            if not owner or not repo:
                change.github_changes = {
                    "error": "GitHub config incomplete (owner/repo required)"
                }
                return change

            if not local_issue.github_issue:
                change.github_changes = {"error": "Issue not linked to GitHub"}
                return change

            # Fetch GitHub issue
            github_issue_number = self._parse_github_issue_number(
                local_issue.github_issue
            )
            github_issue = self.github_client.fetch_issue(
                owner, repo, github_issue_number
            )

            if not github_issue:
                change.github_changes = {"issue": "deleted on GitHub"}
                return change

            # Detect local and GitHub changes
            change.local_changes = self._detect_local_changes(local_issue)
            change.github_changes = self._detect_github_changes(
                local_issue, github_issue
            )

            # Determine conflict status
            if change.local_changes and change.github_changes:
                change.has_conflict = True

        except Exception as e:
            change.github_changes = {"error": str(e)}

        return change

    def detect_milestone_changes(self, local_milestone: Any) -> IssueChange | None:
        """Detect changes for a milestone.

        Args:
            local_milestone: Local milestone to check

        Returns:
            IssueChange with detected changes, or None if no changes
        """
        # Placeholder: Milestone detection logic to be extracted
        # from _detect_milestone_changes
        return None

    @staticmethod
    def _parse_github_issue_number(github_issue: Any) -> int:
        """Parse GitHub issue number from string or int.

        Args:
            github_issue: GitHub issue number (string or int)

        Returns:
            GitHub issue number as integer

        Raises:
            ValueError: If cannot parse issue number
        """
        if isinstance(github_issue, str):
            return int(github_issue)
        return github_issue

    @staticmethod
    def _detect_local_changes(issue: Issue) -> dict[str, Any]:
        """Detect changes made locally to the issue.

        Args:
            issue: Issue to check

        Returns:
            Dict of detected local changes
        """
        changes = {}

        # Check for local modifications
        # (Placeholder - extract from _detect_local_changes)
        # Note: Issue model doesn't track dirty state, so no local changes detected here
        # This is a placeholder for future enhancement when tracking changes

        return changes

    @staticmethod
    def _detect_github_changes(
        local_issue: Issue, github_issue: dict[str, Any]
    ) -> dict[str, Any]:
        """Detect changes made on GitHub.

        Args:
            local_issue: Local issue version
            github_issue: GitHub issue version

        Returns:
            Dict of detected GitHub changes
        """
        changes = {}

        # Compare title
        if github_issue.get("title") != local_issue.title:
            changes["title"] = github_issue.get("title")

        # Compare content
        gh_body = github_issue.get("body", "")
        if gh_body != (local_issue.content or ""):
            changes["content"] = gh_body

        # Compare status
        gh_status = "closed" if github_issue.get("state") == "closed" else "open"
        if gh_status != local_issue.status:
            changes["status"] = gh_status

        return changes
