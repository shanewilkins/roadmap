"""Assignee validation strategies for RoadmapCore."""

from typing import Any, Protocol

from roadmap.common.logging.error_logging import (
    log_error_with_context,
    log_validation_error,
)
from roadmap.common.observability.instrumentation import traced


class AssigneeValidationResult:
    """Result of assignee validation."""

    def __init__(self, is_valid: bool, message: str = "", canonical_id: str = ""):
        """Initialize validation result.

        Args:
            is_valid: Whether the assignee is valid
            message: Error message if invalid, or warning message
            canonical_id: Canonical ID if valid
        """
        self.is_valid = is_valid
        self.message = message
        self.canonical_id = canonical_id


class GitHubBackend(Protocol):
    """Protocol for GitHub-based validation backends.

    Abstracts GitHub validation away from core logic.
    """

    def validate(self, assignee: str) -> tuple[bool, str, str]:
        """Validate assignee against GitHub.

        Args:
            assignee: Username to validate

        Returns:
            Tuple of (is_valid, error_message, canonical_id)
        """
        ...


class IdentitySystemValidator:
    """Validates assignees using the identity management system."""

    def __init__(self, root_path: str | Any):
        """Initialize with roadmap root path.

        Args:
            root_path: Path to roadmap root directory
        """
        self.root_path = root_path

    def validate(self, assignee: str) -> AssigneeValidationResult:
        """Validate assignee using identity management system.

        Args:
            assignee: Username to validate

        Returns:
            Validation result with canonical ID if successful
        """
        # Identity system not available - return special marker
        return AssigneeValidationResult(
            is_valid=False, message="", canonical_id="identity-unavailable"
        )

    def get_validation_mode(self) -> str:
        """Get the configured validation mode.

        Returns:
            Validation mode string (e.g., 'hybrid', 'local-only', 'github-only')
        """
        return "local-only"


class LocalValidator:
    """Validates assignees using basic local rules."""

    @traced("validate_assignee_local")
    def validate(self, assignee: str) -> AssigneeValidationResult:
        """Validate assignee using basic local rules.

        Args:
            assignee: Username to validate

        Returns:
            Validation result
        """
        # Basic validation for local usage
        if len(assignee) >= 2 and not any(char in assignee for char in "<>{}[]()"):
            return AssigneeValidationResult(is_valid=True, canonical_id=assignee)
        else:
            error = ValueError(f"'{assignee}' is not a valid assignee name")
            log_validation_error(
                error,
                entity_type="Assignee",
                field_name="assignee",
                proposed_value=assignee,
            )
            return AssigneeValidationResult(
                is_valid=False, message=f"'{assignee}' is not a valid assignee name"
            )


