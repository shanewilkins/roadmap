"""Team and assignee management orchestrator.

Handles team member queries, assignments, and validation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...application.services import GitHubIntegrationService, IssueService


class TeamOrchestrator:
    """Orchestrates team member and assignee operations."""

    def __init__(
        self,
        github_service: GitHubIntegrationService,
        issue_service: IssueService,
    ):
        """Initialize with required services.

        Args:
            github_service: GitHubIntegrationService instance
            issue_service: IssueService instance
        """
        self.github_service = github_service
        self.issue_service = issue_service

    def get_team_members(self) -> list[str]:
        """Get list of team members.

        Returns:
            List of team member usernames
        """
        return self.github_service.get_team_members()

    def get_current_user(self) -> str | None:
        """Get the current logged-in user.

        Returns:
            Current user identifier if available, None otherwise
        """
        return self.github_service.get_current_user()

    def validate_assignee(self, assignee: str) -> tuple[bool, str]:
        """Validate an assignee using the identity management system.

        Args:
            assignee: Username to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        return self.github_service.validate_assignee(assignee)

    def get_canonical_assignee(self, assignee: str) -> str:
        """Get the canonical form of an assignee name.

        Handles name normalization and aliasing.

        Args:
            assignee: Assignee identifier or alias

        Returns:
            Canonical assignee identifier
        """
        return self.github_service.get_canonical_assignee(assignee)

    def get_assigned_issues(self, assignee: str) -> list:
        """Get all issues assigned to a specific person.

        Args:
            assignee: Username

        Returns:
            List of issues assigned to this person
        """
        all_issues = self.issue_service.list_issues()
        return [issue for issue in all_issues if issue.assignee == assignee]

    def get_all_assigned_issues(self) -> dict[str, list]:
        """Get all issues grouped by assignee.

        Returns:
            Dictionary mapping assignee to list of their issues
        """
        all_issues = self.issue_service.list_issues()
        grouped = {}

        for issue in all_issues:
            if issue.assignee:
                if issue.assignee not in grouped:
                    grouped[issue.assignee] = []
                grouped[issue.assignee].append(issue)

        return grouped
