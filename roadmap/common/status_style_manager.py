"""Centralized status styling for consistent UI across application.

This module consolidates all status-to-style mappings to eliminate DRY violations
and ensure consistent status rendering everywhere.
"""

from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass


class StatusStyle(Enum):
    """Enum for common status values."""

    TODO = "TODO"
    IN_PROGRESS = "IN_PROGRESS"
    BLOCKED = "BLOCKED"
    REVIEW = "REVIEW"
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    COMPLETED = "COMPLETED"
    ARCHIVED = "ARCHIVED"


class StatusStyleManager:
    """Centralized manager for status styling across application."""

    # Rich style mappings for status values
    STATUS_STYLES: dict[str, str] = {
        # Issue/Task statuses
        "TODO": "white",
        "IN_PROGRESS": "yellow",
        "BLOCKED": "red",
        "REVIEW": "blue",
        "CLOSED": "green",
        # Project/Milestone statuses
        "OPEN": "cyan",
        "COMPLETED": "green",
        "ARCHIVED": "dim",
    }

    # Emoji mapping for status
    STATUS_EMOJIS: dict[str, str] = {
        "TODO": "📝",
        "IN_PROGRESS": "🔄",
        "BLOCKED": "🚫",
        "REVIEW": "👀",
        "CLOSED": "✅",
        "OPEN": "📂",
        "COMPLETED": "🎉",
        "ARCHIVED": "📦",
    }

    @classmethod
    def get_style(cls, status: str | Enum) -> str:
        """Get Rich style string for a status.

        Args:
            status: Status value (string or Enum)

        Returns:
            Rich style string (e.g., "bold red")
        """
        status_str = status.value if isinstance(status, Enum) else str(status).upper()
        return cls.STATUS_STYLES.get(status_str, "white")

    @classmethod
    def get_emoji(cls, status: str | Enum) -> str:
        """Get emoji for a status.

        Args:
            status: Status value (string or Enum)

        Returns:
            Emoji character
        """
        status_str = status.value if isinstance(status, Enum) else str(status).upper()
        return cls.STATUS_EMOJIS.get(status_str, "•")

    @classmethod
    def get_rich_text(cls, status: str | Enum, text: str | None = None) -> Any:
        """Create Rich Text object with proper style and emoji.

        Args:
            status: Status value
            text: Optional custom text (defaults to status string)

        Returns:
            Rich Text object ready for rendering
        """
        from rich.text import Text

        display_text = text or str(status)
        return Text(display_text, style=cls.get_style(status))

    @classmethod
    def all_styles(cls) -> dict[str, str]:
        """Get all available status styles.

        Returns:
            Dictionary mapping status -> style
        """
        return cls.STATUS_STYLES.copy()

    @classmethod
    def all_emojis(cls) -> dict[str, str]:
        """Get all available status emojis.

        Returns:
            Dictionary mapping status -> emoji
        """
        return cls.STATUS_EMOJIS.copy()
