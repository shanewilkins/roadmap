"""Table and panel builders for consistent display formatting.

This module provides reusable Rich table and panel construction patterns for entity display:
- Two-column metadata tables (Key-Value format)
- Status and progress tables
- Panel creation with standard borders and styles
- Custom table styling

Consolidates duplicated table construction logic across view.py files.
"""

from typing import Any

from rich.panel import Panel  # type: ignore[import-not-found]
from rich.table import Table  # type: ignore[import-not-found]

# ===== Generic Table Builders =====


def create_metadata_table() -> Table:
    """Create standard 2-column metadata table (Key-Value format).

    Returns:
        Rich Table configured with standard metadata layout
    """
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Key", style="dim")
    table.add_column("Value")
    return table


def create_list_table(
    columns: list[tuple[str, str | None, int | None]] | None = None,
) -> Table:
    """Create table for list display with custom columns.

    Args:
        columns: List of (name, style, width) tuples for columns.
                 If None, creates basic 2-column table.

    Returns:
        Rich Table configured for list display
    """
    table = Table(show_header=True, box=None, padding=(0, 1))

    if columns is None:
        table.add_column("ID", style="cyan", width=9)
        table.add_column("Title", style="white")
    else:
        for col_name, col_style, col_width in columns:
            kwargs: dict[str, Any] = {}
            if col_style:
                kwargs["style"] = col_style
            if col_width:
                kwargs["width"] = col_width
            table.add_column(col_name, **kwargs)

    return table


# ===== Progress Display =====


# ===== Panel Creation =====


def create_panel(
    content: Any,
    title: str | None = None,
    emoji: str | None = None,
    border_style: str = "white",
) -> Panel:
    """Create standard panel with configurable title and border.

    Args:
        content: Content to display in panel (Table, Text, Markdown, etc.)
        title: Optional panel title
        emoji: Optional emoji to prepend to title
        border_style: Border color (default: white)

    Returns:
        Rich Panel
    """
    full_title = None
    if title:
        full_title = f"{emoji} {title}" if emoji else title

    return Panel(
        content,
        title=full_title,
        border_style=border_style,
    )


# ===== Text Builders =====
