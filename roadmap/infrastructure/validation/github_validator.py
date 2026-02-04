"""GitHub-specific assignee validation implementation.

Provides concrete GitHub-based validator implementation without coupling
core services directly to GitHub adapter.
"""

from roadmap.common.logging import get_logger
from roadmap.core.services.issue.assignee_validation_service import (
    AssigneeValidationResult,
)
from roadmap.infrastructure.validation_gateway import ValidationGateway

logger = get_logger(__name__)


class GitHubAssigneeValidator:
    """Validates assignees against GitHub repository access.

    This is the infrastructure implementation that can be injected
    into core validation services.
    """

    def __init__(
        self,
        token: str,
        owner: str,
        repo: str,
        cached_members: set[str] | list[str] | None = None,
    ):
        """Initialize with GitHub configuration.

        Args:
            token: GitHub API token
            owner: Repository owner
            repo: Repository name
            cached_members: Optional cached team members for performance
        """
        self.token = token
        self.owner = owner
        self.repo = repo
        self.cached_members = (
            set(cached_members)
            if isinstance(cached_members, list)
            else (cached_members or set())
        )

    def validate(self, assignee: str) -> AssigneeValidationResult:
        """Validate assignee against GitHub repository.

        Args:
            assignee: Username to validate

        Returns:
            AssigneeValidationResult with validation status
        """
        # Check cache first
        if self.cached_members and assignee in self.cached_members:
            return AssigneeValidationResult(is_valid=True, canonical_id=assignee)

        # Do full validation via API
        try:
            client = ValidationGateway.get_github_client(
                token=self.token, org=self.owner
            )
            github_valid, github_error = client.validate_assignee(assignee)  # type: ignore[attr-defined]

            if github_valid:
                return AssigneeValidationResult(is_valid=True, canonical_id=assignee)
            else:
                return AssigneeValidationResult(is_valid=False, message=github_error)

        except Exception as e:
            error_msg = f"GitHub validation failed: {e}"
            logger.warning(
                "github_validation_error",
                assignee=assignee,
                error=str(e),
                severity="infrastructure",
            )
            return AssigneeValidationResult(is_valid=False, message=error_msg)

    def get_team_members(self) -> list[str]:
        """Get list of valid team members from GitHub.

        Returns:
            List of GitHub repository team members
        """
        try:
            client = ValidationGateway.get_github_client(
                token=self.token, org=self.owner
            )
            members = client.get_team_members()  # type: ignore[attr-defined]
            logger.debug("github_team_members_retrieved", count=len(members))
            return members
        except Exception as e:
            logger.warning(
                "github_team_members_retrieval_failed",
                error=str(e),
                severity="infrastructure",
            )
            return []
