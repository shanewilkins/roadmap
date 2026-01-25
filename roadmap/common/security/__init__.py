"""Security utilities for roadmap CLI application.

This package provides security functionality organized by concern:
- exceptions: Security exception types
- logging: Security event logging
- path_validation: Path validation and safety checks
- file_operations: Secure file and directory operations
- filename_sanitization: Filename sanitization
- temp_files: Secure temporary file handling
- export_cleanup: Export validation and backup cleanup

For backward compatibility, all public classes and functions are re-exported
from the root module.
"""

from .exceptions import PathValidationError, SecurityError
from .export_cleanup import cleanup_old_backups, validate_export_size
from .file_operations import (
    create_secure_directory,
    create_secure_file,
    secure_file_permissions,
)
from .filename_sanitization import sanitize_filename
from .logging import configure_security_logging, log_security_event, security_logger
from .path_validation import validate_path
from .temp_files import create_secure_temp_file

__all__ = [
    # Exceptions
    "SecurityError",
    "PathValidationError",
    # Logging
    "log_security_event",
    "configure_security_logging",
    "security_logger",
    # Path validation
    "validate_path",
    # File operations
    "create_secure_file",
    "create_secure_directory",
    "secure_file_permissions",
    # Filename sanitization
    "sanitize_filename",
    # Temp files
    "create_secure_temp_file",
    # Export/backup
    "validate_export_size",
    "cleanup_old_backups",
]
