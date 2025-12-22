"""Tests for BasePresenter abstract base class."""

import pytest
from io import StringIO
from unittest.mock import MagicMock, patch

from roadmap.adapters.cli.presentation.base_presenter import BasePresenter


class ConcretePresenter(BasePresenter):
    """Concrete implementation of BasePresenter for testing."""

    def render(self, data):
        """Simple render implementation for testing."""
        console = self._get_console()
        console.print(f"Rendered: {data}")


class TestBasePresenterAbstractMethods:
    """Test BasePresenter abstract method requirements."""

    def test_cannot_instantiate_abstract_class(self):
        """Test that BasePresenter cannot be instantiated directly."""
        with pytest.raises(TypeError):
            BasePresenter()

    def test_concrete_class_can_be_instantiated(self):
        """Test that concrete implementations can be instantiated."""
        presenter = ConcretePresenter()
        assert isinstance(presenter, BasePresenter)

    def test_must_implement_render(self):
        """Test that subclasses must implement render method."""

        class IncompletePresenter(BasePresenter):
            pass

        with pytest.raises(TypeError):
            IncompletePresenter()


class TestBasePresenterUtilityMethods:
    """Test BasePresenter utility methods."""

    def test_get_console(self):
        """Test _get_console returns a console instance."""
        console = BasePresenter._get_console()
        assert console is not None
        # Console should have print method
        assert hasattr(console, "print")

    def test_render_header(self):
        """Test _render_header method."""
        with patch("roadmap.adapters.cli.presentation.base_presenter.get_console") as mock_console:
            mock_instance = MagicMock()
            mock_console.return_value = mock_instance

            BasePresenter._render_header("Test Header")

            # Should call console.print
            mock_instance.print.assert_called_once()
            call_args = mock_instance.print.call_args[0][0]
            assert "Test Header" in call_args

    def test_render_header_with_custom_style(self):
        """Test _render_header with custom style."""
        with patch("roadmap.adapters.cli.presentation.base_presenter.get_console") as mock_console:
            mock_instance = MagicMock()
            mock_console.return_value = mock_instance

            BasePresenter._render_header("Header", style="bold red")

            call_args = mock_instance.print.call_args[0][0]
            assert "Header" in call_args
            assert "bold red" in call_args

    def test_render_section(self):
        """Test _render_section method."""
        with patch("roadmap.adapters.cli.presentation.base_presenter.get_console") as mock_console:
            mock_instance = MagicMock()
            mock_console.return_value = mock_instance

            BasePresenter._render_section("Title", "Content")

            mock_instance.print.assert_called_once()
            call_args = mock_instance.print.call_args[0][0]
            assert "Title" in call_args
            assert "Content" in call_args

    def test_render_footer(self):
        """Test _render_footer method."""
        with patch("roadmap.adapters.cli.presentation.base_presenter.get_console") as mock_console:
            mock_instance = MagicMock()
            mock_console.return_value = mock_instance

            BasePresenter._render_footer("Footer message")

            call_args = mock_instance.print.call_args[0][0]
            assert "Footer message" in call_args

    def test_render_footer_without_message(self):
        """Test _render_footer without message."""
        with patch("roadmap.adapters.cli.presentation.base_presenter.get_console") as mock_console:
            mock_instance = MagicMock()
            mock_console.return_value = mock_instance

            BasePresenter._render_footer()

            # Should still call print
            mock_instance.print.assert_called_once()

    def test_render_warning(self):
        """Test _render_warning method."""
        with patch("roadmap.adapters.cli.presentation.base_presenter.get_console") as mock_console:
            mock_instance = MagicMock()
            mock_console.return_value = mock_instance

            BasePresenter._render_warning("Warning message")

            call_args = mock_instance.print.call_args[0][0]
            assert "Warning message" in call_args
            assert "yellow" in call_args or "⚠️" in call_args

    def test_render_error(self):
        """Test _render_error method."""
        with patch("roadmap.adapters.cli.presentation.base_presenter.get_console") as mock_console:
            mock_instance = MagicMock()
            mock_console.return_value = mock_instance

            BasePresenter._render_error("Error message")

            call_args = mock_instance.print.call_args[0][0]
            assert "Error message" in call_args
            assert "red" in call_args or "❌" in call_args

    def test_render_success(self):
        """Test _render_success method."""
        with patch("roadmap.adapters.cli.presentation.base_presenter.get_console") as mock_console:
            mock_instance = MagicMock()
            mock_console.return_value = mock_instance

            BasePresenter._render_success("Success message")

            call_args = mock_instance.print.call_args[0][0]
            assert "Success message" in call_args
            assert "green" in call_args or "✅" in call_args


class TestConcretePresenterImplementation:
    """Test concrete implementation of BasePresenter."""

    def test_concrete_presenter_has_abstract_method(self):
        """Test that concrete presenter has render method."""
        presenter = ConcretePresenter()
        assert hasattr(presenter, "render")
        assert callable(presenter.render)

    def test_concrete_presenter_can_use_utility_methods(self):
        """Test that concrete presenter can use utility methods."""
        presenter = ConcretePresenter()
        with patch("roadmap.adapters.cli.presentation.base_presenter.get_console") as mock_console:
            mock_instance = MagicMock()
            mock_console.return_value = mock_instance

            # Concrete presenter should be able to call utility methods
            BasePresenter._render_header("Test")
            mock_instance.print.assert_called()


class TestBasePresenterInheritance:
    """Test inheritance patterns with BasePresenter."""

    def test_multiple_concrete_implementations(self):
        """Test multiple concrete implementations of BasePresenter."""

        class Presenter1(BasePresenter):
            def render(self, data):
                pass

        class Presenter2(BasePresenter):
            def render(self, data):
                pass

        p1 = Presenter1()
        p2 = Presenter2()

        assert isinstance(p1, BasePresenter)
        assert isinstance(p2, BasePresenter)
        assert isinstance(p1, Presenter1)
        assert isinstance(p2, Presenter2)

    def test_render_method_signature(self):
        """Test that render method is properly inherited."""
        presenter = ConcretePresenter()
        # Should accept any data type
        with patch("roadmap.adapters.cli.presentation.base_presenter.get_console"):
            presenter.render("string data")
            presenter.render({"dict": "data"})
            presenter.render(["list", "data"])
            presenter.render(None)


class TestBasePresenterDocumentation:
    """Test documentation and docstrings are present."""

    def test_base_presenter_has_docstring(self):
        """Test that BasePresenter has documentation."""
        assert BasePresenter.__doc__ is not None
        assert len(BasePresenter.__doc__) > 0

    def test_render_method_has_docstring(self):
        """Test that render method is documented."""
        assert BasePresenter.render.__doc__ is not None

    def test_utility_methods_have_docstrings(self):
        """Test that utility methods are documented."""
        assert BasePresenter._render_header.__doc__ is not None
        assert BasePresenter._render_section.__doc__ is not None
        assert BasePresenter._render_footer.__doc__ is not None
