"""
Roadmap exception hierarchy.

All exceptions include:
- domain_message: Technical message for logging
- user_message: User-friendly message for CLI output
- exit_code: CLI exit code (for Click commands)

This separation allows logging the full technical context while showing
users a clean, actionable message.

Example:
    try:
        service.create_issue(...)
    except NotInitializedError as e:
        logger.error(e.domain_message)  # Technical details
        click.echo(e.user_message, err=True)  # What user sees
        ctx.exit(e.exit_code)
"""


class RoadmapException(Exception):
    """Base exception for all roadmap errors.

    Attributes:
        domain_message: Technical message for logging/debugging
        user_message: User-friendly message for CLI output
        exit_code: Exit code for CLI commands
    """

    exit_code: int = 1

    def __init__(
        self,
        domain_message: str,
        user_message: str | None = None,
    ):
        """Initialize exception with messages.

        Args:
            domain_message: Technical message (what happened technically)
            user_message: User-friendly message (what user should do)
                         Defaults to domain_message if not provided
        """
        self.domain_message = domain_message
        self.user_message = user_message or domain_message
        super().__init__(domain_message)

    def __str__(self) -> str:
        """Return user message for str()."""
        return self.user_message


# ============================================================================
# Initialization & Setup Errors
# ============================================================================


class NotInitializedError(RoadmapException):
    """Roadmap directory (.roadmap/) not initialized."""

    exit_code = 1

    def __init__(self):
        """Initialize NotInitializedError."""
        super().__init__(
            domain_message="Roadmap .roadmap/ directory not found",
            user_message="Roadmap not initialized. Run 'roadmap init' first.",
        )


class AlreadyInitializedError(RoadmapException):
    """Roadmap already initialized in this directory."""

    exit_code = 1

    def __init__(self, directory: str):
        """Initialize AlreadyInitializedError.

        Args:
            directory: Path where roadmap is already initialized.
        """
        super().__init__(
            domain_message=f"Roadmap already initialized in {directory}",
            user_message=f"Roadmap already initialized in {directory}/. "
            "Use --force to reinitialize.",
        )


# ============================================================================
# Entity Not Found Errors
# ============================================================================


class EntityNotFoundError(RoadmapException):
    """Entity (issue, milestone, project) not found."""

    exit_code = 1

    def __init__(self, entity_type: str, entity_id: str):
        """Initialize EntityNotFoundError.

        Args:
            entity_type: Type of entity (Issue, Milestone, Project).
            entity_id: ID of the missing entity.
        """
        super().__init__(
            domain_message=f"{entity_type} {entity_id} not found in database",
            user_message=f"{entity_type} not found: {entity_id}",
        )


class IssueNotFoundError(EntityNotFoundError):
    """Specific: Issue not found."""

    def __init__(self, issue_id: str):
        """Initialize IssueNotFoundError.

        Args:
            issue_id: ID of the missing issue.
        """
        super().__init__("Issue", issue_id)


class MilestoneNotFoundError(EntityNotFoundError):
    """Specific: Milestone not found."""

    def __init__(self, milestone_id: str):
        """Initialize MilestoneNotFoundError.

        Args:
            milestone_id: ID of the missing milestone.
        """
        super().__init__("Milestone", milestone_id)


class ProjectNotFoundError(EntityNotFoundError):
    """Specific: Project not found."""

    def __init__(self, project_id: str):
        """Initialize ProjectNotFoundError.

        Args:
            project_id: ID of the missing project.
        """
        super().__init__("Project", project_id)


# ============================================================================
# Validation Errors
# ============================================================================


class ValidationError(RoadmapException):
    """Input validation failed."""

    exit_code = 2

    def __init__(self, domain_message: str, user_message: str | None = None):
        """Initialize ValidationError.

        Args:
            domain_message: Technical message describing validation failure.
            user_message: User-friendly message. Defaults to domain_message.
        """
        super().__init__(
            domain_message=domain_message,
            user_message=user_message or domain_message,
        )


class InvalidStatusError(ValidationError):
    """Invalid status value."""

    def __init__(self, status: str, valid_statuses: list[str]):
        """Initialize InvalidStatusError.

        Args:
            status: Invalid status value provided.
            valid_statuses: List of valid status values.
        """
        domain_message = f"Validation failed: status '{status}' is not valid"
        user_message = (
            f"Invalid status: '{status}'. Valid values: {', '.join(valid_statuses)}"
        )
        super().__init__(domain_message=domain_message, user_message=user_message)


class InvalidPriorityError(ValidationError):
    """Invalid priority value."""

    def __init__(self, priority: str, valid_priorities: list[str]):
        """Initialize InvalidPriorityError.

        Args:
            priority: Invalid priority value provided.
            valid_priorities: List of valid priority values.
        """
        domain_message = f"Validation failed: priority '{priority}' is not valid"
        user_message = f"Invalid priority: '{priority}'. Valid values: {', '.join(valid_priorities)}"
        super().__init__(domain_message=domain_message, user_message=user_message)


