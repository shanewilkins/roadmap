"""User and Team Operations Module - Handles user management and validation.

This module encapsulates user and team management responsibilities extracted from RoadmapCore,
including team member retrieval, user validation, and assignee management.

Responsibilities:
- Team member retrieval and caching
- Current user management
- Assignee validation and normalization
- Issue assignment queries by user
"""

from roadmap.core.domain import Issue
from roadmap.core.interfaces.assignee_validator import AssigneeValidator
from roadmap.core.services import GitHubIntegrationService, IssueService


class UserOperations:
    """Manager for user and team-related operations."""

    def __init__(
        self,
        github_service: GitHubIntegrationService,
        issue_service: IssueService,
        assignee_validator: AssigneeValidator | None = None,
    ):
        """Initialize user operations manager.

        Args:
            github_service: The GitHubIntegrationService instance
            issue_service: The IssueService instance
            assignee_validator: Validator for assignees (injected based on backend).
                               If None, uses vanilla validator for backwards compatibility.
        """
        self.github_service = github_service
        self.issue_service = issue_service

        # Use injected validator, or fall back to vanilla validator
        if assignee_validator is None:
            from roadmap.infrastructure.validation.vanilla_assignee_validator import (
                VanillaAssigneeValidator,
            )

            assignee_validator = VanillaAssigneeValidator()

        self.assignee_validator = assignee_validator

    def get_team_members(self) -> list[str]:
        """Get team members from GitHub repository.

        Returns:
            List of usernames if GitHub is configured, empty list otherwise
        """
        return self.github_service.get_team_members()

    def get_current_user(self) -> str | None:
        """Get the current user from config.

        Returns:
            Current user's name from config if set, None otherwise
        """
        return self.github_service.get_current_user()

    def get_assigned_issues(self, assignee: str) -> list[Issue]:
        """Get all issues assigned to a specific user.

        Args:
            assignee: The username to get issues for

        Returns:
            List of Issue objects assigned to the user
        """
        return self.issue_service.list_issues(assignee=assignee)

    def get_my_issues(self) -> list[Issue]:
        """Get all issues assigned to the current user.

        Returns:
            List of Issue objects assigned to current user, or empty list if not set
        """
        current_user = self.get_current_user()
        if not current_user:
            return []
        return self.get_assigned_issues(current_user)

    def get_all_assigned_issues(self) -> dict[str, list[Issue]]:
        """Get all issues grouped by assignee.

        Returns:
            Dictionary mapping assignee usernames to their assigned issues
        """
        all_issues = self.issue_service.list_issues()
        assigned_issues: dict[str, list[Issue]] = {}

        for issue in all_issues:
            if issue.assignee:
                if issue.assignee not in assigned_issues:
                    assigned_issues[issue.assignee] = []
                assigned_issues[issue.assignee].append(issue)

        return assigned_issues

    def get_cached_team_members(self) -> list[str]:
        """Get team members with caching (5 minute cache).

        Returns:
            List of cached team member usernames
        """
        return self.github_service.get_cached_team_members()

    def validate_assignee(self, assignee: str) -> tuple[bool, str]:
        """Validate an assignee using the configured validator.

        The validator is backend-specific:
        - GitHub backend: validates against repository collaborators
        - Git backend: accepts any assignee (no-op validator)

        Args:
            assignee: Username to validate

        Returns:
            Tuple of (is_valid, error_message)
            - (True, "") if valid
            - (False, error_message) if invalid
        """
        return self.assignee_validator.validate(assignee)

    def legacy_validate_assignee(self, assignee: str) -> tuple[bool, str]:
        """Legacy validation fallback for when validation strategy fails.

        Args:
            assignee: Username to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        return self.github_service._legacy_validate_assignee(assignee)

    def get_canonical_assignee(self, assignee: str) -> str:
        """Get the canonical form of an assignee name.

        This method should be called after validate_assignee to get the canonical form.

        Args:
            assignee: Input assignee name

        Returns:
            Canonical assignee name (may be same as input if no mapping exists)
        """
        return self.assignee_validator.get_canonical_assignee(assignee)
