"""Common utility functions for CLI operations, file handling, and data processing.

This package provides low-level utilities used across the application:
- CLI helpers: Output formatting, decorators for command functions
- File utilities: File operations and secure file handling
- Path utilities: Path checking and validation
- Status utilities: Status-related helpers
- Timezone utilities: Timezone-aware date/time operations

Note: These are utility functions with minimal dependencies - they should not
import from higher-level modules (services, domain, adapters) to avoid
layer violations and circular dependencies.
"""

from .cli_helpers import OutputFormatHandler, format_output
from .file_utils import (
    SecureFileManager,
    backup_file,
    cleanup_temp_files,
    ensure_directory_exists,
    file_exists_check,
    get_file_size,
    safe_read_file,
    safe_write_file,
)
from .path_utils import build_roadmap_paths
from .status_utils import StatusSummary
from .timezone_utils import (
    TimezoneManager,
    ensure_timezone_aware,
    format_datetime,
    format_relative_time,
    get_timezone_manager,
    migrate_naive_datetime,
    now_local,
    now_utc,
)

__all__ = [
    # CLI helpers
    "OutputFormatHandler",
    "format_output",
    # File utilities
    "SecureFileManager",
    "backup_file",
    "cleanup_temp_files",
    "ensure_directory_exists",
    "file_exists_check",
    "get_file_size",
    "safe_read_file",
    "safe_write_file",
    # Path utilities
    "build_roadmap_paths",
    # Status utilities
    "StatusSummary",
    # Timezone utilities
    "TimezoneManager",
    "ensure_timezone_aware",
    "format_datetime",
    "format_relative_time",
    "get_timezone_manager",
    "migrate_naive_datetime",
    "now_local",
    "now_utc",
]
