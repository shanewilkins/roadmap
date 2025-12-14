"""Milestone table formatting and display."""

from typing import TYPE_CHECKING, Any

from rich.text import Text

from roadmap.common.console import get_console
from roadmap.common.output_models import ColumnDef, ColumnType, TableData
from roadmap.shared.formatters.base_table_formatter import BaseTableFormatter

if TYPE_CHECKING:
    pass


def _get_console():
    """Get a fresh console instance for test compatibility."""
    return get_console()


class MilestoneTableFormatter(BaseTableFormatter):
    """Formats milestones for display and structured output."""

    def __init__(self):
        """Initialize milestone formatter with headers and columns."""
        super().__init__()
        self.columns_config = [
            {"name": "Milestone", "style": "cyan", "width": 20},
            {"name": "Description", "style": "white", "width": 30},
            {"name": "Status", "style": "green", "width": 10},
            {"name": "Due Date", "style": "yellow", "width": 12},
            {"name": "Progress", "style": "blue", "width": 12},
        ]

    def create_table(self) -> Any:
        """Create a rich table with milestone columns."""
        from rich.table import Table

        table = Table(show_header=True, header_style="bold magenta")
        for col in self.columns_config:
            table.add_column(col["name"], style=col["style"], width=col["width"])
        return table

    def add_row(self, table: Any, item) -> None:
        """Add a single milestone row to the table.

        Args:
            table: Rich Table object
            item: Milestone object to add
        """
        progress = ""
        if hasattr(item, "calculated_progress") and item.calculated_progress:
            progress = f"{item.calculated_progress:.0f}%"

        due_date_str = ""
        if hasattr(item, "due_date") and item.due_date:
            due_date_str = item.due_date.strftime("%Y-%m-%d")

        status_value = (
            item.status.value if hasattr(item.status, "value") else str(item.status)
        )

        table.add_row(
            Text(item.name, style="cyan"),
            Text(item.description or "", style="white"),
            Text(status_value, style="green"),
            Text(due_date_str, style="yellow"),
            Text(progress, style="blue"),
        )

    def get_filter_description(self, items: list) -> str:
        """Get human-readable description of filtered milestones.

        Args:
            items: List of milestones being displayed

        Returns:
            Description string (e.g., "5 open milestones")
        """
        count = len(items)
        return f"🏁 {count} milestone{'s' if count != 1 else ''}"

    def display_items(self, items: list, filter_description: str = "all") -> None:
        """Display milestones in a formatted table.

        Args:
            items: List of milestone objects
            filter_description: Description of filter applied
        """
        if not items:
            _get_console().print(
                f"🏁 No {filter_description} milestones found.", style="yellow"
            )
            _get_console().print(
                "Create one with: roadmap milestone create 'Milestone name'",
                style="dim",
            )
            return

        # Display header with filter info
        header_text = f"🏁 {len(items)} {filter_description} milestone{'s' if len(items) != 1 else ''}"
        _get_console().print(header_text, style="bold cyan")
        _get_console().print()

        # Rich table display
        table = self.create_table()
        for item in items:
            self.add_row(table, item)

        _get_console().print(table)

    def items_to_table_data(
        self, items: list, title: str = "Milestones", description: str = ""
    ) -> TableData:
        """Convert Milestone list to TableData for structured output.

        Args:
            items: List of Milestone objects.
            title: Optional table title.
            description: Optional filter description.

        Returns:
            TableData object ready for rendering in any format.
        """
        columns = [
            ColumnDef(
                name="name",
                display_name="Milestone",
                type=ColumnType.STRING,
                width=20,
                display_style="cyan",
                sortable=True,
                filterable=True,
            ),
            ColumnDef(
                name="description",
                display_name="Description",
                type=ColumnType.STRING,
                width=30,
                display_style="white",
                sortable=True,
                filterable=True,
            ),
            ColumnDef(
                name="status",
                display_name="Status",
                type=ColumnType.ENUM,
                width=10,
                display_style="green",
                enum_values=["open", "closed"],
                sortable=True,
                filterable=True,
            ),
            ColumnDef(
                name="due_date",
                display_name="Due Date",
                type=ColumnType.DATE,
                width=12,
                display_style="yellow",
                sortable=True,
                filterable=True,
            ),
            ColumnDef(
                name="progress",
                display_name="Progress",
                type=ColumnType.STRING,
                width=12,
                display_style="blue",
                sortable=False,
                filterable=False,
            ),
        ]

        rows = []
        for milestone in items:
            progress = ""
            if (
                hasattr(milestone, "calculated_progress")
                and milestone.calculated_progress
            ):
                progress = f"{milestone.calculated_progress:.0f}%"

            due_date_str = ""
            if hasattr(milestone, "due_date") and milestone.due_date:
                due_date_str = milestone.due_date.strftime("%Y-%m-%d")

            rows.append(
                [
                    milestone.name,
                    milestone.description or "",
                    milestone.status.value
                    if hasattr(milestone.status, "value")
                    else str(milestone.status),
                    due_date_str,
                    progress,
                ]
            )

        return TableData(
            columns=columns,
            rows=rows,
            title=title,
            description=description,
            total_count=len(items),
            returned_count=len(items),
        )

    # Backward compatibility methods (for existing code that uses static methods)
    @staticmethod
    def milestones_to_table_data(
        milestones: list, title: str = "Milestones", description: str = ""
    ) -> TableData:
        """Convert Milestone list to TableData for structured output (backward compatible)."""
        return MilestoneTableFormatter().items_to_table_data(
            milestones, title, description
        )
