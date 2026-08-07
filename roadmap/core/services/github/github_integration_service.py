"""GitHub integration service for roadmap application.

This module handles GitHub-related operations including authentication,
team member queries, assignee validation, and GitHub configuration management.
"""

import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING

from roadmap.common.configuration import ConfigManager
from roadmap.common.errors import (
    ErrorHandler,
    ErrorSeverity,
    ValidationError,
)
from roadmap.common.errors.error_standards import OperationType, safe_operation
from roadmap.common.logging import get_logger
from roadmap.common.logging.error_logging import (
    log_error_with_context,
    log_external_service_error,
    log_validation_error,
)
from roadmap.common.observability.instrumentation import traced
from roadmap.infrastructure.security.credentials import get_credential_manager

if TYPE_CHECKING:
    from roadmap.core.interfaces import GitHubBackendInterface  # noqa: F401

logger = get_logger(__name__)


class GitHubIntegrationService:
    """Manages GitHub integration and team member operations."""

    def __init__(
        self,
        root_path: Path,
        config_file: Path,
        github_backend: "GitHubBackendInterface | None" = None,
    ):
        """Initialize GitHub integration service.

        Args:
            root_path: Root project path
            config_file: Path to config.yaml file
            github_backend: Optional GitHub backend interface. If not provided,
                           will create GitHubBackendAdapter instance when needed.
        """
        self.root_path = root_path
        self.config_file = config_file
        self._github_backend = github_backend
        self._team_members_cache: list[str] | None = None
        self._cache_timestamp: datetime | None = None
        self._last_canonical_assignee: str | None = None

    def _get_github_backend(self) -> "GitHubBackendInterface":
        """Lazy-load GitHub backend interface.

        Returns:
            GitHubBackendInterface implementation
        """
        if self._github_backend is None:
            raise RuntimeError(
                "GitHub backend not configured. Ensure RoadmapCore is initialized with backend."
            )
        return self._github_backend

    def _get_credentials(self) -> tuple[str | None, str | None, str | None]:
        """Get GitHub credentials from config and environment.

        Returns:
            Tuple of (token, owner, repo) or (None, None, None) if not configured
        """
        try:
            config_manager = ConfigManager(self.config_file)
            config = config_manager.load()
            github_config = getattr(config, "github", None)

            # Get owner and repo from config
            if github_config is None:
                owner = None
                repo = None
            elif isinstance(github_config, dict):
                owner = github_config.get("owner")
                repo = github_config.get("repo")
            else:
                # github_config is a GitHubConfig object
                owner = getattr(github_config, "owner", None)
                repo = getattr(github_config, "repo", None)

            if not isinstance(owner, str) or not owner:
                owner = None
            if not isinstance(repo, str) or not repo:
                repo = None

            # Get token from credentials manager or environment
            credential_manager = get_credential_manager()
            token = credential_manager.get_token()

            if not token:
                token = os.getenv("GITHUB_TOKEN")

            return token, owner, repo
        except Exception as e:
            logger.debug("credentials_retrieval_failed", error=str(e))
            return None, None, None

    @traced("get_github_config")
    @safe_operation(OperationType.READ, "GitHubAPI", retryable=True)
    def get_github_config(self) -> tuple[str | None, str | None, str | None]:
        """Get GitHub configuration from config file and credentials.

        Returns:
            Tuple of (token, owner, repo) or (None, None, None) if not configured
        """
        logger.info("getting_github_config")
        try:
            token, owner, repo = self._get_credentials()

            if not owner or not repo:
                log_validation_error(
                    ValueError("Missing GitHub owner or repo in config"),
                    entity_type="GitHubConfig",
                    field_name="owner_or_repo",
                    proposed_value={"owner": owner, "repo": repo},
                )
                return None, None, None

            return token, owner, repo

        except Exception as e:
            log_error_with_context(
                e,
                operation="get_github_config",
                entity_type="GitHubAPI",
                include_traceback=False,
            )
            logger.debug("github_config_retrieval_failed", error=str(e))
            return None, None, None

    @safe_operation(OperationType.READ, "GitHubAPI", retryable=True)
    @traced("get_team_members")
    def get_team_members(self) -> list[str]:
        """Get team members from GitHub repository.

        Returns:
            List of usernames if GitHub is configured, empty list otherwise
        """
        logger.info("getting_team_members_from_github")
        try:
            token, owner, repo = self.get_github_config()
            if not token or not owner or not repo:
                logger.debug("github_not_configured")
                return []

            # Get team members via backend interface
            try:
                backend = self._get_github_backend()
                members = (
                    backend.list_repositories()
                    if hasattr(backend, "list_repositories")
                    else []
                )
                logger.debug("team_members_retrieved", count=len(members))
                return members if isinstance(members, list) else []
            except Exception as api_error:
                log_external_service_error(
                    api_error,
                    service_name="GitHub",
                    operation="get_team_members",
                )
                return []
        except Exception as e:
            log_error_with_context(
                e,
                operation="get_team_members",
                entity_type="GitHubAPI",
            )
            logger.debug("team_members_retrieval_failed", error=str(e))
            # Return empty list if GitHub is not configured or accessible
            return []

    @safe_operation(OperationType.READ, "GitHubUser", retryable=True)
    @traced("get_current_user")
    def get_current_user(self, config_file: Path | None = None) -> str | None:
        """Get the current user from config.

        Args:
            config_file: Optional override path to config file

        Returns:
            Current user's name from config if set, None otherwise
        """
        logger.info("getting_current_user")
        try:
            config_path = config_file or self.config_file
            config_manager = ConfigManager(config_path)
            config = config_manager.load()
            if config and hasattr(config, "user"):
                user = getattr(config, "user", None)
                if user and hasattr(user, "name"):
                    name = user.name
                    logger.debug("current_user_retrieved", user=name)
                    return name
        except Exception as e:
            logger.debug("current_user_retrieval_failed", error=str(e))

        return None

    @safe_operation(OperationType.READ, "GitHubAPI", retryable=True)
    def get_cached_team_members(self) -> list[str]:
        """Get team members with caching (5 minute cache).

        Returns:
            List of cached team member usernames
        """
        logger.info("getting_cached_team_members")
        # Check if cache is valid (5 minutes)
        if (
            self._team_members_cache is not None
            and self._cache_timestamp is not None
            and datetime.now(UTC) - self._cache_timestamp < timedelta(minutes=5)
        ):
            logger.debug("using_cached_team_members")
            return self._team_members_cache

        # Refresh cache
        team_members = self.get_team_members()
        self._team_members_cache = team_members
        self._cache_timestamp = datetime.now(UTC)
        logger.debug("team_members_cache_refreshed", count=len(team_members))

        return team_members

    @safe_operation(OperationType.READ, "Assignee", retryable=True)
    @traced("validate_assignee")
    def validate_assignee(self, assignee: str) -> tuple[bool, str]:
        """Validate an assignee using the identity management system.

        This validation integrates with the identity management system while
        maintaining backward compatibility with the original API.

        Only validates against GitHub if the sync backend is configured to use
        GitHub. If using vanilla Git backend, validation is skipped.

        Args:
            assignee: Username to validate

        Returns:
            Tuple of (is_valid, error_message)
            - (True, "") if valid (backward compatible)
            - (False, error_message) if invalid
        """
        logger.info("validating_assignee", assignee=assignee)

        # Check which sync backend is configured
        try:
            config_manager = ConfigManager(self.config_file)
            config = config_manager.load()
            github_config_obj = getattr(config, "github", None)

            # Determine sync backend
            if github_config_obj is None:
                sync_backend = "git"
            elif isinstance(github_config_obj, dict):
                sync_backend = github_config_obj.get("sync_backend", "github")
            else:
                sync_backend = getattr(github_config_obj, "sync_backend", "github")

            # Only validate against GitHub if using GitHub backend
            if sync_backend != "github":
                logger.info(
                    "skipping_assignee_validation",
                    reason=f"sync_backend is {sync_backend}, not github",
                    assignee=assignee,
                )
                return True, ""
        except Exception as e:
            logger.debug(
                "sync_backend_detection_failed_continuing_validation",
                error=str(e),
            )
            # If we can't determine backend, continue with validation

        try:
            from roadmap.core.services.issue.assignee_validation_service import (
                AssigneeValidationStrategy,
            )

            # Get GitHub config if available
            github_config = None
            try:
                token, owner, repo = self.get_github_config()
                if token and owner and repo:
                    github_config = (token, owner, repo)
            except Exception as e:
                logger.debug("github_config_for_validation_failed", error=str(e))

            # Get cached team members
            cached_members = None
            try:
                cached_members = self.get_cached_team_members()
            except Exception as e:
                logger.debug("cached_members_for_validation_failed", error=str(e))

            # Use validation strategy
            strategy = AssigneeValidationStrategy(
                self.root_path, github_config, cached_members
            )
            is_valid, error_message, canonical_id = strategy.validate(assignee)

            if is_valid:
                self._last_canonical_assignee = canonical_id
                logger.debug("assignee_validated", assignee=assignee)
                return True, ""
            else:
                logger.warning(
                    "assignee_validation_failed",
                    assignee=assignee,
                    severity="data_error",
                )
                return False, error_message

        except Exception as e:
            # Fall back to legacy validation if strategy fails
            logger.debug("strategy_validation_failed_using_legacy", error=str(e))
            return self._legacy_validate_assignee(assignee)

    def _legacy_validate_assignee(self, assignee: str) -> tuple[bool, str]:
        """Legacy validation fallback for when validation strategy fails.

        Args:
            assignee: Username to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not assignee or not assignee.strip():
            return False, "Assignee cannot be empty"

        assignee = assignee.strip()

        try:
            token, owner, repo = self.get_github_config()
            if not token or not owner or not repo:
                # If GitHub is not configured, allow any assignee without validation
                # This supports local-only roadmap usage without GitHub integration
                self._last_canonical_assignee = assignee
                logger.debug(
                    "github_not_configured_allowing_assignee", assignee=assignee
                )
                return True, ""

            # GitHub is configured - perform validation against repository access

            # First check against cached team members for performance
            team_members = self.get_cached_team_members()
            if team_members and assignee in team_members:
                self._last_canonical_assignee = assignee
                logger.debug("assignee_in_cached_members", assignee=assignee)
                return True, ""

            # If not in cache or cache is empty, do full validation via API
            from roadmap.infrastructure.github_gateway import GitHubGateway

            client = GitHubGateway.get_github_client(
                {"token": token, "owner": owner, "repo": repo}
            )

            # This will do the full GitHub API validation
            github_valid, github_error = client.validate_assignee(assignee)  # type: ignore[attr-defined]
            if github_valid:
                self._last_canonical_assignee = assignee
                logger.debug("assignee_validated_via_github", assignee=assignee)
                return True, ""
            else:
                logger.warning(
                    "assignee_not_in_github", assignee=assignee, severity="data_error"
                )
                return False, github_error

        except Exception as fallback_error:
            # If validation fails due to network/API issues, allow the assignment
            # but log a warning that validation couldn't be performed
            error_handler = ErrorHandler()
            error_handler.handle_error(
                ValidationError(
                    f"Could not validate assignee '{assignee}' - validation unavailable",
                    field="assignee",
                    value=assignee,
                    severity=ErrorSeverity.WARNING,
                    cause=fallback_error,
                ),
                show_traceback=False,
                exit_on_critical=False,
            )
            warning_msg = (
                f"Warning: Could not validate assignee (validation unavailable): "
                f"{str(fallback_error)}"
            )
            self._last_canonical_assignee = assignee
            logger.warning(
                "assignee_validation_unavailable",
                error=str(fallback_error),
                severity="infrastructure",
            )
            return True, warning_msg

    @traced("get_canonical_assignee")
    def get_canonical_assignee(self, assignee: str) -> str:
        """Get the canonical form of an assignee name.

        This method should be called after validate_assignee to get the canonical form.

        Args:
            assignee: Input assignee name

        Returns:
            Canonical assignee name (may be same as input if no mapping exists)
        """
        # Fallback to original assignee
        logger.debug("using_original_assignee", assignee=assignee)
        return assignee

    def get_last_canonical_assignee(self) -> str | None:
        """Get the last validated canonical assignee.

        Returns:
            Last canonical assignee or None
        """
        return self._last_canonical_assignee

    def clear_cache(self) -> None:
        """Clear the team members cache."""
        self._team_members_cache = None
        self._cache_timestamp = None
        logger.debug("team_members_cache_cleared")
