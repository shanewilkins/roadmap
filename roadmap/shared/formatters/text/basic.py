"""Basic text formatting utilities for terminal display."""

from typing import TYPE_CHECKING, Any, Optional

import structlog
from rich.text import Text

logger = structlog.get_logger(__name__)

if TYPE_CHECKING:
    from rich.console import Console
    from rich.panel import Panel


def format_table(
    title: str,
    columns: list[str],
    rows: list[tuple],
    console_obj: Optional["Console"] = None,
) -> str:
    """
    Format data as a rich table for display.

    Args:
        title: Table title
        columns: Column headers
        rows: List of row tuples
        console_obj: Optional console instance

    Returns:
        Formatted table as string
    """
    logger.debug(
        "formatting_table", title=title, col_count=len(columns), row_count=len(rows)
    )
    try:
        from rich.console import Console
    except ImportError:
        # Fallback to simple formatting
        return _format_table_simple(title, columns, rows)

    if console_obj is None:
        from rich.console import Console

        console_obj = Console()

    from rich.table import Table

    table = Table(title=title)
    for col in columns:
        table.add_column(col)

    for row in rows:
        table.add_row(*[str(cell) for cell in row])

    return str(table)


def _format_table_simple(title: str, columns: list[str], rows: list[tuple]) -> str:
    """Fallback simple table formatting without rich."""
    logger.debug(
        "formatting_table_simple",
        title=title,
        col_count=len(columns),
        row_count=len(rows),
    )
    output = [f"\n{title}", "-" * len(title)]
    output.append(" | ".join(columns))
    output.append("-" * (sum(len(c) for c in columns) + len(columns) * 3 - 1))
    for row in rows:
        output.append(" | ".join(str(cell) for cell in row))
    return "\n".join(output)


def format_panel(
    content: str,
    title: str | None = None,
    expand: bool = False,
) -> "Panel":
    """
    Format content in a rich panel.

    Args:
        content: Panel content
        title: Optional panel title
        expand: Whether to expand to console width

    Returns:
        Rich Panel object
    """
    logger.debug(
        "formatting_panel", title=title, expand=expand, content_length=len(content)
    )
    from rich.panel import Panel

    return Panel(content, title=title, expand=expand)


def format_header(text: str, level: int = 1) -> Text:
    """
    Format text as a header with styling.

    Args:
        text: Header text
        level: Header level (1-3, controls styling)

    Returns:
        Styled Text object
    """
    logger.debug("formatting_header", text=text, level=level)
    if level == 1:
        return Text(text, style="bold cyan", justify="center")
    elif level == 2:
        return Text(text, style="bold blue")
    else:
        return Text(text, style="bold")


def format_success(text: str) -> Text:
    """Format text as a success message."""
    logger.debug("formatting_success", text=text)
    return Text(text, style="bold green")


def format_error(text: str) -> Text:
    """Format text as an error message."""
    logger.debug("formatting_error", text=text)
    return Text(text, style="bold red")


def format_warning(text: str) -> Text:
    """Format text as a warning message."""
    logger.debug("formatting_warning", text=text)
    return Text(text, style="bold yellow")


def format_info(text: str) -> Text:
    """Format text as info message."""
    logger.debug("formatting_info", text=text)
    return Text(text, style="bold cyan")


def format_list(items: list[str], title: str | None = None) -> str:
    """
    Format items as a bulleted list.

    Args:
        items: List of items to format
        title: Optional list title

    Returns:
        Formatted list as string
    """
    logger.debug("formatting_list", item_count=len(items), title=title)
    output = []
    if title:
        output.append(f"[bold]{title}[/bold]")
    for item in items:
        output.append(f"  • {item}")
    return "\n".join(output)


def format_key_value_pairs(pairs: dict[str, Any], title: str | None = None) -> str:
    """
    Format key-value pairs for display.

    Args:
        pairs: Dictionary of key-value pairs
        title: Optional title

    Returns:
        Formatted output as string
    """
    logger.debug("formatting_key_value_pairs", pair_count=len(pairs), title=title)
    output = []
    if title:
        output.append(f"[bold]{title}[/bold]")

    max_key_length = max(len(k) for k in pairs.keys()) if pairs else 0
    for key, value in pairs.items():
        output.append(f"  {key.ljust(max_key_length)}: {value}")

    return "\n".join(output)


def truncate_text(text: str, max_length: int = 50, suffix: str = "...") -> str:
    """
    Truncate text to maximum length with optional suffix.

    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add if truncated

    Returns:
        Truncated text
    """
    logger.debug(
        "truncating_text",
        text_length=len(text),
        max_length=max_length,
        was_truncated=len(text) > max_length,
    )
    if len(text) <= max_length:
        return text
    return text[: max_length - len(suffix)] + suffix


def format_json(data: Any, indent: int = 2) -> str:
    """
    Format data as JSON.

    Args:
        data: Data to format
        indent: JSON indentation level

    Returns:
        Formatted JSON string
    """
    logger.debug("formatting_json", data_type=type(data).__name__, indent=indent)
    import json

    return json.dumps(data, indent=indent, default=str)
