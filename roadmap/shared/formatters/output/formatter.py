"""Generic TableData output formatter for multiple formats."""

import csv
import json
from io import StringIO
from typing import TYPE_CHECKING

import structlog
from rich.table import Table

from roadmap.common.output_models import TableData

logger = structlog.get_logger(__name__)

if TYPE_CHECKING:
    pass


class OutputFormatter:
    """
    Format TableData for different output modes.

    Renders the same TableData in multiple formats:
    - Rich: Interactive terminal with colors and styling
    - Plain-text: POSIX-compliant ASCII output (no ANSI codes)
    - JSON: Machine-readable structured data
    - CSV: Tabular data for analysis/import

    Example:
        table = TableData(...)
        formatter = OutputFormatter(table)
        print(formatter.to_json())         # JSON export
        console.print(formatter.to_rich()) # Interactive display
    """

    # Emoji to plain-text mappings for POSIX mode
    EMOJI_MAP = {
        "✅": "[OK]",
        "❌": "[ERROR]",
        "⚠️": "[WARN]",
        "⚙️": "[CONFIG]",
        "📋": "[INFO]",
        "🆔": "[ID]",
        "📊": "[STAT]",
        "🌿": "[BRANCH]",
        "🔗": "[LINK]",
        "💬": "[COMMENT]",
        "📍": "[LOCATION]",
        "🔄": "[SYNC]",
        "🔍": "[SEARCH]",
        "✏️": "[EDIT]",
        "🗑️": "[DELETE]",
        "📁": "[FOLDER]",
        "📈": "[UP]",
        "📉": "[DOWN]",
        "⏸️": "[PAUSE]",
        "▶️": "[PLAY]",
        "⏹️": "[STOP]",
    }

    def __init__(self, table_data: TableData):
        """
        Initialize formatter with table data.

        Args:
            table_data: TableData object to format.
        """
        logger.debug(
            "initializing_output_formatter",
            row_count=len(table_data.active_rows),
            col_count=len(table_data.active_columns),
        )
        self.table = table_data

    def to_rich(self) -> Table:
        """
        Format as Rich table with colors and styling.

        Returns:
            Rich Table object suitable for console.print().

        Note:
            This returns a Rich Table object, not a string. Use with:
            console.print(formatter.to_rich())
        """
        logger.debug(
            "formatting_to_rich",
            rows=len(self.table.active_rows),
            cols=len(self.table.active_columns),
        )
        table = Table(
            title=self.table.title, show_header=True, box=None, padding=(0, 1)
        )

        # Add columns
        for col in self.table.active_columns:
            kwargs = {"style": col.display_style} if col.display_style else {}
            if col.width:
                kwargs["width"] = col.width
            table.add_column(col.display_name, **kwargs)

        # Add rows
        for row in self.table.active_rows:
            table.add_row(*[str(v) if v is not None else "-" for v in row])

        return table

    def to_plain_text(self) -> str:
        """
        Format as plain ASCII text (POSIX-compliant).

        Returns:
            String containing POSIX-safe table output.

        Features:
            - No ANSI color codes
            - No Unicode emoji (replaced with ASCII equivalents)
            - ASCII table borders (pipes and dashes)
            - Fixed-width columns
            - No Rich styling
        """
        logger.debug(
            "formatting_to_plain_text",
            rows=len(self.table.active_rows),
            cols=len(self.table.active_columns),
        )
        if not self.table.active_columns or not self.table.active_rows:
            return ""

        # Build header
        columns = self.table.active_columns
        lines = []

        # Add title if present
        if self.table.title:
            lines.append(self.table.title)
            lines.append("")

        # Calculate column widths
        col_widths = []
        for i, col in enumerate(columns):
            # Width is max of header and data
            header_width = len(col.display_name)
            max_data_width = max(
                (
                    len(str(row[i]) if row[i] is not None else "-")
                    for row in self.table.active_rows
                ),
                default=0,
            )
            width = max(header_width, max_data_width, col.width or 0)
            col_widths.append(width)

        # Build header row
        header_cells = [
            col.display_name.ljust(width)
            for col, width in zip(columns, col_widths, strict=False)
        ]
        header = " | ".join(header_cells)
        lines.append(header)

        # Build separator
        separator = "-+-".join("-" * width for width in col_widths)
        lines.append(separator)

        # Build data rows
        for row in self.table.active_rows:
            cells = []
            for _i, (value, width) in enumerate(zip(row, col_widths, strict=False)):
                str_val = str(value) if value is not None else "-"
                # Replace emoji with ASCII equivalents
                for emoji, replacement in self.EMOJI_MAP.items():
                    str_val = str_val.replace(emoji, replacement)
                cells.append(str_val.ljust(width))
            lines.append(" | ".join(cells))

        return "\n".join(lines)

    def to_json(self) -> str:
        """
        Format as JSON (machine-readable).

        Returns:
            JSON string containing table data and metadata.

        Format:
            {
                "title": "...",
                "columns": [{...}, ...],
                "rows": [[...], ...],
                "metadata": {...}
            }
        """
        logger.debug(
            "formatting_to_json",
            rows=len(self.table.active_rows),
            cols=len(self.table.active_columns),
        )
        data = self.table.to_dict()
        return json.dumps(data, indent=2, default=str)

    def to_csv(self) -> str:
        """
        Format as CSV (RFC 4180 compliant).

        Returns:
            CSV string suitable for import to Excel/Sheets.

        Features:
            - Standard CSV format (RFC 4180)
            - Proper escaping of special characters
            - Headers from display_name
            - All values as strings
        """
        logger.debug(
            "formatting_to_csv",
            rows=len(self.table.active_rows),
            cols=len(self.table.active_columns),
        )
        if not self.table.active_columns or not self.table.active_rows:
            return ""

        output = StringIO()
        columns = self.table.active_columns

        # Write header
        writer = csv.writer(output)
        writer.writerow([col.display_name for col in columns])

        # Write data rows
        for row in self.table.active_rows:
            writer.writerow([str(v) if v is not None else "" for v in row])

        return output.getvalue()

    def to_markdown(self) -> str:
        """
        Format as Markdown table.

        Returns:
            Markdown table syntax suitable for README/docs.

        Note:
            This is a bonus format not required by spec. Useful for documentation.
        """
        logger.debug(
            "formatting_to_markdown",
            rows=len(self.table.active_rows),
            cols=len(self.table.active_columns),
        )
        if not self.table.active_columns or not self.table.active_rows:
            return ""

        columns = self.table.active_columns
        lines = []

        # Add title if present
        if self.table.title:
            lines.append(f"## {self.table.title}\n")

        # Header
        header_cells = [col.display_name for col in columns]
        lines.append("| " + " | ".join(header_cells) + " |")

        # Separator
        separators = ["-" * max(len(col.display_name), 3) for col in columns]
        lines.append("|" + "|".join(["-" * (len(sep) + 2) for sep in separators]) + "|")

        # Data rows
        for row in self.table.active_rows:
            cells = [str(v) if v is not None else "" for v in row]
            lines.append("| " + " | ".join(cells) + " |")

        return "\n".join(lines)


