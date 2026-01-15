"""
Output formatter - Renders TableData in multiple formats.

Supports Rich (interactive), plain-text (POSIX), JSON (machine-readable), and CSV (data analysis).
"""

import csv
import json
from datetime import UTC
from io import StringIO
from typing import Any

from rich.table import Table  # type: ignore[import-not-found]

from roadmap.common.models import TableData


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
        table = Table(
            title=self.table.title, show_header=True, box=None, padding=(0, 1)
        )

        # Add columns
        for col in self.table.active_columns:
            kwargs: dict[str, Any] = (
                {"style": col.display_style} if col.display_style else {}
            )
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

    def to_html(self) -> str:
        """
        Format as HTML table with styling.

        Returns:
            HTML table suitable for email, web, or documentation.
            Includes basic CSS styling for readability.

        Note:
            Generates self-contained HTML with embedded CSS.
            Suitable for email clients and web browsers.
        """
        if not self.table.active_columns or not self.table.active_rows:
            return ""

        columns = self.table.active_columns

        # Build HTML with embedded CSS
        html_lines = [
            "<!DOCTYPE html>",
            "<html>",
            "<head>",
            "<meta charset='utf-8'>",
            "<meta name='viewport' content='width=device-width, initial-scale=1'>",
            "<style>",
            "  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }",
            "  .container { max-width: 100%; background-color: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }",
            "  h1 { color: #333; margin-bottom: 20px; font-size: 24px; }",
            "  table { width: 100%; border-collapse: collapse; margin-top: 10px; }",
            "  thead { background-color: #2c3e50; color: white; }",
            "  th { padding: 12px; text-align: left; font-weight: 600; border: 1px solid #ddd; }",
            "  td { padding: 10px 12px; border: 1px solid #ddd; }",
            "  tbody tr:nth-child(odd) { background-color: #f9f9f9; }",
            "  tbody tr:hover { background-color: #f0f0f0; }",
            "  .footer { margin-top: 20px; font-size: 12px; color: #666; text-align: right; }",
            "</style>",
            "</head>",
            "<body>",
            "<div class='container'>",
        ]

        # Add title
        if self.table.title:
            html_lines.append(f"<h1>{self._escape_html(self.table.title)}</h1>")

        # Start table
        html_lines.append("<table>")

        # Header row
        html_lines.append("<thead>")
        html_lines.append("<tr>")
        for col in columns:
            html_lines.append(f"<th>{self._escape_html(col.display_name)}</th>")
        html_lines.append("</tr>")
        html_lines.append("</thead>")

        # Data rows
        html_lines.append("<tbody>")
        for row in self.table.active_rows:
            html_lines.append("<tr>")
            for cell in row:
                cell_value = self._escape_html(str(cell) if cell is not None else "")
                html_lines.append(f"<td>{cell_value}</td>")
            html_lines.append("</tr>")
        html_lines.append("</tbody>")

        # Close table
        html_lines.append("</table>")

        # Footer with timestamp
        from datetime import datetime

        now = datetime.now(UTC).isoformat()
        html_lines.append(f"<p class='footer'>Generated {now}</p>")

        # Close HTML
        html_lines.append("</div>")
        html_lines.append("</body>")
        html_lines.append("</html>")

        return "\n".join(html_lines)

    @staticmethod
    def _escape_html(text: str) -> str:
        """Escape HTML special characters."""
        return (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#39;")
        )


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


class HTMLOutputFormatter:
    """
    Specialized formatter for HTML output (web/email).

    Used by CLI when --html flag is set or ROADMAP_OUTPUT_FORMAT=html.
    Generates self-contained HTML with embedded CSS for email clients and browsers.
    """

    def __init__(self, table_data: TableData):
        """Initialize with table data."""
        self.formatter = OutputFormatter(table_data)

    def format(self) -> str:
        """Format output as HTML."""
        return self.formatter.to_html()
