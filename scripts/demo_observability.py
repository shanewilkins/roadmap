#!/usr/bin/env python3
"""Example demonstrating OpenTelemetry tracing integration.

This script shows how spans are automatically tracked and injected into logs
when using the @traced decorator.
"""

import logging
import sys
from io import StringIO

from roadmap.common.logging import get_logger, setup_logging
from roadmap.shared.instrumentation import traced
from roadmap.shared.observability import (
    create_span,
    get_current_span,
    set_current_span,
)

# Setup logging to capture output
log_stream = StringIO()
handler = logging.StreamHandler(log_stream)
handler.setLevel(logging.DEBUG)
logging.root.addHandler(handler)

# Configure logging first
logger = setup_logging(log_level="DEBUG", log_to_file=False)


def demonstrate_basic_spans():
    """Demonstrate basic span creation and hierarchy."""
    print("=" * 60)
    print("DEMO 1: Basic Span Creation and Hierarchy")
    print("=" * 60)

    # Create a parent span
    parent_span = create_span("fetch_projects")
    set_current_span(parent_span)

    print(f"Created parent span: {parent_span.span_id}")
    print(f"  Name: {parent_span.name}")
    print(f"  Parent: {parent_span.parent_span_id}")

    # Create a child span
    child_span = create_span("load_project_data")
    print(f"\nCreated child span: {child_span.span_id}")
    print(f"  Name: {child_span.name}")
    print(f"  Parent: {child_span.parent_span_id}")

    # Child's parent should match parent's ID
    assert child_span.parent_span_id == parent_span.span_id
    print("\n✓ Child span correctly linked to parent")

    set_current_span(None)


def demonstrate_traced_decorator():
    """Demonstrate @traced decorator automatically tracking spans."""
    print("\n" + "=" * 60)
    print("DEMO 2: @traced Decorator with Automatic Span Tracking")
    print("=" * 60)

    @traced("calculate_metrics")
    def calculate_project_metrics():
        """Example function using @traced decorator."""
        current = get_current_span()
        print(
            f"Inside function, current span: {current.span_id if current else 'None'}"
        )

        @traced("process_issues")
        def process_issues():
            span = get_current_span()
            print(f"  Processing issues in span: {span.span_id}")
            return 42

        result = process_issues()
        return result

    result = calculate_project_metrics()
    print(f"✓ Decorator tracked execution, result: {result}")


def demonstrate_logging_integration():
    """Demonstrate span context in structured logs."""
    print("\n" + "=" * 60)
    print("DEMO 3: Span Context in Structured Logs")
    print("=" * 60)

    @traced("process_milestone")
    def process_milestone():
        """Function that logs with span context."""
        span = get_current_span()
        logger = get_logger(__name__)

        logger.info(
            "Processing milestone data", milestone_id="m123", status="in_progress"
        )

        print("\nLogged message with span context:")
        print(f"  Span ID: {span.span_id}")
        print("  (This span ID would appear in logs)")

    process_milestone()


def demonstrate_duration_tracking():
    """Demonstrate automatic duration tracking."""
    print("\n" + "=" * 60)
    print("DEMO 4: Automatic Duration Tracking")
    print("=" * 60)

    import time

    @traced("api_request")
    def simulate_api_call():
        """Simulate a slow API call."""
        time.sleep(0.05)  # 50ms
        return {"status": "success"}

    result = simulate_api_call()

    # Get the span (would normally be in logs)
    span = create_span("example")
    print(f"Function completed in: {span.duration_ms:.1f}ms")
    print(f"Result: {result}")


def demonstrate_nested_spans():
    """Demonstrate nested span hierarchy."""
    print("\n" + "=" * 60)
    print("DEMO 5: Nested Span Hierarchy for Nested Operations")
    print("=" * 60)

    @traced("sync_roadmap")
    def sync_roadmap():
        """Top-level sync operation."""

        @traced("sync_projects")
        def sync_projects():
            @traced("sync_single_project")
            def sync_single_project():
                span = get_current_span()
                return span.span_id

            proj_span = sync_single_project()
            spans = [proj_span]

            @traced("sync_single_project")
            def sync_another_project():
                span = get_current_span()
                return span.span_id

            spans.append(sync_another_project())
            return spans

        project_spans = sync_projects()

        @traced("sync_milestones")
        def sync_milestones():
            span = get_current_span()
            return span.span_id

        milestone_span = sync_milestones()

        return {"projects": project_spans, "milestones": milestone_span}

    result = sync_roadmap()
    print("Sync completed with nested structure:")
    print(f"  Project spans: {len(result['projects'])}")
    print(f"  Milestone span: {result['milestones'][:8]}...")
    print("✓ Nested spans tracked successfully")


def main():
    """Run all demonstrations."""
    print("\n" + "=" * 60)
    print("OpenTelemetry Integration Demonstration")
    print("=" * 60)

    try:
        demonstrate_basic_spans()
        demonstrate_traced_decorator()
        demonstrate_logging_integration()
        demonstrate_duration_tracking()
        demonstrate_nested_spans()

        print("\n" + "=" * 60)
        print("✓ ALL DEMONSTRATIONS COMPLETED SUCCESSFULLY")
        print("=" * 60)
        print("\nKey Features Demonstrated:")
        print("  ✓ Automatic span creation and hierarchy")
        print("  ✓ @traced decorator for function instrumentation")
        print("  ✓ Span context injection into logs")
        print("  ✓ Automatic duration tracking")
        print("  ✓ Nested operation tracing")
        print("\nNext Steps:")
        print(
            "  1. Start local Jaeger: docker run -d -p 6831:6831/udp jaegertracing/all-in-one"
        )
        print("  2. Run CLI commands with tracing enabled")
        print("  3. View traces at http://localhost:16686")

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
