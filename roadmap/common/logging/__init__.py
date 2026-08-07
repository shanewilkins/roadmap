"""Structured logging for roadmap CLI application."""

import structlog  # noqa: F401

from roadmap.common.logging.correlation import (
    add_correlation_id,
    clear_correlation_id,
    correlation_id_var,
    get_correlation_id,
    set_correlation_id,
)
from roadmap.common.logging.decorators import (
    get_current_user,
    log_audit_event,
    log_command,
    log_operation_duration,
    verbose_output,
)
from roadmap.common.logging.error_logging import (
    ErrorClassification,
    classify_error,
    is_error_recoverable,
    log_database_error,
    log_error_with_context,
    log_external_service_error,
    log_validation_error,
    suggest_recovery,
)
from roadmap.common.logging.formatters import (
    SENSITIVE_KEYS,
    StructuredFormatter,
    include_structured_fields_in_message,
    scrub_sensitive_data,
)
from roadmap.common.logging.loggers import (
    get_application_logger,
    get_domain_logger,
    get_infrastructure_logger,
    get_logger,
    get_presentation_logger,
    get_security_logger,
)
from roadmap.common.logging.performance_tracking import (
    OperationTimer,
    track_database_operation,
    track_file_operation,
    track_operation_time,
    track_sync_operation,
)
from roadmap.common.logging.utils import (
    configure_for_testing,
    get_stack_trace,
    log_operation,
    log_operation_timing,
    setup_logging,
    should_sample,
)

__all__ = [
    # Formatters and scrubbing
    "StructuredFormatter",
    "scrub_sensitive_data",
    "include_structured_fields_in_message",
    "SENSITIVE_KEYS",
    # Correlation ID
    "correlation_id_var",
    "set_correlation_id",
    "get_correlation_id",
    "clear_correlation_id",
    "add_correlation_id",
    # Logger factories
    "get_logger",
    "get_domain_logger",
    "get_application_logger",
    "get_infrastructure_logger",
    "get_presentation_logger",
    "get_security_logger",
    # Setup and utilities
    "setup_logging",
    "get_stack_trace",
    "log_operation_timing",
    "log_operation",
    "should_sample",
    "configure_for_testing",
    # Decorators
    "log_command",
    "verbose_output",
    "get_current_user",
    "log_audit_event",
    "log_operation_duration",
    # Error logging
    "ErrorClassification",
    "classify_error",
    "is_error_recoverable",
    "log_database_error",
    "log_error_with_context",
    "log_external_service_error",
    "log_validation_error",
    "suggest_recovery",
    # Performance tracking
    "OperationTimer",
    "track_database_operation",
    "track_file_operation",
    "track_operation_time",
    "track_sync_operation",
]

# Initialize logging at module load time
# This is the single source of truth for production logging configuration
setup_logging(log_level="INFO", debug_mode=False, log_to_file=True)

# Get default logger instance
logger = get_logger("roadmap")
