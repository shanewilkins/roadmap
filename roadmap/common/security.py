"""Backward compatibility facade for security module.

This module provides backward compatibility by re-exporting security utilities
from the refactored security package.

New code should import directly from:
- roadmap.common.security.exceptions
- roadmap.common.security.logging
- roadmap.common.security.path_validation
- roadmap.common.security.file_operations
- roadmap.common.security.filename_sanitization
- roadmap.common.security.temp_files
- roadmap.common.security.export_cleanup
"""

import warnings

# Re-export all public classes and functions for backward compatibility
from roadmap.common.security import (
    PathValidationError,
    SecurityError,
    cleanup_old_backups,
    configure_security_logging,
    create_secure_directory,
    create_secure_file,
    create_secure_temp_file,
    log_security_event,
    sanitize_filename,
    secure_file_permissions,
    validate_export_size,
    validate_path,
)

# Emit deprecation warning when this module is imported
warnings.warn(
    "The 'roadmap.common.security' module is deprecated. "
    "Use 'roadmap.common.security' package directly instead. "
    "This module will be removed in v1.0.0.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = [
    # Exceptions
    "SecurityError",
    "PathValidationError",
    # Logging
    "log_security_event",
    "configure_security_logging",
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
