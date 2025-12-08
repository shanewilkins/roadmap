"""Table and panel builders for consistent display formatting.

This module provides reusable Rich table and panel construction patterns for entity display:
- Two-column metadata tables (Key-Value format)
- Status and progress tables
- Panel creation with standard borders and styles
- Custom table styling

Consolidates duplicated table construction logic across view.py files.
"""

from typing import Any, Optional

from rich.panel import Panel  # type: ignore[import-not-found]
from rich.table import Table  # type: ignore[import-not-found]
from rich.text import Text  # type: ignore[import-not-found]


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


def create_status_table(title: str = "Status") -> Table:
    """Create table for displaying status information.
    
    Args:
        title: Optional table title
        
    Returns:
        Rich Table configured for status display
    """
    table = Table(title=title, show_header=True, box=None, padding=(0, 2))
    table.add_column("Status", style="white", width=15)
    table.add_column("Count", style="cyan", width=10)
    return table


def create_list_table(
    columns: Optional[list[tuple[str, Optional[str], Optional[int]]]] = None,
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


def create_progress_panel(completed: int, total: int) -> Panel:
    """Create panel showing progress metrics.
    
    Args:
        completed: Number of completed items
        total: Total number of items
        
    Returns:
        Rich Panel with progress table
    """
    percentage = (completed / total * 100) if total > 0 else 0
    
    progress_table = create_metadata_table()
    progress_table.add_row("Issues Complete", f"{completed}/{total}")
    progress_table.add_row("Percentage", f"{percentage:.1f}%")
    
    border_style = "green" if percentage > 50 else "yellow"
    return Panel(
        progress_table,
        title="📊 Progress",
        border_style=border_style,
    )


# ===== Panel Creation =====


def create_panel(
    content: Any,
    title: Optional[str] = None,
    emoji: Optional[str] = None,
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


def create_info_panel(content: Any, title: str) -> Panel:
    """Create info panel (blue border).
    
    Args:
        content: Content to display
        title: Panel title
        
    Returns:
        Rich Panel with blue border
    """
    return create_panel(content, title=title, border_style="blue")


def create_success_panel(content: Any, title: str) -> Panel:
    """Create success panel (green border).
    
    Args:
        content: Content to display
        title: Panel title
        
    Returns:
        Rich Panel with green border
    """
    return create_panel(content, title=title, border_style="green")


def create_warning_panel(content: Any, title: str) -> Panel:
    """Create warning panel (yellow border).
    
    Args:
        content: Content to display
        title: Panel title
        
    Returns:
        Rich Panel with yellow border
    """
    return create_panel(content, title=title, border_style="yellow")


def create_error_panel(content: Any, title: str) -> Panel:
    """Create error panel (red border).
    
    Args:
        content: Content to display
        title: Panel title
        
    Returns:
        Rich Panel with red border
    """
    return create_panel(content, title=title, border_style="red")


# ===== Text Builders =====


def create_status_header(
    title: str,
    status: str,
    status_color: str,
    details: Optional[list[tuple[str, str]]] = None,
) -> Text:
    """Create header text with status and optional details.
    
    Args:
        title: Main title text
        status: Status value to display
        status_color: Color for status badge
        details: Optional list of (label, value) pairs to append
        
    Returns:
        Rich Text object with formatted header
    """
    header = Text()
    header.append(title, style="bold white")
    header.append("\n")
    header.append(f"[{status.upper()}]", style=f"bold {status_color}")
    
    if details:
        for label, value in details:
            header.append(" • ", style="dim")
            header.append(f"{label}: {value}", style="white")
    
    return header


def add_status_badge(text: Text, status: str, status_color: str) -> Text:
    """Add status badge to existing Text object.
    
    Args:
        text: Text object to add badge to
        status: Status value
        status_color: Color for status
        
    Returns:
        Modified Text object
    """
    text.append(f" [{status.upper()}]", style=f"bold {status_color}")
    return text


def add_detail_to_text(text: Text, label: str, value: str, style: str = "white") -> Text:
    """Add detail line to Text object.
    
    Args:
        text: Text object to add to
        label: Detail label
        value: Detail value
        style: Optional style for value
        
    Returns:
        Modified Text object
    """
    text.append(f"\n{label}: ", style="dim")
    text.append(value, style=style)
    return text
