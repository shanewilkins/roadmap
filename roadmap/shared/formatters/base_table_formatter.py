"""Base table formatter for DRY consolidation.

This module provides abstract base class for all table formatters,
eliminating duplicate code across Issue, Project, and Milestone formatters.
"""

from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

from roadmap.common.console import get_console
from roadmap.common.models import TableData

# Generic type for domain models
T = TypeVar("T")


class BaseTableFormatter(ABC, Generic[T]):
    """Abstract base class for table formatters."""

    def __init__(self):
        """Initialize base formatter."""
        pass

    @property
    def console(self):
        """Get console instance dynamically for test compatibility."""
        return get_console()

    @abstractmethod
    def create_table(self) -> Any:
        """Create and configure the rich Table for this formatter.

        Returns:
            Configured Rich Table with columns
        """
        pass

    @abstractmethod
    def add_row(self, table: Any, item: T) -> None:
        """Add a single item row to the table.

        Args:
            table: The Rich Table to add row to
            item: The domain object to format
        """
        pass

    @abstractmethod
    def get_filter_description(self, items: list[T]) -> str:
        """Get human-readable description of filtered items.

        Args:
            items: List of items being displayed

        Returns:
            Description string (e.g., "2 open issue")
        """
        pass

    def display_items(self, items: list[T], filter_description: str = "all") -> None:
        """Display items in a formatted table.

        Args:
            items: List of items to display
            filter_description: Human-readable filter description
        """
        if not items:
            self.console.print(
                f"📋 No {filter_description} items found.", style="yellow"
            )
            self.console.print(
                "Create one with: roadmap [command] create '[Name]'",
                style="dim",
            )
            return

        # Display header with filter info
        filter_desc = self.get_filter_description(items)
        self.console.print(f"📋 {filter_desc}", style="bold cyan")
        self.console.print()

        # Create and populate table
        table = self.create_table()
        for item in items:
            self.add_row(table, item)

        self.console.print(table)

    @abstractmethod
    def items_to_table_data(
        self, items: list[T], title: str = "Items", description: str = ""
    ) -> TableData:
        """Convert items to TableData for structured output.

        Args:
            items: List of items to convert
            title: Table title
            description: Optional description

        Returns:
            TableData object for rendering in any format
        """
        pass
