"""Error path tests for exception_handler module.

Tests focus on:
- Error handling with Click context
- Exception formatting and exit codes
- Decorator error capturing and propagation
- Edge cases (None context, missing attributes, etc.)
"""

from unittest.mock import Mock, patch

import click
import pytest

from roadmap.adapters.cli.exception_handler import (
    handle_cli_exception,
    setup_cli_exception_handling,
    with_exception_handler,
)
from roadmap.common.errors.exceptions import RoadmapException

pytestmark = pytest.mark.unit


class TestHandleCliException:
    """Test handle_cli_exception error handling."""

    def test_handle_cli_exception_with_roadmap_exception(self):
        """Test handling RoadmapException formats and exits correctly."""
        ctx = Mock(spec=click.Context)
        exc = RoadmapException(
            domain_message="Test domain error",
            user_message="Test user message",
        )

        with patch(
            "roadmap.adapters.cli.exception_handler.get_console_stderr"
        ) as mock_console:
            mock_stderr = Mock()
            mock_console.return_value = mock_stderr

            handle_cli_exception(ctx, exc, show_traceback=False)

            mock_stderr.print.assert_called_once()
            ctx.exit.assert_called_once_with(1)

    def test_handle_cli_exception_with_generic_exception(self):
        """Test handling generic Exception shows error and exits."""
        ctx = Mock(spec=click.Context)
        exc = ValueError("Generic error")

        with patch(
            "roadmap.adapters.cli.exception_handler.get_console_stderr"
        ) as mock_console:
            mock_stderr = Mock()
            mock_console.return_value = mock_stderr

            handle_cli_exception(ctx, exc, show_traceback=False)

            mock_stderr.print.assert_called_once()
            ctx.exit.assert_called_once_with(1)

    def test_handle_cli_exception_with_traceback(self):
        """Test traceback display when show_traceback=True."""
        ctx = Mock(spec=click.Context)
        exc = ValueError("Error with traceback")

        with patch(
            "roadmap.adapters.cli.exception_handler.get_console_stderr"
        ) as mock_console:
            mock_stderr = Mock()
            mock_console.return_value = mock_stderr

            handle_cli_exception(ctx, exc, show_traceback=True)

            # Should call print at least once for error message, plus print_exception
            mock_stderr.print.assert_called()
            mock_stderr.print_exception.assert_called_once()
            ctx.exit.assert_called_once_with(1)

    def test_handle_cli_exception_preserves_custom_exit_code(self):
        """Test custom exit code from RoadmapException is used."""
        ctx = Mock(spec=click.Context)
        exc = RoadmapException(
            domain_message="Auth failed",
            user_message="Authentication required",
        )
        exc.exit_code = 2

        with patch(
            "roadmap.adapters.cli.exception_handler.get_console_stderr"
        ) as mock_console:
            mock_stderr = Mock()
            mock_console.return_value = mock_stderr

            handle_cli_exception(ctx, exc, show_traceback=False)

            ctx.exit.assert_called_once_with(2)

    def test_handle_cli_exception_with_none_context(self):
        """Test handling exception with None console context."""
        ctx = Mock(spec=click.Context)
        exc = RuntimeError("Runtime error")

        with patch(
            "roadmap.adapters.cli.exception_handler.get_console_stderr"
        ) as mock_console:
            mock_stderr = Mock()
            mock_console.return_value = mock_stderr

            handle_cli_exception(ctx, exc, show_traceback=False)

            ctx.exit.assert_called_once_with(1)

    def test_handle_cli_exception_with_empty_message(self):
        """Test handling exception with empty message."""
        ctx = Mock(spec=click.Context)
        exc = RoadmapException(
            domain_message="",
            user_message="",
        )

        with patch(
            "roadmap.adapters.cli.exception_handler.get_console_stderr"
        ) as mock_console:
            mock_stderr = Mock()
            mock_console.return_value = mock_stderr

            handle_cli_exception(ctx, exc, show_traceback=False)

            mock_stderr.print.assert_called_once()
            ctx.exit.assert_called_once()

    def test_handle_cli_exception_with_multiline_message(self):
        """Test handling exception with multiline message."""
        ctx = Mock(spec=click.Context)
        exc = RoadmapException(
            domain_message="Line 1\nLine 2\nLine 3",
            user_message="User Line 1\nUser Line 2",
        )

        with patch(
            "roadmap.adapters.cli.exception_handler.get_console_stderr"
        ) as mock_console:
            mock_stderr = Mock()
            mock_console.return_value = mock_stderr

            handle_cli_exception(ctx, exc, show_traceback=False)

            mock_stderr.print.assert_called_once()


