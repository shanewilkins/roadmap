"""Display formatting utilities for lists and panels."""

from typing import Any


def format_display_list(items: list[str], title: str | None = None) -> str:
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


def format_display_pairs(pairs: dict[str, Any], title: str | None = None) -> str:
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
