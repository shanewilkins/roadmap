"""Observability and instrumentation utilities.

This module provides:
- Tracing with OpenTelemetry (otel_init)
- Span context management (observability)
- Instrumentation decorators (instrumentation)

Use submodule imports for clarity:
  from roadmap.common.observability.instrumentation import traced
  from roadmap.common.observability.observability import get_current_span, set_current_span
  from roadmap.common.observability.otel_init import initialize_tracing, is_tracing_enabled
"""

from .instrumentation import span_context_processor, traced
from .observability import Span, create_span, get_current_span, set_current_span
from .otel_init import get_tracer, initialize_tracing, is_tracing_enabled

__all__ = [
    "traced",
    "span_context_processor",
    "Span",
    "create_span",
    "get_current_span",
    "set_current_span",
    "get_tracer",
    "initialize_tracing",
    "is_tracing_enabled",
]
