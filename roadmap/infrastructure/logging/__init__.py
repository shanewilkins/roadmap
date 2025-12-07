"""Logging utilities and decorators for cross-layer infrastructure concerns.

Provides decorators for command logging, error logging, and performance tracking
for comprehensive audit trail and observability across the application.
"""

from roadmap.infrastructure.logging.decorators import (
    get_current_user,
    log_command,
    verbose_output,
)
from roadmap.infrastructure.logging.error_logging import (
    ErrorClassification,
    classify_error,
    is_error_recoverable,
    log_error_with_context,
    suggest_recovery,
)
from roadmap.infrastructure.logging.performance_tracking import (
    track_database_operation,
    track_file_operation,
    track_operation_time,
)

__all__ = [
    "log_command",
    "verbose_output",
    "get_current_user",
    "ErrorClassification",
    "classify_error",
    "is_error_recoverable",
    "suggest_recovery",
    "log_error_with_context",
    "track_operation_time",
    "track_database_operation",
    "track_file_operation",
]
