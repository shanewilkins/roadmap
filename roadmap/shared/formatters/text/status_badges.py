"""Status badge and percentage formatting."""

from rich.text import Text


def format_status_badge(status: str) -> Text:
    """
    Format a status as a colored badge.

    Args:
        status: Status value

    Returns:
        Styled Text badge
    """
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


__all__ = ["format_status_badge", "format_percentage"]