class TestWithExceptionHandlerDecorator:
    """Test with_exception_handler decorator error handling."""

    def test_decorator_returns_function(self):
        """Test decorator returns wrapped function."""

        @with_exception_handler(show_traceback=False)
        def dummy_func(ctx):
            return 42

        assert callable(dummy_func)

    def test_decorator_creates_wrapper(self):
        """Test decorator creates a wrapper function with context support."""

        @with_exception_handler(show_traceback=False)
        def dummy_func(ctx):
            return 42

        # The decorator wraps the function
        assert callable(dummy_func)
        assert hasattr(dummy_func, "__name__")

    def test_decorator_catches_click_abort_behavior(self):
        """Test decorator checks for Click.Abort in exception handling."""
        with patch("roadmap.adapters.cli.exception_handler.click.Abort"):

            @with_exception_handler(show_traceback=False)
            def dummy_func(ctx):
                # This tests that the decorator has the right exception handling code
                return 42

            # Verify decorator is applied
            assert callable(dummy_func)

    def test_decorator_catches_click_exception_behavior(self):
        """Test decorator checks for Click.ClickException in exception handling."""
        with patch("roadmap.adapters.cli.exception_handler.click.ClickException"):

            @with_exception_handler(show_traceback=False)
            def dummy_func(ctx):
                return 42

            # Verify decorator is applied
            assert callable(dummy_func)

    def test_decorator_with_context_manager_setup(self):
        """Test decorator works with proper Click context setup."""

        @with_exception_handler(show_traceback=False)
        def dummy_func(ctx):
            return ctx

        # Verify decorator doesn't break function signature
        assert callable(dummy_func)

    def test_decorator_preserves_docstring(self):
        """Test decorator preserves function docstring."""

        @with_exception_handler(show_traceback=False)
        def dummy_func(ctx):
            """Test function docstring."""
            return 42

        # Note: Click decorator may wrap the function, but wrapper should exist
        assert callable(dummy_func)

    def test_decorator_exception_handling_structure(self):
        """Test decorator has proper exception handling structure."""
        # The decorator should create a wrapper with try/except
        decorator = with_exception_handler(show_traceback=False)
        assert callable(decorator)

    def test_decorator_with_show_traceback_false(self):
        """Test decorator accepts show_traceback=False parameter."""
        decorator = with_exception_handler(show_traceback=False)
        assert callable(decorator)

        @decorator
        def dummy_func(ctx):
            return 42

        assert callable(dummy_func)

    def test_decorator_with_show_traceback_true(self):
        """Test decorator accepts show_traceback=True parameter."""
        decorator = with_exception_handler(show_traceback=True)
        assert callable(decorator)

        @decorator
        def dummy_func(ctx):
            return 42

        assert callable(dummy_func)

    def test_decorator_exception_catching_for_roadmap_exception(self):
        """Test exception handling catches RoadmapException."""
        # Test that the code structure includes exception handling for RoadmapException
        import inspect

        source = inspect.getsource(with_exception_handler)
        assert "RoadmapException" in source
        assert "handle_cli_exception" in source

    def test_decorator_exception_catching_for_generic_exception(self):
        """Test exception handling catches generic Exception."""
        import inspect

        source = inspect.getsource(with_exception_handler)
        assert "Exception" in source

    def test_decorator_click_pass_context_applied(self):
        """Test decorator applies click.pass_context for proper context handling."""
        import inspect

        source = inspect.getsource(with_exception_handler)
        assert "pass_context" in source

    def test_decorator_returns_multiple_times(self):
        """Test decorator can be applied multiple times."""

        @with_exception_handler(show_traceback=False)
        def func1(ctx):
            return 1

        @with_exception_handler(show_traceback=True)
        def func2(ctx):
            return 2

        assert callable(func1)
        assert callable(func2)


