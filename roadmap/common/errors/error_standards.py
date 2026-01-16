"""Standardized error handling patterns and decorators.

This module provides reusable decorators and context managers for consistent
error handling across the codebase. All decorators automatically log errors
with rich context, support retry logic for transient failures, and convert
exceptions to appropriate RoadmapException types.

Key patterns:
    @safe_operation - Wraps CRUD operations with automatic error handling
    @log_operation - Lightweight operation logging without exception conversion
    with_error_handling() - Context manager for error handling blocks
    ErrorContext - Builder for rich error context at error time

Example:
    @safe_operation(OperationType.CREATE, "Issue")
    def create_issue(title: str) -> Issue:
        return Issue(title)  # Errors automatically caught, logged, wrapped

    @safe_operation(OperationType.SYNC, "GitHub", retryable=True, max_retries=3)
    def fetch_issues(project_id: str) -> list[dict]:
        return github_api.get_issues(project_id)  # Retries on transient failures
"""

import time
from collections.abc import Callable
from contextlib import contextmanager
from functools import wraps
from typing import Any, ParamSpec, TypeVar

from roadmap.common.logging import get_logger
from roadmap.common.logging.error_logging import (
    is_error_recoverable,
    log_error_with_context,
)

logger = get_logger(__name__)

P = ParamSpec("P")
T = TypeVar("T")


# ============================================================================
# STANDARD OPERATION TYPES
# ============================================================================


class OperationType:
    """Standard operation type constants for consistent error handling."""

    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    SYNC = "sync"
    IMPORT = "import"
    EXPORT = "export"
    VALIDATE = "validate"
    AUTHENTICATE = "authenticate"
    FETCH = "fetch"
    SAVE = "save"


# ============================================================================
# ERROR CONTEXT BUILDER - Captures rich context at error time
# ============================================================================


class ErrorContext:
    """Builder for rich error context to include in logs and exceptions.

    Fluent API for capturing operation context that will be included in
    error logs and exception messages. Supports context like entity IDs,
    input parameters, operation state, and suggested recovery actions.

    Example:
        context = (
            ErrorContext("sync", "Issues")
            .with_entity_id(project_id)
            .with_input(force=True, filters={})
            .with_state(synced_count=10, failed_count=1)
            .with_recovery("retry", "Check network connection")
        )
        context_dict = context.build()
    """

    def __init__(self, operation: str, entity_type: str | None = None):
        """Initialize error context.

        Args:
            operation: Name of the operation (e.g., "create", "sync")
            entity_type: Type of entity being operated on (e.g., "Issue", "Milestone")
        """
        self.data: dict[str, Any] = {
            "operation": operation,
        }
        if entity_type:
            self.data["entity_type"] = entity_type

    def with_entity_id(self, entity_id: str | int) -> "ErrorContext":
        """Add entity ID to context."""
        self.data["entity_id"] = str(entity_id)
        return self

    def with_input(self, **kwargs: Any) -> "ErrorContext":
        """Add input parameters to context."""
        if kwargs:
            self.data["input"] = kwargs
        return self

    def with_state(self, **kwargs: Any) -> "ErrorContext":
        """Add operation state to context."""
        if kwargs:
            self.data["state"] = kwargs
        return self

    def with_recovery(self, action: str, details: str = "") -> "ErrorContext":
        """Add recovery suggestion to context."""
        self.data["recovery_action"] = action
        if details:
            self.data["recovery_details"] = details
        return self

    def with_attempt(self, attempt: int, max_retries: int) -> "ErrorContext":
        """Add retry attempt information to context."""
        self.data["retry_attempt"] = attempt
        self.data["max_retries"] = max_retries
        return self

    def build(self) -> dict[str, Any]:
        """Build and return the context dictionary."""
        return self.data.copy()


# ============================================================================
# DECORATOR: @safe_operation - Wraps CRUD operations with standard handling
# ============================================================================


