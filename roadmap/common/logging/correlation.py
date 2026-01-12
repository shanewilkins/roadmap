"""Correlation ID tracking for distributed tracing across operations."""

import contextvars
import uuid

# Context variable for correlation ID tracking across async operations
correlation_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "correlation_id", default=None
)


def add_correlation_id(logger, _method_name, event_dict):
    """Structlog processor to add correlation ID to all log entries."""
    cid = correlation_id_var.get()
    if cid:
        event_dict["correlation_id"] = cid
    return event_dict


def set_correlation_id(correlation_id: str | None = None) -> str:
    """Set correlation ID for current context.

    Args:
        correlation_id: Optional correlation ID (generates UUID if None)

    Returns:
        The correlation ID that was set
    """
    cid = correlation_id or str(uuid.uuid4())
    correlation_id_var.set(cid)
    return cid


def get_correlation_id() -> str | None:
    """Get correlation ID from current context.

    Returns:
        Current correlation ID or None
    """
    return correlation_id_var.get()


def clear_correlation_id() -> None:
    """Clear correlation ID from current context."""
    correlation_id_var.set(None)
