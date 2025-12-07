"""Error handling and exception definitions for Roadmap.

This package provides organized error classes, categorized by concern:
- error_base: Core exception classes and enums
- error_file: File and I/O related errors
- error_validation: Data validation errors
- error_network: Network and GitHub API errors
- error_git: Git operation errors and configuration errors
- error_security: Security and parsing errors
- error_handler: Error handling utilities
"""

from roadmap.common.errors.error_base import ErrorCategory, ErrorSeverity, RoadmapError
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
from roadmap.common.errors.error_validation import (
    IssueNotFoundError,
    MilestoneNotFoundError,
    StateError,
    ValidationError,
)

__all__ = [
    "ErrorSeverity",
    "ErrorCategory",
    "RoadmapError",
    "FileOperationError",
    "ValidationError",
    "NetworkError",
    "GitOperationError",
    "ConfigurationError",
    "IssueNotFoundError",
    "MilestoneNotFoundError",
    "GitHubAPIError",
    "AuthenticationError",
    "StateError",
    "ParseError",
    "PersistenceError",
    "FileLockError",
    "DirectoryCreationError",
    "FileReadError",
    "FileWriteError",
    "ExportError",
    "ImportError",
    "SecurityError",
    "PathValidationError",
    "ErrorHandler",
    "handle_errors",
]
