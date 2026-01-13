"""Shared utilities and formatters.

This layer contains cross-cutting concerns and utilities shared across multiple layers:
- Formatting utilities (display, export, table layouts)
- Observability (logging, auditing, performance tracking, tracing)
- Common helpers and validators

These utilities are used by CLI, services, and domain layers.
"""

from .instrumentation import span_context_processor, traced
from .observability import Span, create_span, get_current_span, set_current_span
from .otel_init import get_tracer, initialize_tracing, is_tracing_enabled


def __getattr__(name):
    """Lazy load formatter classes to avoid circular imports during initialization."""
    formatter_names = {
        "IssueExporter",
        "IssueTableFormatter",
        "KanbanLayout",
        "KanbanOrganizer",
        "MilestoneTableFormatter",
        "ProjectTableFormatter",
    }
    if name in formatter_names:
        from .formatters import (
            IssueExporter,
            IssueTableFormatter,
            KanbanLayout,
            KanbanOrganizer,
            MilestoneTableFormatter,
            ProjectTableFormatter,
        )

        formatters_dict = {
            "IssueExporter": IssueExporter,
            "IssueTableFormatter": IssueTableFormatter,
            "KanbanLayout": KanbanLayout,
            "KanbanOrganizer": KanbanOrganizer,
            "MilestoneTableFormatter": MilestoneTableFormatter,
            "ProjectTableFormatter": ProjectTableFormatter,
        }
        return formatters_dict[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


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
