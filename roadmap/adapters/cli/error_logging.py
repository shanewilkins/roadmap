"""Error logging utilities for structured error handling and diagnostics.

Provides functions to log errors with context, classify errors, and provide
recovery suggestions for better debugging and operational visibility.
"""

import traceback
from typing import Any

from roadmap.common.logging import get_logger

logger = get_logger(__name__)


class ErrorClassification:
    """Error classification constants."""

    USER_ERROR = "user_error"  # User input or usage error
    SYSTEM_ERROR = "system_error"  # Internal system failure
    EXTERNAL_ERROR = "external_error"  # External service failure
    UNKNOWN_ERROR = "unknown_error"  # Unclassified


def classify_error(error: Exception) -> str:
    """Classify an error to help with diagnostics and recovery.

    Args:
        error: The exception to classify

    Returns:
        Error classification string
    """
    # Import these locally to avoid circular imports
    from roadmap.common.errors import RoadmapError, ValidationError

    if isinstance(error, ValidationError | ValueError | TypeError | KeyError):
        return ErrorClassification.USER_ERROR

    if isinstance(error, OSError | RoadmapError):
        return ErrorClassification.SYSTEM_ERROR

    if isinstance(error, ConnectionError | TimeoutError):
        return ErrorClassification.EXTERNAL_ERROR

    return ErrorClassification.UNKNOWN_ERROR


def is_error_recoverable(error: Exception) -> bool:
    """Determine if an error is recoverable with retry.

    Args:
        error: The exception to evaluate

    Returns:
        True if the error is likely recoverable with retry
    """
    recoverable_errors = (
        ConnectionError,
        TimeoutError,
        BlockingIOError,
        BrokenPipeError,
    )
    return isinstance(error, recoverable_errors)


def suggest_recovery(error: Exception, context: dict | None = None) -> str:
    """Suggest a recovery action for an error.

    Args:
        error: The exception to suggest recovery for
        context: Additional context about the operation

    Returns:
        Suggested recovery action
    """
    classification = classify_error(error)

    if is_error_recoverable(error):
        return "retry"

    if classification == ErrorClassification.USER_ERROR:
        return "validate_input"

    if classification == ErrorClassification.EXTERNAL_ERROR:
        return "check_connectivity"

    if classification == ErrorClassification.SYSTEM_ERROR:
        return "manual_intervention"

    return "contact_support"


def log_error_with_context(
    error: Exception,
    operation: str,
    entity_type: str | None = None,
    entity_id: str | None = None,
    additional_context: dict | None = None,
    include_traceback: bool = False,
) -> None:
    """Log an error with comprehensive context for debugging.

    Args:
        error: The exception that occurred
        operation: Name of the operation that failed
        entity_type: Type of entity being operated on
        entity_id: ID of the entity
        additional_context: Any additional context dictionary
        include_traceback: Whether to include full traceback
    """
    classification = classify_error(error)
    recoverable = is_error_recoverable(error)
    recovery_action = suggest_recovery(error)

    context = {
        "operation": operation,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "error_type": type(error).__name__,
        "error_message": str(error),
        "error_classification": classification,
        "is_recoverable": recoverable,
        "suggested_action": recovery_action,
    }

    if additional_context:
        context.update(additional_context)

    if include_traceback:
        context["traceback"] = traceback.format_exc()

    logger.error(f"{operation}_failed", **context)


def log_validation_error(
    error: Exception,
    entity_type: str,
    field_name: str | None = None,
    proposed_value: Any | None = None,
) -> None:
    """Log a validation error with field-specific context.

    Args:
        error: The validation error
        entity_type: Type of entity being validated
        field_name: Name of the field that failed validation
        proposed_value: The value that failed validation
    """
    logger.warning(
        "validation_error",
        error_type=type(error).__name__,
        error_message=str(error),
        entity_type=entity_type,
        field_name=field_name,
        proposed_value=proposed_value,
        suggested_action="validate_input",
    )


def log_database_error(
    error: Exception,
    operation: str,
    entity_type: str | None = None,
    entity_id: str | None = None,
    retry_count: int = 0,
) -> None:
    """Log a database error with recovery context.

    Args:
        error: The database error
        operation: Database operation that failed (create, read, update, delete)
        entity_type: Type of entity
        entity_id: ID of the entity
        retry_count: Number of retries attempted
    """
    recoverable = is_error_recoverable(error)
    recovery_action = "retry" if recoverable else "manual_intervention"

    logger.error(
        "database_operation_failed",
        operation=operation,
        entity_type=entity_type,
        entity_id=entity_id,
        error_type=type(error).__name__,
        error_message=str(error),
        retry_count=retry_count,
        is_recoverable=recoverable,
        suggested_action=recovery_action,
    )


def log_external_service_error(
    error: Exception,
    service_name: str,
    operation: str,
    retry_count: int = 0,
) -> None:
    """Log an external service error (GitHub API, etc.).

    Args:
        error: The error from external service
        service_name: Name of the external service
        operation: Operation being performed
        retry_count: Number of retries attempted
    """
    logger.error(
        "external_service_error",
        service_name=service_name,
        operation=operation,
        error_type=type(error).__name__,
        error_message=str(error),
        retry_count=retry_count,
        is_recoverable=is_error_recoverable(error),
        suggested_action="check_connectivity"
        if is_error_recoverable(error)
        else "contact_support",
    )
