"""Output formatting utilities for CLI display."""

from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from rich.console import Console
    from rich.panel import Panel
    from rich.text import Text


def format_table(
    title: str,
    columns: list[str],
    rows: list[tuple],
    console: Optional["Console"] = None,
) -> str:
    """
    Format data as a rich table for display.

    Args:
        title: Table title
        columns: Column headers
        rows: List of row tuples
        console: Optional console instance

    Returns:
        Formatted table as string
    """
    try:
        from rich.table import Table
    except ImportError:
        # Fallback to simple formatting
        return _format_table_simple(title, columns, rows)

    if console is None:
        from rich.console import Console

        console = Console()

    table = Table(title=title)
    for col in columns:
        table.add_column(col)

    for row in rows:
        table.add_row(*[str(cell) for cell in row])

    return str(table)


def _format_table_simple(title: str, columns: list[str], rows: list[tuple]) -> str:
    """Fallback simple table formatting without rich."""
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
    from rich.panel import Panel

    return Panel(content, title=title, expand=expand)


def format_header(text: str, level: int = 1) -> "Text":
    """
    Format text as a header with styling.

    Args:
        text: Header text
        level: Header level (1-3, controls styling)

    Returns:
        Styled Text object
    """
    from rich.text import Text

    if level == 1:
        return Text(text, style="bold cyan", justify="center")
    elif level == 2:
        return Text(text, style="bold blue")
    else:
        return Text(text, style="bold")


def format_success(text: str) -> "Text":
    """Format text as a success message."""
    from rich.text import Text

    return Text(text, style="bold green")


def format_error(text: str) -> "Text":
    """Format text as an error message."""
    from rich.text import Text

    return Text(text, style="bold red")


def format_warning(text: str) -> "Text":
    """Format text as a warning message."""
    from rich.text import Text

    return Text(text, style="bold yellow")


def format_info(text: str) -> "Text":
    """Format text as info message."""
    from rich.text import Text

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
    output = []
    if title:
        output.append(f"[bold]{title}[/bold]")

    max_key_length = max(len(k) for k in pairs.keys()) if pairs else 0
    for key, value in pairs.items():
        output.append(f"  {key.ljust(max_key_length)}: {value}")

    return "\n".join(output)


def format_status_badge(status: str) -> "Text":
    """
    Format a status as a colored badge.

    Args:
        status: Status value

    Returns:
        Styled Text badge
    """
    from rich.text import Text

    status_lower = str(status).lower()

    # Map status values to colors
    status_colors = {
        "closed": "bold green",
        "in-progress": "bold blue",
        "in_progress": "bold blue",
        "todo": "bold yellow",
        "blocked": "bold red",
        "review": "bold magenta",
        "open": "bold green",
        "active": "bold green",
        "on-hold": "bold yellow",
        "on_hold": "bold yellow",
        "planning": "bold blue",
        "completed": "bold green",
        "cancelled": "bold red",
        "critical": "bold red",
        "high": "bold yellow",
        "medium": "bold blue",
        "low": "bold green",
    }

    style = status_colors.get(status_lower, "white")
    return Text(f"[{status}]", style=style)


def format_percentage(value: float, decimals: int = 1) -> str:
    """
    Format a numeric value as a percentage.

    Args:
        value: Decimal value (0.0-1.0 or 0-100)
        decimals: Number of decimal places

    Returns:
        Formatted percentage string
    """
    if value <= 1.0:
        value = value * 100
    return f"{value:.{decimals}f}%"


def format_duration(seconds: float) -> str:
    """
    Format duration in seconds to human-readable format.

    Args:
        seconds: Duration in seconds

    Returns:
        Formatted duration string
    """
    if seconds < 60:
        return f"{int(seconds)}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}m"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}h"


def format_count(count: int, singular: str, plural: str | None = None) -> str:
    """
    Format a count with proper singular/plural form.

    Args:
        count: The count
        singular: Singular form
        plural: Plural form (defaults to singular + 's')

    Returns:
        Formatted count string
    """
    if plural is None:
        plural = f"{singular}s"
    return f"{count} {singular if count == 1 else plural}"


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
    import json

    return json.dumps(data, indent=indent, default=str)


