"""
Unified output management for CLI commands.

Centralizes all CLI output handling across:
- Multiple formats (table/json/csv/markdown)
- Terminal vs file output
- Test-friendly rendering (ANSI stripping)
- Format auto-detection

This replaces scattered console.print() and click.secho() calls with
a unified interface that supports exporting to files.
"""

import os
import sys
from pathlib import Path

import click
from rich.console import Console

from roadmap.common.output_formatter import OutputFormatter
from roadmap.common.output_models import TableData


class OutputManager:
    """
    Unified output management for CLI commands.

    Handles rendering of TableData in multiple formats:
    - table: Pretty Rich table (default, terminal-friendly)
    - plain: ASCII table (POSIX-compliant, no ANSI codes)
    - json: Machine-readable JSON (API/data export)
    - csv: RFC 4180 CSV (Excel/Sheets import)
    - markdown: Markdown table (documentation)
    - html: HTML table with styling (email/web)

    Can output to terminal or file with automatic format detection.

    Example:
        # Terminal output
        manager = OutputManager(format='table')
        manager.render_table(table_data)

        # File output
        manager = OutputManager(
            format='csv',
            output_file=Path('/tmp/export.csv')
        )
        manager.render_table(table_data)

        # In Click commands
        @click.option('--format', type=click.Choice(['table', 'json', 'csv', 'html']))
        @click.option('--output', type=click.Path())
        def list_items(format, output):
            manager = OutputManager(
                format=format or 'table',
                output_file=Path(output) if output else None
            )
            table_data = IssueTableFormatter.issues_to_table_data(items)
            manager.render_table(table_data)
    """

    VALID_FORMATS = {"table", "plain", "json", "csv", "markdown", "html"}

    def __init__(
        self,
        format: str = "table",
        output_file: Path | None = None,
        force_plain: bool = False,
    ):
        """
        Initialize OutputManager.

        Args:
            format: Output format (table/plain/json/csv/markdown/html)
            output_file: Optional file path to save output
            force_plain: Force plain text output (for testing)

        Raises:
            ValueError: If format is not valid
        """
        if format not in self.VALID_FORMATS:
            raise ValueError(
                f"Invalid format '{format}'. Must be one of: {', '.join(self.VALID_FORMATS)}"
            )

        self.format = format
        self.output_file = output_file
        self.force_plain = force_plain

        # Determine color support
        should_use_colors = self._should_use_colors()

        # Initialize console for Rich output
        # Use test-safe settings that work with Click's test runner
        is_testing = self._is_testing_environment()
        self.console = Console(
            file=sys.stdout,
            force_terminal=should_use_colors and not is_testing,
            no_color=not should_use_colors or is_testing or force_plain,
            width=80 if is_testing else 120,
        )

    @staticmethod
    def _is_testing_environment() -> bool:
        """Detect if running in a test environment."""
        return any(
            [
                "PYTEST_CURRENT_TEST" in os.environ,
                "pytest" in sys.modules,
                "_pytest" in [m.split(".")[0] for m in sys.modules.keys()],
                os.environ.get("NO_COLOR") in ("1", "true"),
            ]
        )

    @staticmethod
    def _should_use_colors() -> bool:
        """
        Detect if terminal supports colors.

        Checks:
        1. NO_COLOR env var (standard no-color support)
        2. FORCE_COLOR env var (force colors even in non-TTY)
        3. Terminal type (dumb, emacs, etc. don't support colors)
        4. isatty() - check if stdout is a terminal
        5. CI environment detection

        Returns:
            True if colors should be used, False otherwise
        """
        # Check NO_COLOR first (highest priority to disable)
        if os.environ.get("NO_COLOR", "").lower() in ("1", "true", "yes"):
            return False

        # Check FORCE_COLOR (explicit enable)
        if os.environ.get("FORCE_COLOR", "").lower() in ("1", "true", "yes"):
            return True

        # Check terminal type
        term = os.environ.get("TERM", "").lower()
        if term in ("dumb", "emacs", "milk"):
            return False

        # Check if stdout is a TTY
        try:
            if not sys.stdout.isatty():
                return False
        except (AttributeError, Exception):
            # If isatty() fails, assume no colors
            return False

        # Check for CI environments (usually don't support interactive colors)
        ci_env_vars = [
            "CI",
            "CONTINUOUS_INTEGRATION",
            "GITHUB_ACTIONS",
            "GITLAB_CI",
            "TRAVIS",
            "CIRCLECI",
            "JENKINS_URL",
            "BUILDKITE",
            "DRONE",
        ]
        if any(var in os.environ for var in ci_env_vars):
            # CI is set, but some CI systems do support colors
            # Check for specific ones that support colors
            if os.environ.get("GITHUB_ACTIONS") == "true":
                return True  # GitHub Actions supports colors
            if os.environ.get("GITLAB_CI") == "true":
                return True  # GitLab CI supports colors
            # Others might not, so be conservative
            return False

        # Default: use colors (most modern terminals support them)
        return True

    def render_table(self, table_data: TableData) -> None:
        """
        Render a table in the configured format.

        Handles both terminal output and file saves.
        Automatically detects test environment and strips ANSI codes.

        Args:
            table_data: TableData object to render
        """
        formatter = OutputFormatter(table_data)

        if self.format == "table":
            # Rich table for terminal (pretty output)
            content = formatter.to_rich()
            self.console.print(content)

        elif self.format == "plain":
            # Plain ASCII for POSIX compatibility
            content = formatter.to_plain_text()
            self._output_content(content)

        elif self.format == "json":
            # JSON for data export
            content = formatter.to_json()
            self._output_content(content)

        elif self.format == "csv":
            # CSV for spreadsheet import
            content = formatter.to_csv()
            self._output_content(content)

        elif self.format == "markdown":
            # Markdown for documentation
            content = formatter.to_markdown()
            self._output_content(content)

        elif self.format == "html":
            # HTML for email/web
            content = formatter.to_html()
            self._output_content(content)

    def render_rich(self, renderable) -> None:
        """
        Render a Rich-compatible object.

        Useful for rendering non-table objects like Panels, etc.

        Args:
            renderable: Any Rich-compatible renderable object
        """
        self.console.print(renderable)

    def _output_content(self, content: str) -> None:
        """
        Output content to file or stdout.

        Args:
            content: String content to output
        """
        if self.output_file:
            self.output_file.parent.mkdir(parents=True, exist_ok=True)
            self.output_file.write_text(content)
            click.secho(f"✅ Saved to {self.output_file}", fg="green")
        else:
            click.echo(content)

    def print_message(
        self, message: str, style: str | None = None, fg: str | None = None
    ) -> None:
        """
        Print a simple message (not a table).

        Useful for status messages, warnings, etc.

        Args:
            message: Message to print
            style: Rich style (e.g., 'bold red')
            fg: Click color (e.g., 'green')
        """
        if self.format in {"json", "csv", "markdown"}:
            # Skip non-data messages in data export formats
            return

        if self.format == "table" or self.format == "plain":
            if fg:
                click.secho(message, fg=fg)
            elif style:
                self.console.print(message, style=style)
            else:
                click.echo(message)

    def print_styled(
        self,
        text: str,
        color: str | None = None,
        bold: bool = False,
        italic: bool = False,
    ) -> None:
        """
        Print styled text (terminal output only).

        Args:
            text: Text to print
            color: Color name (red, green, yellow, etc.)
            bold: Make bold
            italic: Make italic
        """
        if self.format in {"json", "csv", "markdown"}:
            return

        if color or bold or italic:
            click.secho(text, fg=color, bold=bold)
        else:
            click.echo(text)

    def print_section_header(self, title: str) -> None:
        """
        Print a section header.

        Args:
            title: Section title
        """
        if self.format in {"json", "csv", "markdown"}:
            return

        click.secho(f"\n{title}", fg="cyan", bold=True)


# Convenience function for quick output
def create_output_manager(
    format: str | None = None, output_file: str | None = None
) -> OutputManager:
    """
    Create an OutputManager with optional CLI arguments.

    Useful for Click commands with --format and --output options.

    Args:
        format: Output format or None (uses 'table' default)
        output_file: Path to output file or None (uses stdout)

    Returns:
        Configured OutputManager instance
    """
    return OutputManager(
        format=format or "table",
        output_file=Path(output_file) if output_file else None,
    )
