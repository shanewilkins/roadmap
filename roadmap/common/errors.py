"""
Exception Definitions and Error Enums for Roadmap

This module serves as the primary public API for error handling, re-exporting
all error classes from specialized category modules.
"""

from roadmap.common.error_base import ErrorCategory, ErrorSeverity, RoadmapError
from roadmap.common.error_file import (
    DirectoryCreationError,
    ExportError,
    FileLockError,
    FileOperationError,
    FileReadError,
    FileWriteError,
    ImportError,
    PersistenceError,
)
from roadmap.common.error_git import ConfigurationError, GitOperationError
from roadmap.common.error_handler import ErrorHandler, handle_errors
from roadmap.common.error_network import (
    AuthenticationError,
    GitHubAPIError,
    NetworkError,
)
from roadmap.common.error_security import ParseError, PathValidationError, SecurityError
from roadmap.common.error_validation import (
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