# ============================================================================
# Operation Errors
# ============================================================================


class OperationError(RoadmapException):
    """Operation failed (creation, update, deletion, etc.)."""

    exit_code = 1

    def __init__(self, operation: str, reason: str):
        """Initialize OperationError.

        Args:
            operation: Description of the operation that failed.
            reason: Reason why the operation failed.
        """
        super().__init__(
            domain_message=f"Failed to {operation}: {reason}",
            user_message=f"Failed to {operation}: {reason}",
        )


class CreateError(OperationError):
    """Failed to create entity."""

    def __init__(self, entity_type: str, reason: str):
        """Initialize CreateError.

        Args:
            entity_type: Type of entity that failed to create.
            reason: Reason for creation failure.
        """
        super().__init__(f"create {entity_type}", reason)


class UpdateError(OperationError):
    """Failed to update entity."""

    def __init__(self, entity_type: str, reason: str):
        """Initialize UpdateError.

        Args:
            entity_type: Type of entity that failed to update.
            reason: Reason for update failure.
        """
        super().__init__(f"update {entity_type}", reason)


class DeleteError(OperationError):
    """Failed to delete entity."""

    def __init__(self, entity_type: str, reason: str):
        """Initialize DeleteError.

        Args:
            entity_type: Type of entity that failed to delete.
            reason: Reason for deletion failure.
        """
        super().__init__(f"delete {entity_type}", reason)


# ============================================================================
# Database/Persistence Errors
# ============================================================================


class PersistenceError(RoadmapException):
    """Database or file persistence operation failed."""

    exit_code = 1

    def __init__(self, operation: str, reason: str):
        """Initialize PersistenceError.

        Args:
            operation: Name of the persistence operation that failed.
            reason: Reason for failure.
        """
        super().__init__(
            domain_message=f"Persistence operation '{operation}' failed: {reason}",
            user_message="Storage operation failed. Check disk space and permissions.",
        )


class DatabaseError(PersistenceError):
    """Database operation failed."""

    def __init__(self, reason: str):
        """Initialize DatabaseError.

        Args:
            reason: Reason for database operation failure.
        """
        super().__init__("database", reason)


class FileOperationError(PersistenceError):
    """File operation failed."""

    def __init__(self, reason: str):
        """Initialize FileOperationError.

        Args:
            reason: Reason for file operation failure.
        """
        super().__init__("file_operation", reason)


# ============================================================================
# Git/GitHub Errors
# ============================================================================


class GitError(RoadmapException):
    """Git operation failed."""

    exit_code = 1

    def __init__(self, operation: str, reason: str):
        """Initialize GitError.

        Args:
            operation: Name of the Git operation that failed.
            reason: Reason for failure.
        """
        super().__init__(
            domain_message=f"Git operation '{operation}' failed: {reason}",
            user_message=f"Git operation failed: {reason}",
        )


class GitHubError(RoadmapException):
    """GitHub integration failed."""

    exit_code = 1

    def __init__(self, operation: str, reason: str):
        """Initialize GitHubError.

        Args:
            operation: Name of the GitHub operation that failed.
            reason: Reason for failure.
        """
        super().__init__(
            domain_message=f"GitHub operation '{operation}' failed: {reason}",
            user_message=f"GitHub operation failed: {reason}",
        )


class NoGitRepositoryError(GitError):
    """Not in a Git repository."""

    def __init__(self):
        """Initialize NoGitRepositoryError."""
        super().__init__(
            "repository_check",
            "Not in a Git repository",
        )


class GitConfigError(GitError):
    """Git configuration missing or invalid."""

    def __init__(self, config_key: str):
        """Initialize GitConfigError.

        Args:
            config_key: Name of the missing Git configuration key.
        """
        super().__init__(
            "config_read",
            f"Git config '{config_key}' not found. Run: git config user.name 'Your Name'",
        )


# ============================================================================
# Configuration/Setup Errors
# ============================================================================


class ConfigurationError(RoadmapException):
    """Configuration is invalid or missing."""

    exit_code = 1

    def __init__(self, issue: str):
        """Initialize ConfigurationError.

        Args:
            issue: Description of the configuration problem.
        """
        super().__init__(
            domain_message=f"Configuration error: {issue}",
            user_message=f"Configuration error: {issue}",
        )


# ============================================================================
# Security Errors
# ============================================================================


class SecurityError(RoadmapException):
    """Security validation failed."""

    exit_code = 1

    def __init__(self, issue: str):
        """Initialize SecurityError.

        Args:
            issue: Description of the security check failure.
        """
        super().__init__(
            domain_message=f"Security check failed: {issue}",
            user_message="Security validation failed. Check file permissions.",
        )


class PathValidationError(SecurityError):
    """Path traversal or invalid path detected."""

    def __init__(self, path: str):
        """Initialize PathValidationError.

        Args:
            path: The invalid path that failed validation.
        """
        super().__init__(f"Invalid path: {path}")
