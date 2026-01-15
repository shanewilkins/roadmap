"""Smart table layout system with responsive formatting.

Automatically detects terminal width and switches to vertical layout
when horizontal table is too wide.
"""

import shutil
from dataclasses import dataclass

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from roadmap.common.models import TableData


@dataclass
class LayoutConfig:
    """Configuration for smart table layouts."""

    min_column_width: int = 15
    max_horizontal_width: int = 120
    vertical_threshold: float = (
        0.8  # Switch to vertical if table > 80% of terminal width
    )
    responsive_enabled: bool = True


class SmartTableLayout:
    """Renders tables with responsive layout based on terminal width."""

    def __init__(self, config: LayoutConfig | None = None):
        """Initialize layout system.

        Args:
            config: Layout configuration
        """
        self.config = config or LayoutConfig()

    def get_terminal_width(self) -> int:
        """Get terminal width in columns.

        Returns:
            Terminal width, defaults to 80 if unable to detect
        """
        try:
            width = shutil.get_terminal_size().columns
            return max(width, 40)  # Minimum 40 columns
        except Exception:
            return 80  # Default fallback

    def calculate_table_width(self, table_data: TableData) -> int:
        """Calculate estimated table width based on column headers and data.

        Args:
            table_data: Table data to measure

        Returns:
            Estimated table width in columns
        """
        if not table_data.columns or not table_data.rows:
            return 20

        # Estimate based on column headers and sample data
        total_width = 0
        max_samples = min(5, len(table_data.rows))

        for i, column in enumerate(table_data.columns):
            # Start with header width
            col_width = len(column.display_name) + 2

            # Check sample data for this column
            for row_idx in range(max_samples):
                if row_idx < len(table_data.rows) and i < len(table_data.rows[row_idx]):
                    value = table_data.rows[row_idx][i]
                    col_width = max(col_width, len(str(value)))

            # Add padding and separators
            col_width = min(col_width + 2, 30)  # Cap at 30 per column
            total_width += col_width

        # Add separators and padding
        total_width += len(table_data.columns) + 4

        return total_width

    def should_use_vertical_layout(self, table_data: TableData) -> bool:
        """Determine if vertical layout should be used.

        Args:
            table_data: Table data to evaluate

        Returns:
            True if vertical layout is recommended
        """
        if not self.config.responsive_enabled:
            return False

        terminal_width = self.get_terminal_width()
        table_width = self.calculate_table_width(table_data)

        # Use vertical if table would take > threshold of terminal width
        return table_width > (terminal_width * self.config.vertical_threshold)

    def render_horizontal(self, table_data: TableData) -> Table:
        """Render table in horizontal layout.

        Args:
            table_data: Table data to render

        Returns:
            Rich Table object
        """
        table = Table(
            title=table_data.title,
            show_header=True,
            header_style="bold cyan",
        )

        # Add columns
        for column in table_data.columns:
            table.add_column(column.display_name, style=column.display_style or "")

        # Add rows
        for row in table_data.rows:
            values = [str(val) if val is not None else "" for val in row]
            table.add_row(*values)

        return table

    def render_vertical(self, table_data: TableData) -> Panel:
        """Render table in vertical layout (one field per line).

        Args:
            table_data: Table data to render

        Returns:
            Rich Panel with vertical layout
        """
        from rich.text import Text

        panels_content = []

        for row_idx, row in enumerate(table_data.rows):
            # Create header for this row
            row_header = f"Entry {row_idx + 1}"

            # Build content for this row
            row_text = Text()
            row_text.append(row_header + "\n", style="bold cyan")

            for col_idx, column in enumerate(table_data.columns):
                value = row[col_idx] if col_idx < len(row) else ""
                row_text.append(f"  {column.display_name}: ", style="bold")
                row_text.append(f"{value}\n")

            panels_content.append(row_text)

        # Combine all panels
        combined = Text()
        for i, text in enumerate(panels_content):
            combined.append(text)
            if i < len(panels_content) - 1:
                combined.append("\n" + "─" * 40 + "\n\n")

        return Panel(
            combined,
            title=table_data.title,
            expand=False,
        )

    def render(self, table_data: TableData) -> Table | Panel:
        """Render table with appropriate layout based on terminal width.

        Args:
            table_data: Table data to render

        Returns:
            Rich Table or Panel object
        """
        if self.should_use_vertical_layout(table_data):
            return self.render_vertical(table_data)
        else:
            return self.render_horizontal(table_data)

    def render_as_string(self, table_data: TableData, width: int | None = None) -> str:
        """Render table to string representation.

        Useful for testing and non-interactive environments.

        Args:
            table_data: Table data to render
            width: Override terminal width

        Returns:
            String representation of table
        """
        # Temporarily override terminal width for testing
        original_get_width = self.get_terminal_width
        if width is not None:
            self.get_terminal_width = lambda: width

        try:
            renderable = self.render(table_data)
            from io import StringIO

            string_io = StringIO()
            temp_console = Console(file=string_io)
            temp_console.print(renderable)
            return string_io.getvalue()
        finally:
            self.get_terminal_width = original_get_width
