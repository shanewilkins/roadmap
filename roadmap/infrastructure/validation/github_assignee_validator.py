"""GitHub-specific assignee validator implementation.

Validates assignees against GitHub repository collaborators and
provides canonical name resolution.
"""

from roadmap.common.logging import get_logger

logger = get_logger(__name__)


class GitHubAssigneeValidator:
    """Validates assignees against GitHub repository configuration.

    Delegates to GitHubIntegrationService for the actual validation logic,
    while implementing the AssigneeValidator protocol.
    """

    def __init__(self, github_service):
        """Initialize with a GitHub integration service.

        Args:
            github_service: GitHubIntegrationService instance for validation
        """
        self.github_service = github_service

    def validate(self, assignee: str) -> tuple[bool, str]:
        """Validate assignee against GitHub.

        Args:
            assignee: Username to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        return self.github_service.validate_assignee(assignee)

    def get_canonical_assignee(self, assignee: str) -> str:
        """Get the canonical form of an assignee name from GitHub.

        Args:
            assignee: Input assignee name

        Returns:
            Canonical assignee name
        """
        return self.github_service.get_canonical_assignee(assignee)
