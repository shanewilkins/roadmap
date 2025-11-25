"""Assignee validation strategies for RoadmapCore."""

from typing import Any


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
        try:
            from roadmap.future.identity import IdentityManager

            identity_manager = IdentityManager(self.root_path)
            is_valid, result, profile = identity_manager.resolve_assignee(assignee)

            if is_valid:
                canonical_id = profile.canonical_id if profile else result
                return AssigneeValidationResult(
                    is_valid=True, canonical_id=canonical_id
                )
            else:
                # Return the validation mode so caller knows what fallbacks are appropriate
                mode = identity_manager.config.validation_mode
                return AssigneeValidationResult(
                    is_valid=False, message=result, canonical_id=mode
                )

        except Exception:
            # Identity system not available - return special marker
            return AssigneeValidationResult(
                is_valid=False, message="", canonical_id="identity-unavailable"
            )

    def get_validation_mode(self) -> str:
        """Get the configured validation mode.

        Returns:
            Validation mode string (e.g., 'hybrid', 'local-only', 'github-only')
        """
        try:
            from roadmap.future.identity import IdentityManager

            identity_manager = IdentityManager(self.root_path)
            return identity_manager.config.validation_mode
        except Exception:
            return "local-only"


class GitHubValidator:
    """Validates assignees against GitHub repository access."""

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
            Validation result
        """
        # Check cache first
        if self.cached_members and assignee in self.cached_members:
            return AssigneeValidationResult(is_valid=True, canonical_id=assignee)

        # Do full validation via API
        try:
            from ..infrastructure.github import GitHubClient

            client = GitHubClient(token=self.token, owner=self.owner, repo=self.repo)
            github_valid, github_error = client.validate_assignee(assignee)

            if github_valid:
                return AssigneeValidationResult(is_valid=True, canonical_id=assignee)
            else:
                return AssigneeValidationResult(is_valid=False, message=github_error)

        except Exception as e:
            return AssigneeValidationResult(
                is_valid=False, message=f"GitHub validation failed: {e}"
            )


class LocalValidator:
    """Validates assignees using basic local rules."""

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

    def validate(self, assignee: str) -> tuple[bool, str, str]:
        """Validate assignee using appropriate strategy.

        Args:
            assignee: Username to validate

        Returns:
            Tuple of (is_valid, error_message, canonical_id)
        """
        if not assignee or not assignee.strip():
            return False, "Assignee cannot be empty", ""

        assignee = assignee.strip()

        # Try identity management system first
        identity_result = self.identity_validator.validate(assignee)

        if identity_result.is_valid:
            return True, "", identity_result.canonical_id

        # Check if identity system is unavailable (not configured)
        identity_unavailable = identity_result.canonical_id == "identity-unavailable"

        if identity_unavailable:
            # Identity system not available - try other validation methods
            # First try GitHub if configured
            if self.github_config:
                token, owner, repo = self.github_config
                if token and owner and repo:
                    github_result = self._validate_with_github(assignee)
                    if github_result.is_valid:
                        return True, "", github_result.canonical_id
                    else:
                        # GitHub validation failed, return the error
                        return False, github_result.message, ""

            # No GitHub or GitHub failed - allow local validation
            local_result = self.local_validator.validate(assignee)
            if local_result.is_valid:
                return True, "", local_result.canonical_id
            else:
                return False, local_result.message, ""

        # Identity system is available but validation failed
        # The canonical_id field contains the validation mode
        validation_mode = identity_result.canonical_id or "local-only"

        # Try GitHub validation if configured and mode allows it
        if self._should_use_github_validation(validation_mode):
            github_result = self._validate_with_github(assignee)
            if github_result.is_valid:
                return True, "", github_result.canonical_id
            elif validation_mode == "github-only":
                return False, github_result.message, ""

        # Try local validation if mode allows it
        if self._should_use_local_validation(validation_mode):
            local_result = self.local_validator.validate(assignee)
            if local_result.is_valid:
                return True, "", local_result.canonical_id
            else:
                return False, local_result.message, ""

        # No fallback available, return identity system result
        return False, identity_result.message, ""

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
        github_validator = GitHubValidator(token, owner, repo, self.cached_members)
        return github_validator.validate(assignee)
