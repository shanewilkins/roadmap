"""Base presenter class for all CLI presenters.

This module provides an abstract base class that defines the interface for all
presenters in the CLI layer. All presenters should inherit from BasePresenter
to ensure consistent method signatures and behavior.
"""

from abc import ABC, abstractmethod
from typing import Any

from rich.console import Console

from roadmap.common.console import get_console


class BasePresenter(ABC):
    """Abstract base class for all CLI presenters.

    Defines the standard interface that all presenters must implement.
    Presenters are responsible for formatting and rendering data to the console.

    Example:
        class MyPresenter(BasePresenter):
            def render(self, data: dict) -> None:
                console = get_console()
                console.print(data["title"])
    """

    @abstractmethod
    def render(self, data: Any) -> None:
        """Render data to console.

        This is the main entry point for presentation. Implementers should
        format the provided data and output it using the console.

        Args:
            data: The data to render. Type depends on specific presenter.

        Raises:
            ValueError: If data is invalid or incomplete
        """
        pass

    # ─────────────────────────────────────────────────────────────────────────
    # Common Utility Methods (Optional for subclasses to use)
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _get_console() -> Console:
        """Get the standard console instance.

        Returns:
            The global console instance for output
        """
        return get_console()

    @staticmethod
    def _render_header(title: str, style: str = "bold cyan") -> None:
        """Render a section header.

        Args:
            title: Header text
            style: Rich style string (default: bold cyan)
        """
        console = get_console()
        console.print(f"\n[{style}]{title}[/{style}]")

    @staticmethod
    def _render_section(title: str, content: str, style: str = "dim") -> None:
        """Render a named section with indented content.

        Args:
            title: Section title
            content: Section content
            style: Rich style for title (default: dim)
        """
        console = get_console()
        console.print(f"[{style}]{title}:[/{style}] {content}")

    @staticmethod
    def _render_footer(message: str | None = None) -> None:
        """Render footer content.

        Args:
            message: Optional footer message
        """
        console = get_console()
        if message:
            console.print(f"\n[dim]{message}[/dim]")
        else:
            console.print()

    @staticmethod
    def _render_warning(message: str) -> None:
        """Render a warning message.

        Args:
            message: Warning text
        """
        console = get_console()
        console.print(f"[yellow]⚠️  {message}[/yellow]")

    @staticmethod
    def _render_error(message: str) -> None:
        """Render an error message.

        Args:
            message: Error text
        """
        console = get_console()
        console.print(f"[red]❌ {message}[/red]")

    @staticmethod
    def _render_success(message: str) -> None:
        """Render a success message.

        Args:
            message: Success text
        """
        console = get_console()
        console.print(f"[green]✅ {message}[/green]")
