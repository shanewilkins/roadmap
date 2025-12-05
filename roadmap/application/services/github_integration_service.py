"""GitHub integration service for roadmap application.

This module handles GitHub-related operations including authentication,
team member queries, assignee validation, and GitHub configuration management.
"""

import os
from datetime import datetime, timedelta
from pathlib import Path

from roadmap.infrastructure.github import GitHubClient
from roadmap.infrastructure.security.credentials import get_credential_manager
from roadmap.shared.config_manager import ConfigManager
from roadmap.shared.errors import (
    ErrorHandler,
    ErrorSeverity,
    ValidationError,
)
from roadmap.shared.logging import get_logger

logger = get_logger(__name__)


class GitHubIntegrationService:
    """Manages GitHub integration and team member operations."""

    def __init__(self, root_path: Path, config_file: Path):
        """Initialize GitHub integration service.

        Args:
            root_path: Root project path
            config_file: Path to config.yaml file
        """
        self.root_path = root_path
        self.config_file = config_file
        self._team_members_cache: list[str] | None = None
        self._cache_timestamp: datetime | None = None
        self._last_canonical_assignee: str | None = None

    def get_github_config(self) -> tuple[str | None, str | None, str | None]:
        """Get GitHub configuration from config file and credentials.

        Returns:
            Tuple of (token, owner, repo) or (None, None, None) if not configured
        """
        try:
            config_manager = ConfigManager(self.config_file)
            config = config_manager.load()
            github_config = getattr(config, "github", None) or {}

            # Get owner and repo from config
            owner = (
                github_config.get("owner") if isinstance(github_config, dict) else None
            )
            repo = (
                github_config.get("repo") if isinstance(github_config, dict) else None
            )

            if not owner or not repo:
                return None, None, None

            # Get token from credentials manager or environment
            credential_manager = get_credential_manager()
            token = credential_manager.get_token()

            if not token:
                token = os.getenv("GITHUB_TOKEN")

            return token, owner, repo

        except Exception as e:
            logger.debug("github_config_retrieval_failed", error=str(e))
            return None, None, None

    def get_team_members(self) -> list[str]:
        """Get team members from GitHub repository.

        Returns:
            List of usernames if GitHub is configured, empty list otherwise
        """
        try:
            token, owner, repo = self.get_github_config()
            if not token or not owner or not repo:
                logger.debug("github_not_configured")
                return []

            # Get team members
            client = GitHubClient(token=token, owner=owner, repo=repo)
            members = client.get_team_members()
            logger.debug("team_members_retrieved", count=len(members))
            return members
        except Exception as e:
            logger.debug("team_members_retrieval_failed", error=str(e))
            # Return empty list if GitHub is not configured or accessible
            return []

    def get_current_user(self, config_file: Path | None = None) -> str | None:
        """Get the current user from config.

        Args:
            config_file: Optional override path to config file

        Returns:
            Current user's name from config if set, None otherwise
        """
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

    def get_cached_team_members(self) -> list[str]:
        """Get team members with caching (5 minute cache).

        Returns:
            List of cached team member usernames
        """
        # Check if cache is valid (5 minutes)
        if (
            self._team_members_cache is not None
            and self._cache_timestamp is not None
            and datetime.now() - self._cache_timestamp < timedelta(minutes=5)
        ):
            logger.debug("using_cached_team_members")
            return self._team_members_cache

        # Refresh cache
        team_members = self.get_team_members()
        self._team_members_cache = team_members
        self._cache_timestamp = datetime.now()
        logger.debug("team_members_cache_refreshed", count=len(team_members))

        return team_members

    def validate_assignee(self, assignee: str) -> tuple[bool, str]:
        """Validate an assignee using the identity management system.

        This validation integrates with the identity management system while
        maintaining backward compatibility with the original API.

        Args:
            assignee: Username to validate

        Returns:
            Tuple of (is_valid, error_message)
            - (True, "") if valid (backward compatible)
            - (False, error_message) if invalid
        """
        try:
            from roadmap.application.services.assignee_validation_service import (
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
                logger.warning("assignee_validation_failed", assignee=assignee)
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
            from roadmap.infrastructure.github import GitHubClient

            client = GitHubClient(token=token, owner=owner, repo=repo)

            # This will do the full GitHub API validation
            github_valid, github_error = client.validate_assignee(assignee)
            if github_valid:
                self._last_canonical_assignee = assignee
                logger.debug("assignee_validated_via_github", assignee=assignee)
                return True, ""
            else:
                logger.warning("assignee_not_in_github", assignee=assignee)
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
            logger.warning("assignee_validation_unavailable", error=str(fallback_error))
            return True, warning_msg

    def get_canonical_assignee(self, assignee: str) -> str:
        """Get the canonical form of an assignee name.

        This method should be called after validate_assignee to get the canonical form.

        Args:
            assignee: Input assignee name

        Returns:
            Canonical assignee name (may be same as input if no mapping exists)
        """
        # Try to get from identity management system
        try:
            from roadmap.future.identity import IdentityManager

            identity_manager = IdentityManager(self.root_path)
            is_valid, result, profile = identity_manager.resolve_assignee(assignee)

            if is_valid and profile:
                canonical = profile.canonical_id
                logger.debug(
                    "canonical_assignee_from_identity",
                    assignee=assignee,
                    canonical=canonical,
                )
                return canonical
            elif is_valid:
                logger.debug(
                    "canonical_assignee_from_result",
                    assignee=assignee,
                    canonical=result,
                )
                return result
        except Exception as e:
            logger.debug("identity_manager_canonical_failed", error=str(e))

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