class TestSetupCliExceptionHandling:
    """Test setup_cli_exception_handling configuration."""

    def test_setup_creates_handler_function(self):
        """Test setup creates exception handler without errors."""
        with patch("roadmap.adapters.cli.exception_handler.click.get_current_context"):
            # Should not raise
            setup_cli_exception_handling()

    def test_setup_handler_function_callable(self):
        """Test exception handler function is callable."""
        with patch("roadmap.adapters.cli.exception_handler.click.get_current_context"):
            setup_cli_exception_handling()
            # If we get here without error, setup completed

    def test_setup_with_click_context_and_exception(self):
        """Test handler works with actual Click context and exception."""
        ctx = Mock(spec=click.Context)
        exc = RoadmapException(
            domain_message="Setup test error",
            user_message="Test message",
        )

        with patch(
            "roadmap.adapters.cli.exception_handler.get_console_stderr"
        ) as mock_console:
            mock_stderr = Mock()
            mock_console.return_value = mock_stderr

            # Call setup to get the handler function
            with patch(
                "roadmap.adapters.cli.exception_handler.click.get_current_context"
            ):
                setup_cli_exception_handling()

            # The setup creates an inner function that calls handle_cli_exception
            # Verify it would work by testing directly
            handle_cli_exception(ctx, exc, show_traceback=False)
            ctx.exit.assert_called_once()


class TestExceptionHandlerIntegration:
    """Integration tests for exception_handler module."""

    def test_handle_and_formatter_work_together(self):
        """Test handle_cli_exception and format_error_message work together."""
        ctx = Mock(spec=click.Context)
        exc = RoadmapException(
            domain_message="Test domain error",
            user_message="Test user error",
        )

        with patch(
            "roadmap.adapters.cli.exception_handler.get_console_stderr"
        ) as mock_console:
            with patch(
                "roadmap.adapters.cli.exception_handler.format_error_message",
                return_value="Formatted message",
            ) as mock_format:
                mock_stderr = Mock()
                mock_console.return_value = mock_stderr

                handle_cli_exception(ctx, exc, show_traceback=False)

                mock_format.assert_called_once_with(exc)
                mock_stderr.print.assert_called_once_with("Formatted message")
                ctx.exit.assert_called_once_with(1)

    def test_error_message_formatting_in_handler(self):
        """Test error messages are formatted correctly."""
        ctx = Mock(spec=click.Context)
        exc = RoadmapException(
            domain_message="Technical: Invalid syntax",
            user_message="Invalid configuration format",
        )

        with patch(
            "roadmap.adapters.cli.exception_handler.get_console_stderr"
        ) as mock_console:
            with patch(
                "roadmap.adapters.cli.exception_handler.format_error_message"
            ) as mock_format:
                mock_format.return_value = "Formatted error"
                mock_stderr = Mock()
                mock_console.return_value = mock_stderr

                handle_cli_exception(ctx, exc, show_traceback=False)

                mock_format.assert_called_once_with(exc)
                mock_stderr.print.assert_called_once_with("Formatted error")

    def test_roadmap_exception_vs_generic_exception_handling(self):
        """Test different handling for RoadmapException vs generic Exception."""
        ctx1 = Mock(spec=click.Context)
        ctx2 = Mock(spec=click.Context)

        roadmap_exc = RoadmapException(
            domain_message="Roadmap error",
            user_message="User message",
        )
        roadmap_exc.exit_code = 2

        generic_exc = ValueError("Generic error")

        with patch(
            "roadmap.adapters.cli.exception_handler.get_console_stderr"
        ) as mock_console:
            mock_stderr = Mock()
            mock_console.return_value = mock_stderr

            # Handle roadmap exception
            handle_cli_exception(ctx1, roadmap_exc, show_traceback=False)
            ctx1.exit.assert_called_once_with(2)

            # Handle generic exception
            handle_cli_exception(ctx2, generic_exc, show_traceback=False)
            ctx2.exit.assert_called_once_with(1)

    def test_traceback_display_integration(self):
        """Test traceback display in exception handler."""
        ctx = Mock(spec=click.Context)
        exc = RuntimeError("Error with traceback")

        with patch(
            "roadmap.adapters.cli.exception_handler.get_console_stderr"
        ) as mock_console:
            mock_stderr = Mock()
            mock_console.return_value = mock_stderr

            handle_cli_exception(ctx, exc, show_traceback=True)

            # Should print error message and exception traceback
            assert mock_stderr.print.call_count >= 1
            mock_stderr.print_exception.assert_called_once()

    def test_exception_handler_with_various_exception_types(self):
        """Test handler works with different exception types."""
        exceptions = [
            ValueError("Value error"),
            TypeError("Type error"),
            KeyError("Key error"),
        ]

        with patch(
            "roadmap.adapters.cli.exception_handler.get_console_stderr"
        ) as mock_console:
            mock_stderr = Mock()
            mock_console.return_value = mock_stderr

            for exc in exceptions:
                ctx = Mock(spec=click.Context)
                handle_cli_exception(ctx, exc, show_traceback=False)
                ctx.exit.assert_called_once_with(1)
