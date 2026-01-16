"""Test observability and tracing integration."""

import pytest

from roadmap.common.observability.instrumentation import traced
from roadmap.common.observability.observability import (
    create_span,
    get_current_span,
    set_current_span,
)


def test_span_creation():
    """Test basic span creation."""
    span = create_span("test_operation")

    assert span.name == "test_operation"
    assert span.span_id is not None
    assert span.parent_span_id is None
    assert span.duration_ms >= 0


def test_span_context():
    """Test span context management."""
    # Clear any existing span
    set_current_span(None)

    # Create first span
    span1 = create_span("operation_1")
    set_current_span(span1)

    assert get_current_span() == span1

    # Create child span
    span2 = create_span("operation_2")
    assert span2.parent_span_id == span1.span_id

    set_current_span(span2)
    assert get_current_span() == span2

    # Clear
    set_current_span(None)
    assert get_current_span() is None


def test_traced_decorator():
    """Test @traced decorator."""

    @traced("test_function")
    def my_function(x: int) -> int:
        return x * 2

    result = my_function(5)
    assert result == 10


def test_traced_decorator_with_exception():
    """Test @traced decorator handles exceptions."""

    @traced("failing_function")
    def my_function():
        raise ValueError("Test error")

    with pytest.raises(ValueError):
        my_function()


def test_span_duration():
    """Test span duration tracking."""
    import time

    span = create_span("timed_operation")
    time.sleep(0.01)  # 10ms

    # Duration should be at least 10ms
    assert span.duration_ms >= 10


def test_span_to_dict():
    """Test span serialization."""
    span = create_span("operation")
    span_dict = span.to_dict()

    assert "span_id" in span_dict
    assert "parent_span_id" in span_dict
    assert "span_duration_ms" in span_dict
    assert span_dict["span_id"] == span.span_id
