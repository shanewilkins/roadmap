"""Service for persisting issues to local storage (YAML files)."""

from typing import TYPE_CHECKING

from structlog import get_logger

from roadmap.core.domain.issue import Issue
from roadmap.core.models.sync_models import SyncIssue

if TYPE_CHECKING:
    from roadmap.infrastructure.core import RoadmapCore  # noqa: F401

logger = get_logger(__name__)


class IssuePersistenceService:
    """Handles persistence of issues to local storage (YAML files).

    Centralizes all operations for:
    - Updating the github_issue field on Issue objects
    - Managing remote_ids dictionaries
    - Saving issues to YAML repository

    This eliminates the duplication of save patterns in pull_issue() and push_issue().
    """

    @staticmethod
    def update_issue_with_remote_id(
        issue: Issue,
        backend_name: str,
        backend_id: int | str,
    ) -> None:
        """Update an issue's remote_ids dictionary with a new backend mapping.

        Args:
            issue: Issue to update
            backend_name: Backend name (e.g., "github")
            backend_id: ID from remote backend
        """
        if issue.remote_ids is None:
            issue.remote_ids = {}

        issue.remote_ids[backend_name] = str(backend_id)

        logger.debug(
            "updated_remote_ids",
            issue_id=issue.id,
            backend_name=backend_name,
            backend_id=backend_id,
        )

    @staticmethod
    def update_github_issue_number(issue: Issue, github_number: int) -> None:
        """Update the github_issue field on an Issue object.

        This field is used for quick GitHub lookups without querying remote_ids.

        Args:
            issue: Issue to update
            github_number: GitHub issue number to set
        """
        issue.github_issue = github_number

        logger.debug(
            "updated_github_issue_number",
            issue_id=issue.id,
            github_issue=github_number,
        )

    @staticmethod
    def save_issue(issue: Issue, core: "RoadmapCore") -> bool:
        """Save an issue to local YAML repository.

        Args:
            issue: Issue to save
            core: RoadmapCore for accessing repositories

        Returns:
            True if save succeeded, False otherwise
        """
        try:
            if not issue or not issue.id:
                logger.warning(
                    "cannot_save_invalid_issue",
                    issue_id=getattr(issue, "id", None),
                )
                return False

            repo = core.issue_service.repository
            if not repo:
                logger.error(
                    "issue_repository_not_available",
                    issue_id=issue.id,
                )
                return False

            repo.save(issue)

            logger.info(
                "issue_saved_to_yaml",
                issue_id=issue.id,
                title=issue.title,
            )
            return True

        except AttributeError as e:
            logger.error(
                "issue_persistence_attribute_error",
                issue_id=getattr(issue, "id", "unknown"),
                error=str(e),
                error_type="AttributeError",
            )
            return False
        except Exception as e:
            logger.error(
                "issue_persistence_save_failed",
                issue_id=getattr(issue, "id", "unknown"),
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True,
            )
            return False

    @staticmethod
    def apply_sync_issue_to_local(
        local_issue: Issue,
        sync_issue: SyncIssue,
    ) -> None:
        """Apply data from a SyncIssue to update a local Issue object.

        Used when pulling changes from remote backend to update local state.
        Preserves local ID while updating fields from remote.

        Args:
            local_issue: Local issue to update (ID preserved)
            sync_issue: Remote sync_issue with new data
        """
        # Update core fields from sync_issue
        local_issue.title = sync_issue.title or local_issue.title
        local_issue.assignee = sync_issue.assignee or local_issue.assignee
        local_issue.milestone = sync_issue.milestone or local_issue.milestone
        local_issue.labels = sync_issue.labels or local_issue.labels

        # Update timestamps
        if sync_issue.updated_at:
            local_issue.updated = sync_issue.updated_at

        # Update remote_ids from sync_issue (important for tracking)
        if sync_issue.remote_ids:
            if local_issue.remote_ids is None:
                local_issue.remote_ids = {}
            local_issue.remote_ids.update(sync_issue.remote_ids)

        # Merge metadata while preserving local metadata
        if sync_issue.metadata:
            if local_issue.github_sync_metadata is None:
                local_issue.github_sync_metadata = {}
            local_issue.github_sync_metadata.update(sync_issue.metadata)

        logger.debug(
            "applied_sync_issue_to_local",
            issue_id=local_issue.id,
            title=local_issue.title,
            from_backend=sync_issue.backend_name,
        )

    @staticmethod
    def get_issue_from_repo(
        issue_id: str,
        core: "RoadmapCore",
    ) -> Issue | None:
        """Retrieve an issue from the local repository.

        Args:
            issue_id: Issue ID to retrieve
            core: RoadmapCore for accessing repositories

        Returns:
            Issue if found, None otherwise
        """
        try:
            repo = core.issue_service.repository
            issue = repo.get(issue_id)

            if issue:
                logger.debug(
                    "retrieved_issue_from_repo",
                    issue_id=issue_id,
                    title=issue.get("title")
                    if isinstance(issue, dict)
                    else issue.title,
                )
            else:
                logger.debug("issue_not_found_in_repo", issue_id=issue_id)

            return issue

        except Exception as e:
            logger.error(
                "failed_to_retrieve_issue_from_repo",
                issue_id=issue_id,
                error=str(e),
            )
            return None

    @staticmethod
    def is_github_linked(issue: Issue) -> bool:
        """Check if an issue is already linked to GitHub.

        Args:
            issue: Issue to check

        Returns:
            True if issue has github_issue set or github in remote_ids
        """
        if hasattr(issue, "github_issue") and issue.github_issue:
            return True

        if issue.remote_ids and "github" in issue.remote_ids:
            return True

        return False

    @staticmethod
    def get_github_issue_number(issue: Issue) -> int | str | None:
        """Extract the GitHub issue number from an Issue.

        Checks both github_issue field and remote_ids dict.

        Args:
            issue: Issue to extract from

        Returns:
            GitHub issue number if found, None otherwise
        """
        # First check direct field (property)
        if issue.github_issue is not None:
            return issue.github_issue

        # Then check remote_ids
        if issue.remote_ids and "github" in issue.remote_ids:
            return issue.remote_ids["github"]

        return None
