"""Logging utilities and decorators for cross-layer infrastructure concerns.

Provides decorators for command logging, error logging, and performance tracking
for comprehensive audit trail and observability across the application.
"""

from roadmap.infrastructure.logging.decorators import (
    get_current_user,
    log_audit_event,
    log_command,
    log_operation_duration,
    verbose_output,
)
from roadmap.infrastructure.logging.error_logging import (
    ErrorClassification,
    classify_error,
    is_error_recoverable,
    log_database_error,
    log_error_with_context,
    log_external_service_error,
    log_validation_error,
    suggest_recovery,
)
from roadmap.infrastructure.logging.performance_tracking import (
    OperationTimer,
    track_database_operation,
    track_file_operation,
    track_operation_time,
    track_sync_operation,
)

__all__ = [
    "log_command",
    "verbose_output",
    "get_current_user",
    "log_audit_event",
    "log_operation_duration",
    "ErrorClassification",
    "classify_error",
    "is_error_recoverable",
    "suggest_recovery",
    "log_error_with_context",
    "log_validation_error",
    "log_database_error",
    "log_external_service_error",
    "track_operation_time",
    "track_database_operation",
    "track_file_operation",
    "track_sync_operation",
    "OperationTimer",
]
