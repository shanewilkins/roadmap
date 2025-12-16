"""Error handling and exception definitions for Roadmap.

This package provides organized error classes, categorized by concern:
- exceptions: High-level exceptions with domain and user messages (NEW)
- error_base: Core exception classes and enums
- error_file: File and I/O related errors
- error_validation: Data validation errors
- error_network: Network and GitHub API errors
- error_git: Git operation errors and configuration errors
- error_security: Security and parsing errors
- error_handler: Error handling utilities
- error_standards: Standardized error handling decorators and context managers (NEW)
"""

# Legacy error hierarchy (backwards compatibility)
from roadmap.common.errors.error_base import (
    ErrorCategory,
    ErrorSeverity,
    RoadmapError,
)
from roadmap.common.errors.error_file import (
    DirectoryCreationError,
    ExportError,
    FileLockError,
    FileOperationError,
    FileReadError,
    FileWriteError,
    ImportError,
    PersistenceError,
)
from roadmap.common.errors.error_git import ConfigurationError, GitOperationError
from roadmap.common.errors.error_handler import ErrorHandler, handle_errors
from roadmap.common.errors.error_network import (
    AuthenticationError,
    GitHubAPIError,
    NetworkError,
)
from roadmap.common.errors.error_security import (
    ParseError,
    PathValidationError,
    SecurityError,
)

# Standardized error handling decorators and utilities
from roadmap.common.errors.error_standards import (
    ErrorContext,
    OperationType,
    RecoveryAction,
    log_operation,
    safe_operation,
    with_error_handling,
)
from roadmap.common.errors.error_validation import (
    IssueNotFoundError,
    MilestoneNotFoundError,
    StateError,
    ValidationError,
)

# New exception hierarchy (recommended for future use)
from roadmap.common.errors.exceptions import (
    AlreadyInitializedError,
    CreateError,
    DatabaseError,
    DeleteError,
    EntityNotFoundError,
    GitConfigError,
    GitError,
    GitHubError,
    InvalidPriorityError,
    InvalidStatusError,
    NoGitRepositoryError,
    NotInitializedError,
    OperationError,
    ProjectNotFoundError,
    RoadmapException,
    UpdateError,
)
from roadmap.common.errors.exceptions import (
    IssueNotFoundError as NewIssueNotFoundError,
)
from roadmap.common.errors.exceptions import (
    MilestoneNotFoundError as NewMilestoneNotFoundError,
)
from roadmap.common.errors.exceptions import (
    ValidationError as NewValidationError,
)

__all__ = [
    # Legacy (backwards compatibility)
    "ErrorSeverity",
    "ErrorCategory",
    "RoadmapError",
    "FileOperationError",
    "DirectoryCreationError",
    "FileReadError",
    "FileWriteError",
    "ExportError",
    "ImportError",
    "PersistenceError",
    "FileLockError",
    "ValidationError",
    "NetworkError",
    "AuthenticationError",
    "GitHubAPIError",
    "GitOperationError",
    "SecurityError",
    "PathValidationError",
    "ParseError",
    "ErrorHandler",
    "handle_errors",
    "StateError",
    "IssueNotFoundError",
    "MilestoneNotFoundError",
    "ConfigurationError",
    # New exceptions (recommended)
    "RoadmapException",
    "NotInitializedError",
    "AlreadyInitializedError",
    "EntityNotFoundError",
    "NewIssueNotFoundError",
    "NewMilestoneNotFoundError",
    "ProjectNotFoundError",
    "NewValidationError",
    "InvalidStatusError",
    "InvalidPriorityError",
    "OperationError",
    "CreateError",
    "UpdateError",
    "DeleteError",
    "DatabaseError",
    "GitError",
    "GitHubError",
    "GitConfigError",
    "NoGitRepositoryError",
    # Standardized error handling decorators and utilities
    "safe_operation",
    "log_operation",
    "with_error_handling",
    "ErrorContext",
    "OperationType",
    "RecoveryAction",
]