# Operation Display Formatters
# These format operation success/failure messages consistently across CLI commands


def format_operation_success(
    emoji: str,
    action: str,
    entity_title: str | None = None,
    entity_id: str | None = None,
    reason: str | None = None,
    extra_details: dict[str, str] | None = None,
) -> list[str]:
    """
    Format a successful operation message with consistent styling.

    Returns a list of formatted lines for console output.

    Args:
        emoji: Emoji to display (e.g., "✅", "🚫", "📊")
        action: Action verb (e.g., "Blocked", "Closed", "Updated")
        entity_title: Title/name of the entity affected (e.g., issue title)
        entity_id: ID of the entity (displayed separately as cyan)
        reason: Optional reason for the operation
        extra_details: Optional dict of additional details to display

    Returns:
        List of formatted output lines
    """
    lines = []

    # Main success line: emoji + action + title
    if entity_title:
        lines.append(f"{emoji} {action} issue: {entity_title}")
    else:
        lines.append(f"{emoji} {action}")

    # Entity ID line (if provided)
    if entity_id:
        lines.append(f"   ID: {entity_id}")

    # Reason line (if provided)
    if reason:
        lines.append(f"   Reason: {reason}")

    # Extra details (if provided)
    if extra_details:
        for key, value in extra_details.items():
            lines.append(f"   {key}: {value}")

    return lines


def format_operation_failure(
    action: str,
    entity_id: str | None = None,
    error: str | None = None,
    suggestion: str | None = None,
) -> list[str]:
    """
    Format a failed operation message with consistent styling.

    Returns a list of formatted lines for console output.

    Args:
        action: Action that failed (e.g., "block", "close", "update")
        entity_id: ID of the entity that failed (optional)
        error: Error message/reason for failure
        suggestion: Suggested recovery action

    Returns:
        List of formatted output lines
    """
    lines = []

    # Main failure line
    if entity_id:
        lines.append(f"❌ Failed to {action} issue: {entity_id}")
    else:
        lines.append(f"❌ Failed to {action}")

    # Error details (if provided)
    if error:
        lines.append(f"   Error: {error}")

    # Suggestion (if provided)
    if suggestion:
        lines.append(f"   💡 {suggestion}")

    return lines


def format_entity_details(
    entity_id: str,
    entity_title: str | None = None,
    entity_type: str = "item",
    status: str | None = None,
    details: dict[str, str] | None = None,
) -> list[str]:
    """
    Format entity details for consistent display across commands.

    Args:
        entity_id: ID of the entity
        entity_title: Title/name of the entity
        entity_type: Type of entity (e.g., "issue", "milestone")
        status: Current status of entity
        details: Additional details dict

    Returns:
        List of formatted output lines
    """
    lines = []

    # ID and title
    if entity_title:
        lines.append(f"📋 {entity_type.title()}: {entity_title}")
    lines.append(f"   ID: {entity_id}")

    # Status
    if status:
        lines.append(f"   Status: {status}")

    # Additional details
    if details:
        for key, value in details.items():
            lines.append(f"   {key}: {value}")

    return lines


def format_list_items(
    items: list[dict[str, str]],
    show_count: int | None = None,
    more_suffix: str = "... and {count} more",
) -> list[str]:
    """
    Format a list of items consistently.

    Args:
        items: List of dicts with 'id' and 'title' keys minimum
        show_count: Maximum items to show (None = show all)
        more_suffix: Format string for "... and X more" suffix

    Returns:
        List of formatted output lines
    """
    lines = []

    # Determine how many to show
    items_to_show = items
    remaining = 0
    if show_count and len(items) > show_count:
        items_to_show = items[:show_count]
        remaining = len(items) - show_count

    # Format each item
    for item in items_to_show:
        item_id = item.get("id", "")[:8]  # Show first 8 chars of ID
        title = item.get("title", "")
        lines.append(f"   • {item_id} - {title}")

    # Add "... and X more" if truncated
    if remaining > 0:
        lines.append(more_suffix.format(count=remaining))

    return lines
