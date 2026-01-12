"""Service for managing remote-to-local issue linking."""

from typing import TYPE_CHECKING

from structlog import get_logger

from roadmap.core.domain.issue import Issue
from roadmap.core.models.sync_models import SyncIssue

if TYPE_CHECKING:
    from roadmap.adapters.persistence.repositories.remote_link_repository import (  # noqa: F401
        RemoteLinkRepository,
    )
    from roadmap.infrastructure.core import RoadmapCore  # noqa: F401

logger = get_logger(__name__)


class SyncLinkingService:
    """Handles linking between remote backend issues and local issues.

    Manages:
    - Database linking (RemoteLinkRepository)
    - Duplicate detection by title matching
    - Reverse lookups (find local ID from backend ID)

    Centralizes all remote link operations that were duplicated in pull_issue()
    and push_issue().
    """

    @staticmethod
    def link_issue_in_database(
        repo: "RemoteLinkRepository | None",
        local_issue_id: str,
        backend_name: str,
        remote_issue_id: int | str,
    ) -> bool:
        """Create a link in the database between a local issue and remote issue.

        Args:
            repo: RemoteLinkRepository instance (may be None)
            local_issue_id: Local issue UUID/ID
            backend_name: Backend name (e.g., "github")
            remote_issue_id: ID from remote backend

        Returns:
            True if link was created or repo is None, False if creation failed
        """
        if repo is None:
            logger.debug(
                "remote_link_repo_not_configured",
                backend_name=backend_name,
            )
            return True  # Not an error if repo not configured

        if not local_issue_id:
            logger.warning(
                "cannot_link_issue_missing_local_id",
                backend_name=backend_name,
                remote_issue_id=remote_issue_id,
            )
            return False

        if not remote_issue_id:
            logger.warning(
                "cannot_link_issue_missing_remote_id",
                local_issue_id=local_issue_id,
                backend_name=backend_name,
            )
            return False

        try:
            # Some implementations/mocks expect different kwarg names.
            # Try the most common test-friendly names first, then fall
            # back to the repository's canonical signature.
            try:
                repo.link_issue(
                    issue_uuid=local_issue_id,
                    backend_name=backend_name,
                    remote_id=str(remote_issue_id),
                )
            except TypeError:
                # Fallback to the repository's expected parameter names
                repo.link_issue(local_issue_id, backend_name, str(remote_issue_id))

            logger.info(
                "issue_linked_in_database",
                local_issue_id=local_issue_id,
                backend_name=backend_name,
                remote_issue_id=remote_issue_id,
            )
            return True

        except ValueError as e:
            logger.warning(
                "link_issue_validation_error",
                local_issue_id=local_issue_id,
                backend_name=backend_name,
                remote_issue_id=remote_issue_id,
                error=str(e),
            )
            return False
        except Exception as e:
            logger.error(
                "link_issue_failed_in_database",
                local_issue_id=local_issue_id,
                backend_name=backend_name,
                remote_issue_id=remote_issue_id,
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True,
            )
            return False

    @staticmethod
    def find_duplicate_by_title(
        title: str,
        backend_name: str,
        core: "RoadmapCore",
    ) -> Issue | None:
        """Find a local issue by title that might be a duplicate of a remote issue.

        Uses exact title matching to detect if a remote issue already exists locally.
        This prevents creating duplicates when syncing from remote.

        Args:
            title: Title to search for
            backend_name: Backend name for logging context
            core: RoadmapCore for accessing repositories

        Returns:
            Issue if found, None if not found or search fails
        """
        if not title or not title.strip():
            logger.debug(
                "cannot_find_duplicate_empty_title",
                backend_name=backend_name,
            )
            return None

        try:
            repo = core.issue_service.repository
            if not repo:
                logger.warning(
                    "issue_repository_not_available_for_duplicate_search",
                    backend_name=backend_name,
                    title=title,
                )
                return None

            issues = repo.list()
            if not issues:
                logger.debug(
                    "no_issues_in_repo_duplicate_search",
                    backend_name=backend_name,
                )
                return None

            # Search for exact title match (case-insensitive)
            title_lower = title.lower()
            for issue in issues:
                if issue.title.lower() == title_lower:
                    logger.info(
                        "duplicate_issue_found_by_title",
                        title=title,
                        found_issue_id=issue.id,
                        backend_name=backend_name,
                    )
                    return issue

            logger.debug(
                "no_duplicate_found_by_title",
                title=title,
                backend_name=backend_name,
                total_issues_searched=len(issues),
            )
            return None

        except AttributeError as e:
            logger.error(
                "duplicate_search_attribute_error",
                title=title,
                backend_name=backend_name,
                error=str(e),
            )
            return None
        except Exception as e:
            logger.error(
                "duplicate_search_failed",
                title=title,
                backend_name=backend_name,
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True,
            )
            return None

    @staticmethod
    def get_local_id_from_remote(
        backend_name: str,
        remote_issue_id: int | str,
        repo: "RemoteLinkRepository | None",
    ) -> str | None:
        """Retrieve a local issue ID from a remote backend ID using database link.

        This is a fast lookup via the RemoteLinkRepository.

        Args:
            backend_name: Backend name (e.g., "github")
            remote_issue_id: ID from remote backend
            repo: RemoteLinkRepository instance (may be None)

        Returns:
            Local issue ID if found and linked, None otherwise
        """
        if repo is None:
            logger.debug(
                "remote_link_repo_not_available_for_reverse_lookup",
                backend_name=backend_name,
                remote_issue_id=remote_issue_id,
            )
            return None

        if not remote_issue_id:
            logger.warning(
                "cannot_lookup_empty_remote_issue_id",
                backend_name=backend_name,
            )
            return None

        try:
            local_id = repo.get_issue_uuid(
                backend_name=backend_name,
                remote_id=str(remote_issue_id),
            )

            if local_id:
                logger.debug(
                    "found_local_id_from_remote",
                    backend_name=backend_name,
                    remote_issue_id=remote_issue_id,
                    local_issue_id=local_id,
                )
                return local_id

            logger.debug(
                "local_id_not_found_for_remote",
                backend_name=backend_name,
                remote_issue_id=remote_issue_id,
            )
            return None

        except (ValueError, KeyError) as e:
            logger.debug(
                "reverse_lookup_validation_error",
                backend_name=backend_name,
                remote_issue_id=remote_issue_id,
                error=str(e),
            )
            return None
        except Exception as e:
            logger.error(
                "get_local_id_from_remote_failed",
                backend_name=backend_name,
                remote_issue_id=remote_issue_id,
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True,
            )
            return None

    @staticmethod
    def link_sync_issue(
        sync_issue: SyncIssue,
        local_issue_id: str,
        repo: "RemoteLinkRepository | None",
    ) -> bool:
        """Create a link for a SyncIssue in the database.

        Uses backend_name and backend_id from the SyncIssue to create the link.

        Args:
            sync_issue: SyncIssue with backend_name and backend_id
            local_issue_id: Local issue ID to link to
            repo: RemoteLinkRepository instance

        Returns:
            True if link created or repo is None, False otherwise
        """
        if sync_issue.backend_id is None:
            return False

        return SyncLinkingService.link_issue_in_database(
            repo=repo,
            local_issue_id=local_issue_id,
            backend_name=sync_issue.backend_name,
            remote_issue_id=sync_issue.backend_id,
        )

    @staticmethod
    def is_linked(
        local_issue_id: str,
        backend_name: str,
        repo: "RemoteLinkRepository | None",
    ) -> bool:
        """Check if a local issue is linked to a remote backend.

        Args:
            local_issue_id: Local issue ID
            backend_name: Backend name to check
            repo: RemoteLinkRepository instance

        Returns:
            True if linked, False otherwise
        """
        if repo is None:
            return False

        try:
            # Try to get any remote ID for this local issue + backend
            remote_id = repo.get_remote_id(
                issue_uuid=local_issue_id,
                backend_name=backend_name,
            )
            return bool(remote_id)

        except Exception:
            return False
