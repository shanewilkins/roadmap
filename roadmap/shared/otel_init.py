"""OpenTelemetry initialization for local tracing.

Sets up trace exporter and jaeger integration for local development.
Exports traces to local Jaeger agent on UDP port 6831.
"""

import logging

logger = logging.getLogger(__name__)

# Global tracer instance
_tracer: object | None = None


def initialize_tracing(service_name: str = "roadmap-cli") -> None:
    """Initialize OpenTelemetry tracing with Jaeger exporter.

    This must be called once at application startup before any tracing
    operations. It configures trace export to a local Jaeger agent.

    Args:
        service_name: Name of the service for Jaeger (default: "roadmap-cli")

    Example:
        from roadmap.shared.otel_init import initialize_tracing
        initialize_tracing()
    """
    global _tracer

    try:
        from opentelemetry.exporter.jaeger.thrift import JaegerExporter
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        # Create Jaeger exporter
        jaeger_exporter = JaegerExporter(
            agent_host_name="localhost",
            agent_port=6831,
        )

        # Create tracer provider
        tracer_provider = TracerProvider()
        tracer_provider.add_span_processor(BatchSpanProcessor(jaeger_exporter))

        # Set global tracer provider
        from opentelemetry import trace

        trace.set_tracer_provider(tracer_provider)

        _tracer = trace.get_tracer(__name__)

        logger.debug(
            "OpenTelemetry tracing initialized",
            extra={"service": service_name, "exporter": "jaeger"},
        )

    except ImportError as e:
        logger.warning(
            f"OpenTelemetry not available: {e}. "
            "Tracing features will be disabled. "
            "Install with: pip install opentelemetry-exporter-jaeger"
        )
        _tracer = None


def is_tracing_enabled() -> bool:
    """Check if tracing has been initialized.

    Returns:
        True if tracing is available, False otherwise
    """
    return _tracer is not None


def get_tracer():
    """Get the global tracer instance.

    Returns:
        Tracer instance if initialized, None otherwise
    """
    return _tracer
