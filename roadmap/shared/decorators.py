"""Decorators for service operations with intelligent error handling and logging.

Provides consistent patterns for:
- Exception handling across service methods
- Configurable logging levels for different failure scenarios
- Optional stack trace capture for debugging
- Production-ready error reporting

The @service_operation decorator is the foundation for eliminating silent failures
and providing production observability.
"""

import traceback as tb_module
from collections.abc import Callable
from functools import wraps
from typing import Any, Literal

from roadmap.shared.logging import get_logger

logger = get_logger(__name__)


def service_operation(
    default_return: Any = None,
    error_message: str | None = None,
    log_level: Literal["debug", "info", "warning", "error"] = "error",
    include_traceback: bool = False,
    log_success: bool = False,
):
    """Decorator for service methods with intelligent error handling.

    **Key Features:**
    - Mandatory error logging (no silent failures)
    - Configurable logging severity based on failure type
    - Optional stack traces for debugging
    - Automatic error context enrichment
    - Consistent return value handling

    **Log Level Guidance:**

    Use `"warning"` for operational failures (expected to sometimes fail):
        - File not found, item not found, permission denied
        - Intended for: get/list operations, optional checks, lookups
        - Example: @service_operation(log_level="warning")

    Use `"error"` for unexpected failures (should rarely happen):
        - Database corruption, file system errors, system resource issues
        - Intended for: create/update/delete, critical operations
        - Example: @service_operation(log_level="error")

    Use `"debug"` for health/status checks (non-critical, potentially noisy):
        - Polling operations, availability checks, status queries
        - Intended for: frequent checking operations
        - Example: @service_operation(log_level="debug")

    Use `"info"` sparingly for business milestones (use debug/warning otherwise)
        - Intended for: significant business events worth tracking
        - Example: @service_operation(log_level="info")

    **Parameters:**

    Args:
        default_return: Value to return on error (default {})
        error_message: Custom error message (auto-generated if None)
        log_level: Logging severity - "debug"|"info"|"warning"|"error"
        include_traceback: Include full stack trace in logs (for debugging)
        log_success: Whether to log on successful completion

    **Usage Examples:**

    ```python
    # Database read operation (expected to sometimes fail)
    @service_operation(default_return=None, log_level="warning")
    def get_issue(self, issue_id: str) -> Issue | None:
        return self._find_issue(issue_id)

    # File parsing with debugging support
    @service_operation(
        default_return=[],
        log_level="warning",
        include_traceback=True
    )
    def list_issues(self):
        return FileEnumerationService.enumerate_and_parse(...)

    # Database write operation (should rarely fail)
    @service_operation(
        default_return=False,
        log_level="error",
        include_traceback=True
    )
    def save_issue(self, issue):
        return self.db.save(issue)

    # Health check polling (less critical)
    @service_operation(default_return=False, log_level="debug")
    def is_healthy(self) -> bool:
        return self.check_readiness()
    ```

    **Error Logging Output:**

    When a decorated function raises an exception:

    ```
    WARNING: Error in get_issue | error=not found | error_type=FileNotFoundError | operation=get_issue
    ERROR: Error in save_issue | error=connection lost | error_type=ConnectionError | operation=save_issue | traceback=<full trace>
    DEBUG: Error in is_healthy | error=timeout | error_type=TimeoutError | operation=is_healthy
    ```

    **Testing:**

    The decorator ensures all failures are logged. Test that:
    - Successful calls don't log errors
    - Failed calls log at the specified level
    - Default return value is returned on error
    - Exception details are captured in logs
    - Traceback is included when requested
    """
    # Validate log level
    valid_levels = {"debug", "info", "warning", "error"}
    if log_level not in valid_levels:
        raise ValueError(f"log_level must be one of {valid_levels}, got '{log_level}'")

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(self, *args, **kwargs) -> Any:
            try:
                result = func(self, *args, **kwargs)
                if log_success:
                    logger.debug(f"{func.__name__}_completed")
                return result
            except Exception as e:
                _log_operation_error(
                    func=func,
                    error=e,
                    error_message=error_message,
                    log_level=log_level,
                    include_traceback=include_traceback,
                )
                return default_return if default_return is not None else {}

        return wrapper

    return decorator


def _log_operation_error(
    func: Callable,
    error: Exception,
    error_message: str | None,
    log_level: str,
    include_traceback: bool,
) -> None:
    """Helper to log operation errors consistently with context.

    Captures error details and routes to appropriate logger method
    based on configured log level.

    Args:
        func: The function that failed
        error: The exception that was caught
        error_message: Optional custom message
        log_level: Logging level to use ("debug"|"info"|"warning"|"error")
        include_traceback: Whether to include full stack trace
    """
    msg = error_message or f"Error in {func.__name__}"

    log_data = {
        "error": str(error),
        "error_type": type(error).__name__,
        "operation": func.__name__,
    }

    if include_traceback:
        log_data["traceback"] = tb_module.format_exc()

    # Route to appropriate logger method
    log_func = getattr(logger, log_level, logger.error)
    log_func(msg, **log_data)
