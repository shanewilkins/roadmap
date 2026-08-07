"""Minimal trace context management for distributed tracing.

Provides simple span tracking and timing for debugging performance
and correlating logs within a single CLI invocation.
"""

import contextvars
import time
import uuid
from dataclasses import dataclass
from typing import Optional

# Context variable to store current span
_current_span: contextvars.ContextVar[Optional["Span"]] = contextvars.ContextVar(
    "current_span", default=None
)


@dataclass
class Span:
    """Represents a single operation in a trace."""

    name: str
    span_id: str
    start_time: float
    parent_span_id: str | None = None

    @property
    def duration_ms(self) -> float:
        """Get elapsed time in milliseconds."""
        return (time.time() - self.start_time) * 1000

    def to_dict(self):
        """Convert to dict for logging."""
        return {
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "span_duration_ms": self.duration_ms,
        }


def create_span(name: str) -> Span:
    """Create a new span.

    Args:
        name: Name of the operation being traced

    Returns:
        Span object representing this operation
    """
    parent = _current_span.get()
    span = Span(
        name=name,
        span_id=uuid.uuid4().hex[:16],
        start_time=time.time(),
        parent_span_id=parent.span_id if parent else None,
    )
    return span


def set_current_span(span: Span | None) -> None:
    """Set the current active span.

    Args:
        span: Span object to set as current, or None to clear
    """
    _current_span.set(span)


def get_current_span() -> Span | None:
    """Get the current active span.

    Returns:
        Current Span object or None if no active span
    """
    return _current_span.get()
