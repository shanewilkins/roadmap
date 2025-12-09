"""Decorators for automatic span creation and timing.

Provides @traced decorator for instrumenting functions with automatic
trace span creation and duration tracking.
"""

import functools
import logging
from collections.abc import Callable
from typing import Any, TypeVar

from .observability import create_span, get_current_span, set_current_span

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


def traced(operation_name: str) -> Callable[[F], F]:
    """Decorator to automatically create spans for functions.

    Wraps a function to create a trace span, track duration, and set
    span context in logs. Works with both sync and async functions.

    Args:
        operation_name: Name of the operation to use in traces

    Returns:
        Decorator function

    Example:
        @traced("fetch_items")
        def get_items():
            return [1, 2, 3]
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            span = create_span(operation_name)
            previous_span = get_current_span()

            try:
                set_current_span(span)
                result = func(*args, **kwargs)

                # Log span completion
                logger.debug(
                    f"Span completed: {operation_name}",
                    extra={
                        "span_id": span.span_id,
                        "parent_span_id": span.parent_span_id,
                        "duration_ms": span.duration_ms,
                    },
                )

                return result
            except Exception as exc:
                logger.error(
                    f"Span failed: {operation_name}",
                    extra={
                        "span_id": span.span_id,
                        "parent_span_id": span.parent_span_id,
                        "duration_ms": span.duration_ms,
                        "error": str(exc),
                    },
                    exc_info=True,
                )
                raise
            finally:
                set_current_span(previous_span)

        return wrapper  # type: ignore

    return decorator


def span_context_processor(
    logger: Any, name: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    """Structlog processor to inject span context into logs.

    Adds span_id and parent_span_id to all log events from within
    an active span.

    Args:
        logger: The logger instance
        name: Name of the logging call
        event_dict: The event dictionary

    Returns:
        Modified event dictionary with span context
    """
    span = get_current_span()
    if span:
        event_dict["span_id"] = span.span_id
        event_dict["parent_span_id"] = span.parent_span_id
        event_dict["span_elapsed_ms"] = span.duration_ms

    return event_dict
