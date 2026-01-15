"""Logging utilities for comprehensive structured logging across the application.

Provides helpers for:
- Method entry/exit logging with timing
- Business logic event logging
- State change tracking
- Performance metrics
- Contextual information capture
"""

import time
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from roadmap.common.logging import get_logger

logger = get_logger(__name__)


@contextmanager
def log_operation(
    operation_name: str,
    level: str = "info",
    **context: Any,
) -> Iterator[dict[str, Any]]:
    """Context manager for logging operation execution with timing and context.

    Logs operation entry, execution time, and exit. Captures any exceptions that occur.

    Args:
        operation_name: Name of the operation (e.g., "create_issue", "update_project")
        level: Log level ("debug", "info", "warning")
        **context: Additional context to include in logs (e.g., entity_id, count)

    Yields:
        Dictionary for tracking additional operation metrics

    Example:
        with log_operation("create_issue", entity_id=issue_id, priority="HIGH") as metrics:
            result = create_issue()
            metrics["result_count"] = 1

    The context manager will log:
        - Entry: "{operation_name}_start" with all context
        - Exit: "{operation_name}_complete" with timing and metrics
        - Error: "{operation_name}_failed" if exception occurs
    """
    start_time = time.time()
    metrics: dict[str, Any] = {}
    log_func = getattr(logger, level)

    try:
        log_func(f"{operation_name}_start", **context)
        yield metrics

    except Exception as e:
        elapsed = time.time() - start_time
        log_func(
            f"{operation_name}_failed",
            elapsed_seconds=round(elapsed, 3),
            error_type=type(e).__name__,
            **context,
            **metrics,
        )
        raise

    else:
        elapsed = time.time() - start_time
        log_func(
            f"{operation_name}_complete",
            elapsed_seconds=round(elapsed, 3),
            **context,
            **metrics,
        )


def log_entry(
    operation_name: str,
    level: str = "debug",
    **parameters: Any,
) -> None:
    """Log method entry with parameters.

    Args:
        operation_name: Name of the operation
        level: Log level
        **parameters: Method parameters to log
    """
    log_func = getattr(logger, level)
    log_func(f"{operation_name}_start", **parameters)


def log_exit(
    operation_name: str,
    level: str = "debug",
    elapsed_seconds: float | None = None,
    **result: Any,
) -> None:
    """Log method exit with result and timing.

    Args:
        operation_name: Name of the operation
        level: Log level
        elapsed_seconds: Execution time in seconds
        **result: Result information to log
    """
    log_func = getattr(logger, level)
    if elapsed_seconds is not None:
        result["elapsed_seconds"] = round(elapsed_seconds, 3)
    log_func(f"{operation_name}_complete", **result)


def log_event(
    event_name: str,
    level: str = "info",
    **details: Any,
) -> None:
    """Log a business logic event or milestone.

    Args:
        event_name: Name of the event (e.g., "issue_assigned", "milestone_closed")
        level: Log level
        **details: Event details
    """
    log_func = getattr(logger, level)
    log_func(event_name, **details)


def log_state_change(
    entity_type: str,
    entity_id: str,
    old_state: dict[str, Any],
    new_state: dict[str, Any],
    level: str = "info",
) -> None:
    """Log a state change for an entity.

    Args:
        entity_type: Type of entity (e.g., "Issue", "Milestone")
        entity_id: Entity identifier
        old_state: Previous state
        new_state: New state
        level: Log level
    """
    changes = {}
    all_keys = set(old_state.keys()) | set(new_state.keys())

    for key in all_keys:
        old_val = old_state.get(key)
        new_val = new_state.get(key)
        if old_val != new_val:
            changes[key] = {"from": old_val, "to": new_val}

    log_func = getattr(logger, level)
    log_func(
        f"{entity_type.lower()}_state_changed",
        entity_type=entity_type,
        entity_id=entity_id,
        changes=changes,
    )


def log_collection_operation(
    collection_name: str,
    count: int,
    operation: str = "processed",
    level: str = "debug",
    **context: Any,
) -> None:
    """Log collection processing (e.g., parsed 5 issues).

    Args:
        collection_name: Name of the collection (e.g., "issues", "milestones")
        count: Number of items processed
        operation: Operation performed (e.g., "processed", "created", "updated")
        level: Log level
        **context: Additional context
    """
    log_func = getattr(logger, level)
    log_func(
        f"{collection_name}_{operation}",
        count=count,
        **context,
    )


def log_metric(
    metric_name: str,
    value: float | int,
    unit: str = "",
    level: str = "debug",
    **context: Any,
) -> None:
    """Log a performance or business metric.

    Args:
        metric_name: Name of the metric (e.g., "query_time", "issue_count")
        value: Metric value
        unit: Unit of measurement (e.g., "ms", "seconds", "items")
        level: Log level
        **context: Additional context
    """
    log_func = getattr(logger, level)
    data: dict[str, Any] = {"value": value}
    if unit:
        data["unit"] = unit
    log_func(metric_name, **data, **context)