def safe_operation(
    operation_type: str,
    entity_type: str | None = None,
    include_traceback: bool = False,
    retryable: bool = False,
    max_retries: int = 1,
    retry_delay: float = 0.5,
    retry_backoff: float = 2.0,
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Decorator for safe operation execution with standard error handling.

    Wraps create, read, update, delete, sync operations with:
    - Automatic error classification and logging with rich context
    - Graceful exception conversion to appropriate RoadmapException
    - Optional retry on recoverable errors with exponential backoff
    - Traceback inclusion for debugging when needed

    Args:
        operation_type: Type of operation (OperationType constants)
        entity_type: Type of entity being operated on (Issue, Milestone, etc.)
        include_traceback: Whether to include full traceback in error logs
        retryable: Whether to retry on recoverable errors
        max_retries: Maximum retry attempts (if retryable=True)
        retry_delay: Initial delay in seconds between retries
        retry_backoff: Multiplier for delay after each retry (exponential backoff)

    Returns:
        Decorator function

    Example:
        @safe_operation(OperationType.CREATE, "Issue")
        def create_issue(title: str, description: str) -> Issue:
            # Function body - errors are automatically caught and logged
            return Issue(title, description)

        @safe_operation(OperationType.DELETE, "Issue", retryable=True, max_retries=3)
        def delete_issue(issue_id: str) -> None:
            # Will retry up to 3 times on network/timeout errors
            pass

    Raises:
        CreateError: If operation_type is CREATE and original error occurs
        UpdateError: If operation_type is UPDATE and original error occurs
        DeleteError: If operation_type is DELETE and original error occurs
        RoadmapException: For other operation types
    """
    from roadmap.common.errors.exceptions import (
        CreateError,
        DeleteError,
        RoadmapException,
        UpdateError,
    )

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:  # type: ignore[return-value]
            context = ErrorContext(operation_type, entity_type)

            # Capture first string/int argument as entity_id if available
            if args and isinstance(args[0], str | int):
                context.with_entity_id(args[0])
            elif "id" in kwargs and isinstance(kwargs["id"], str | int):
                context.with_entity_id(kwargs["id"])

            # Capture input parameters for debugging
            context.with_input(**kwargs)

            attempt = 0
            last_error: Exception | None = None
            delay = retry_delay

            while attempt < max_retries:
                try:
                    if attempt > 0:
                        logger.debug(
                            f"retry_{operation_type}",
                            attempt=attempt,
                            max_retries=max_retries,
                            entity_type=entity_type,
                        )
                    return func(*args, **kwargs)

                except RoadmapException:
                    # Already a roadmap exception - let it propagate
                    raise

                except Exception as e:
                    # Lazy import to avoid infrastructure dependency in common layer
                    from roadmap.common.logging.error_logging import (
                        is_error_recoverable,
                        log_error_with_context,
                    )

                    last_error = e
                    is_recoverable = is_error_recoverable(e)

                    # Build context with retry information if applicable
                    error_context = context.build()
                    if retryable and max_retries > 1:
                        error_context["retry_attempt"] = attempt + 1
                        error_context["max_retries"] = max_retries

                    # Log the error with full context
                    log_error_with_context(
                        e,
                        f"{operation_type}_{entity_type or 'unknown'}",
                        entity_type=entity_type,
                        additional_context=error_context,
                        include_traceback=include_traceback,
                    )

                    # Check if we should retry
                    if retryable and is_recoverable and attempt < max_retries - 1:
                        attempt += 1
                        logger.info(
                            f"retrying_{operation_type}",
                            attempt=attempt,
                            max_retries=max_retries,
                            error_type=type(e).__name__,
                            delay_seconds=delay,
                        )
                        time.sleep(delay)
                        delay *= retry_backoff
                        continue  # Retry

                    # Convert to appropriate RoadmapException if not retrying
                    attempt_info = (
                        f" (after {attempt} retries)"
                        if retryable and attempt > 0
                        else ""
                    )
                    error_msg = f"{str(e)}{attempt_info}"

                    if operation_type == OperationType.CREATE:
                        raise CreateError(
                            entity_type or "entity",
                            error_msg,
                        ) from e
                    elif operation_type == OperationType.UPDATE:
                        raise UpdateError(
                            entity_type or "entity",
                            error_msg,
                        ) from e
                    elif operation_type == OperationType.DELETE:
                        raise DeleteError(
                            entity_type or "entity",
                            error_msg,
                        ) from e
                    else:
                        raise RoadmapException(
                            domain_message=f"{operation_type} failed: {error_msg}",
                            user_message=f"Failed to {operation_type}: {str(e)}",
                        ) from e

            # If we exhausted retries, raise the last error
            if last_error:
                raise last_error

        return wrapper

    return decorator


# ============================================================================
# DECORATOR: @log_operation - For operations that don't need exception handling
# ============================================================================


def log_operation(
    operation_type: str,
    entity_type: str | None = None,
    log_inputs: bool = True,
    log_output: bool = False,
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Lightweight decorator to log operation execution without error handling.

    Use for operations that are already well-protected or don't need automatic
    error conversion. Logs the operation, inputs, and optionally outputs.

    Args:
        operation_type: Type of operation
        entity_type: Type of entity
        log_inputs: Whether to log input arguments
        log_output: Whether to log the return value

    Returns:
        Decorator function

    Example:
        @log_operation(OperationType.READ, "Issue", log_inputs=True)
        def get_issue(issue_id: str) -> Issue:
            # Log entry/exit but let exceptions propagate normally
            return issues_db.get(issue_id)
    """

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            if log_inputs:
                logger.info(
                    f"{operation_type}_started",
                    entity_type=entity_type,
                    **kwargs,
                )

            result = func(*args, **kwargs)

            if log_output and result:
                logger.info(
                    f"{operation_type}_completed",
                    entity_type=entity_type,
                )

            return result

        return wrapper

    return decorator


# ============================================================================
# CONTEXT MANAGER: with_error_handling - For non-function error handling
# ============================================================================


@contextmanager
def with_error_handling(
    operation: str,
    entity_type: str | None = None,
    entity_id: str | int | None = None,
    fail_silently: bool = False,
    include_traceback: bool = False,
):
    """Context manager for error handling in operation blocks.

    Use when you have a block of code that might fail and you want consistent
    error logging and exception wrapping without using a decorator.

    Args:
        operation: Name of the operation (e.g., "sync", "export")
        entity_type: Type of entity involved
        entity_id: ID of the entity being operated on
        fail_silently: If True, log error but don't re-raise
        include_traceback: Include full traceback in logs

    Yields:
        None

    Raises:
        RoadmapException: If error occurs and fail_silently=False

    Example:
        with with_error_handling("sync", "Issues", entity_id=project_id):
            # Code that might fail
            sync_issues(project_id)

        # Error is automatically logged and wrapped in appropriate exception
    """
    from roadmap.common.errors.exceptions import RoadmapException

    try:
        yield
    except RoadmapException:
        raise
    except Exception as e:
        context = {
            "operation": operation,
            "entity_type": entity_type,
            "entity_id": str(entity_id) if entity_id else None,
        }

        log_error_with_context(
            e,
            operation,
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id else None,
            additional_context=context,
            include_traceback=include_traceback,
        )

        if not fail_silently:
            raise RoadmapException(
                domain_message=f"{operation} failed: {str(e)}",
                user_message=f"Failed to {operation}",
            ) from e


# ============================================================================
# RECOVERY ACTION HANDLERS - For application-level recovery
# ============================================================================


class RecoveryAction:
    """Handles recovery from common error scenarios.

    Provides static methods for common recovery patterns like retry with
    backoff, handling missing files, and suggesting recovery actions.

    Example:
        try:
            result = risky_operation()
        except ConnectionError as e:
            if RecoveryAction.is_retryable(e):
                result = RecoveryAction.retry_with_backoff(risky_operation)
    """

    @staticmethod
    def retry_with_backoff(
        func: Callable[..., T],
        max_attempts: int = 3,
        initial_delay: float = 0.5,
        backoff_factor: float = 2.0,
    ) -> T:  # type: ignore[return-value]
        """Retry a function with exponential backoff.

        Args:
            func: Function to retry
            max_attempts: Maximum number of attempts
            initial_delay: Initial delay in seconds between retries
            backoff_factor: Multiplier for delay after each retry

        Returns:
            Return value from successful function call

        Raises:
            Last exception if all retries exhausted
        """
        last_error: Exception | None = None
        delay = initial_delay

        for attempt in range(max_attempts):
            try:
                return func()
            except Exception as e:
                last_error = e
                if attempt < max_attempts - 1 and is_error_recoverable(e):
                    time.sleep(delay)
                    delay *= backoff_factor
                else:
                    raise

        if last_error:
            raise last_error

    @staticmethod
    def is_retryable(error: Exception) -> bool:
        """Check if an error is retryable.

        Args:
            error: Exception to check

        Returns:
            True if error is recoverable/retryable
        """
        return is_error_recoverable(error)

    @staticmethod
    def handle_missing_file(
        filepath: str, create_default: bool = True, content: str = ""
    ) -> bool:
        """Handle missing file error by creating default.

        Args:
            filepath: Path to the missing file
            create_default: Whether to create a default file
            content: Content to write to the file

        Returns:
            True if file was created successfully, False otherwise
        """
        if not create_default:
            return False

        from pathlib import Path

        try:
            Path(filepath).parent.mkdir(parents=True, exist_ok=True)
            Path(filepath).write_text(content)
            logger.info("created_missing_file", filepath=filepath)
            return True
        except Exception as e:
            logger.error("failed_to_create_file", filepath=filepath, error=str(e))
            return False

    @staticmethod
    def handle_permission_error(filepath: str) -> str:
        """Suggest recovery action for permission error.

        Args:
            filepath: Path that had permission error

        Returns:
            Suggested recovery command
        """
        return f"Check file permissions: chmod u+rw {filepath}"

    @staticmethod
    def handle_connection_error(service: str) -> str:
        """Suggest recovery action for connection error.

        Args:
            service: Name of service that couldn't be reached

        Returns:
            Suggested recovery action
        """
        return (
            f"Unable to reach {service}. Check network connection and service status."
        )


__all__ = [
    "OperationType",
    "ErrorContext",
    "safe_operation",
    "log_operation",
    "with_error_handling",
    "RecoveryAction",
]