class PlainTextOutputFormatter:
    """
    Specialized formatter for plain-text output with emoji replacement.

    Used by CLI when ROADMAP_OUTPUT_FORMAT=plain or --plain-text flag is set.
    Ensures all output is POSIX-compliant (no ANSI codes, ASCII emoji).
    """

    def __init__(self, table_data: TableData):
        """Initialize with table data."""
        self.formatter = OutputFormatter(table_data)

    def format(self) -> str:
        """Format output in plain-text mode."""
        return self.formatter.to_plain_text()


class JSONOutputFormatter:
    """
    Specialized formatter for JSON output (machine-readable).

    Used by CLI when --json flag is set or ROADMAP_OUTPUT_FORMAT=json.
    Ensures valid JSON output for tool integration.
    """

    def __init__(self, table_data: TableData):
        """Initialize with table data."""
        self.formatter = OutputFormatter(table_data)

    def format(self) -> str:
        """Format output as JSON."""
        return self.formatter.to_json()


class CSVOutputFormatter:
    """
    Specialized formatter for CSV output (data analysis).

    Used by CLI when --csv flag is set or ROADMAP_OUTPUT_FORMAT=csv.
    Ensures RFC 4180 compliant CSV output.
    """

    def __init__(self, table_data: TableData):
        """Initialize with table data."""
        self.formatter = OutputFormatter(table_data)

    def format(self) -> str:
        """Format output as CSV."""
        return self.formatter.to_csv()