class AssigneeValidationStrategy:
    """Orchestrates assignee validation using multiple strategies."""

    def __init__(
        self,
        root_path: str | Any,
        github_config: tuple[str, str, str] | None = None,
        cached_members: set[str] | list[str] | None = None,
    ):
        """Initialize validation strategy.

        Args:
            root_path: Path to roadmap root directory
            github_config: Optional tuple of (token, owner, repo) for GitHub validation
            cached_members: Optional cached team members for performance
        """
        self.root_path = root_path
        self.github_config = github_config
        self.cached_members = cached_members

        self.identity_validator = IdentitySystemValidator(root_path)
        self.local_validator = LocalValidator()

    def _validate_empty(self, assignee: str) -> tuple[bool, str, str] | None:
        """Check if assignee is empty."""
        if not assignee or not assignee.strip():
            return False, "Assignee cannot be empty", ""
        return None

    def _try_identity_validation(self, assignee: str) -> tuple[bool, str, str] | None:
        """Try validating with identity system."""
        identity_result = self.identity_validator.validate(assignee)
        if identity_result.is_valid:
            return True, "", identity_result.canonical_id
        return None

    def _try_identity_unavailable_path(
        self, assignee: str, identity_result
    ) -> tuple[bool, str, str] | None:
        """Handle case where identity system is unavailable."""
        if identity_result.canonical_id != "identity-unavailable":
            return None

        if self.github_config:
            token, owner, repo = self.github_config
            if token and owner and repo:
                github_result = self._validate_with_github(assignee)
                if github_result.is_valid:
                    return True, "", github_result.canonical_id
                else:
                    return False, github_result.message, ""

        local_result = self.local_validator.validate(assignee)
        if local_result.is_valid:
            return True, "", local_result.canonical_id
        else:
            return False, local_result.message, ""

    def _try_identity_failed_path(self, assignee: str, validation_mode: str):
        """Try fallback validation when identity system failed."""
        if self._should_use_github_validation(validation_mode):
            github_result = self._validate_with_github(assignee)
            if github_result.is_valid:
                return True, "", github_result.canonical_id
            elif validation_mode == "github-only":
                return False, github_result.message, ""

        if self._should_use_local_validation(validation_mode):
            local_result = self.local_validator.validate(assignee)
            if local_result.is_valid:
                return True, "", local_result.canonical_id
            else:
                return False, local_result.message, ""

        return None

    @traced("validate_assignee_strategy")
    def validate(self, assignee: str) -> tuple[bool, str, str]:
        """Validate assignee using appropriate strategy.

        Args:
            assignee: Username to validate

        Returns:
            Tuple of (is_valid, error_message, canonical_id)
        """
        try:
            # Check for empty assignee
            empty_result = self._validate_empty(assignee)
            if empty_result is not None:
                is_valid, message, _ = empty_result
                if not is_valid:
                    log_validation_error(
                        ValueError(message),
                        entity_type="Assignee",
                        field_name="assignee",
                        proposed_value=assignee,
                    )
                return empty_result

            assignee = assignee.strip()

            # Try identity system first
            identity_result = self.identity_validator.validate(assignee)
            identity_valid = self._try_identity_validation(assignee)
            if identity_valid is not None:
                return identity_valid

            # Handle identity unavailable case
            identity_unavailable_result = self._try_identity_unavailable_path(
                assignee, identity_result
            )
            if identity_unavailable_result is not None:
                return identity_unavailable_result

            # Identity system is available but validation failed
            validation_mode = identity_result.canonical_id or "local-only"

            # Try fallback validation paths
            fallback_result = self._try_identity_failed_path(assignee, validation_mode)
            if fallback_result is not None:
                return fallback_result

            # No fallback available, return identity system result
            if not identity_result.is_valid:
                log_validation_error(
                    ValueError(identity_result.message),
                    entity_type="Assignee",
                    field_name="assignee",
                    proposed_value=assignee,
                )
            return False, identity_result.message, ""
        except Exception as e:
            log_error_with_context(
                e,
                operation="validate_assignee",
                entity_type="Assignee",
                additional_context={"assignee": assignee},
            )
            raise

    def _should_use_github_validation(self, validation_mode: str) -> bool:
        """Check if GitHub validation should be attempted.

        Args:
            validation_mode: Current validation mode

        Returns:
            True if GitHub validation should be used
        """
        if not self.github_config:
            return False

        token, owner, repo = self.github_config
        if not (token and owner and repo):
            return False

        return validation_mode in ["hybrid", "github-only"]

    def _should_use_local_validation(self, validation_mode: str) -> bool:
        """Check if local validation should be attempted.

        Args:
            validation_mode: Current validation mode

        Returns:
            True if local validation should be used
        """
        # Use local validation if GitHub is not configured
        if not self.github_config:
            return validation_mode in ["local-only", "hybrid"]

        token, owner, repo = self.github_config
        if not (token and owner and repo):
            return validation_mode in ["local-only", "hybrid"]

        return False

    @traced("validate_assignee_github")
    def _validate_with_github(self, assignee: str) -> AssigneeValidationResult:
        """Validate using GitHub.

        Args:
            assignee: Username to validate

        Returns:
            Validation result
        """
        if not self.github_config:
            return AssigneeValidationResult(
                is_valid=False, message="GitHub not configured"
            )

        token, owner, repo = self.github_config
        # Import here to avoid hard dependency on infrastructure
        from roadmap.infrastructure.github_validator import GitHubAssigneeValidator

        github_validator = GitHubAssigneeValidator(
            token, owner, repo, self.cached_members
        )
        result = github_validator.validate(assignee)
        return result
