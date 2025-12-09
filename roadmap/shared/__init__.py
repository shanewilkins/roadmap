"""Shared utilities and formatters.

This layer contains cross-cutting concerns and utilities shared across multiple layers:
- Formatting utilities (display, export, table layouts)
- Observability (logging, auditing, performance tracking, tracing)
- Common helpers and validators

These utilities are used by CLI, services, and domain layers.
"""

from .formatters import (
    IssueExporter,
    IssueTableFormatter,
    KanbanLayout,
    KanbanOrganizer,
    MilestoneTableFormatter,
    ProjectTableFormatter,
)
from .instrumentation import span_context_processor, traced
from .observability import Span, create_span, get_current_span, set_current_span
from .otel_init import get_tracer, initialize_tracing, is_tracing_enabled

__all__ = [
    "IssueTableFormatter",
    "IssueExporter",
    "KanbanOrganizer",
    "KanbanLayout",
    "MilestoneTableFormatter",
    "ProjectTableFormatter",
    # Observability exports
    "Span",
    "create_span",
    "get_current_span",
    "set_current_span",
    "traced",
    "span_context_processor",
    "initialize_tracing",
    "is_tracing_enabled",
    "get_tracer",
]
