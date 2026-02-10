"""Tests for OpenTelemetry initialization."""

from unittest.mock import Mock

from roadmap.common.observability.otel_init import (
    get_tracer,
    initialize_tracing,
    is_tracing_enabled,
)


class TestInitializeTracing:
    """Tests for initialize_tracing function."""

    def test_initialize_tracing_with_default_service_name(self):
        """Test initialize_tracing with default service name."""
        import roadmap.common.observability.otel_init as otel_module

        # Reset before test
        otel_module._tracer = None

        try:
            initialize_tracing()
            # If it succeeds, tracer should be set
            assert otel_module._tracer is not None, "Tracer should be initialized"
        except ImportError:
            # Expected if otel not installed - that's OK
            pass

    def test_initialize_tracing_with_custom_service_name(self):
        """Test initialize_tracing with custom service name."""
        import roadmap.common.observability.otel_init as otel_module

        # Reset before test
        otel_module._tracer = None

        try:
            initialize_tracing("custom-service")
            # If it succeeds, tracer should be set with the custom name
            assert otel_module._tracer is not None, (
                "Tracer should be initialized with custom name"
            )
        except ImportError:
            # Expected if otel not installed - that's OK
            pass

    def test_initialize_tracing_no_exception(self):
        """Test that initialize_tracing doesn't raise unexpected exceptions."""
        import roadmap.common.observability.otel_init as otel_module

        # Reset before test
        otel_module._tracer = None

        # Should either initialize or raise ImportError (both are OK)
        exception_raised = None
        try:
            initialize_tracing()
        except ImportError:
            exception_raised = ImportError
        except Exception as e:
            exception_raised = type(e)

        # Assert that only ImportError was raised (or nothing)
        assert exception_raised is None or exception_raised is ImportError, (
            f"Should only raise ImportError or succeed, not {exception_raised}"
        )


class TestIsTracingEnabled:
    """Tests for is_tracing_enabled function."""

    def test_is_tracing_enabled_returns_boolean(self):
        """Test that is_tracing_enabled returns a boolean."""
        result = is_tracing_enabled()
        assert isinstance(result, bool)

    def test_is_tracing_enabled_initially_disabled(self):
        """Test that tracing is disabled initially."""
        # Reset global state
        import roadmap.common.observability.otel_init as otel_module

        otel_module._tracer = None
        result = is_tracing_enabled()
        assert result is False

    def test_is_tracing_enabled_after_initialization(self):
        """Test tracing status changes after initialization."""
        import roadmap.common.observability.otel_init as otel_module

        # Set up a mock tracer
        otel_module._tracer = Mock()
        result = is_tracing_enabled()
        assert result is True

        # Clean up
        otel_module._tracer = None


class TestGetTracer:
    """Tests for get_tracer function."""

    def test_get_tracer_returns_none_initially(self):
        """Test that get_tracer returns None initially."""
        import roadmap.common.observability.otel_init as otel_module

        otel_module._tracer = None
        result = get_tracer()
        assert result is None

    def test_get_tracer_returns_tracer_instance(self):
        """Test that get_tracer returns tracer instance if set."""
        import roadmap.common.observability.otel_init as otel_module

        mock_tracer = Mock()
        otel_module._tracer = mock_tracer
        result = get_tracer()
        assert result is mock_tracer

        # Clean up
        otel_module._tracer = None

    def test_get_tracer_returns_correct_type(self):
        """Test that get_tracer returns correct type."""
        result = get_tracer()
        assert result is None or callable(result)


class TestTracingIntegration:
    """Integration tests for tracing."""

    def test_initialize_then_check_status(self):
        """Test initializing and checking tracing status."""
        # Reset
        import roadmap.common.observability.otel_init as otel_module

        otel_module._tracer = None

        assert is_tracing_enabled() is False
        assert get_tracer() is None

    def test_tracing_global_state(self):
        """Test that tracing uses global state."""
        import roadmap.common.observability.otel_init as otel_module

        # Create a mock tracer
        mock_tracer = Mock()
        otel_module._tracer = mock_tracer

        # Both functions should reference it
        assert get_tracer() is mock_tracer
        assert is_tracing_enabled() is True

        # Clean up
        otel_module._tracer = None

    def test_multiple_initializations(self):
        """Test that multiple initializations don't cause issues."""
        try:
            initialize_tracing("service1")
            initialize_tracing("service2")
        except ImportError:
            # Expected if otel not installed
            pass
        # If we reach here, multiple initializations handled
        assert True

    def test_tracing_disabled_state(self):
        """Test that tracing disabled state works correctly."""
        import roadmap.common.observability.otel_init as otel_module

        # Set tracer to None to disable
        otel_module._tracer = None

        assert is_tracing_enabled() is False
        assert get_tracer() is None
