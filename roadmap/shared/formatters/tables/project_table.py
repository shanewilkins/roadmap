"""Project table formatting and display."""

from typing import TYPE_CHECKING, Any, cast

from roadmap.common.console import get_console
from roadmap.common.output_models import ColumnDef, ColumnType, TableData
from roadmap.core.domain import Priority, ProjectStatus
from roadmap.shared.formatters.base_table_formatter import BaseTableFormatter

if TYPE_CHECKING:
    pass

console = get_console()


class ProjectTableFormatter(BaseTableFormatter):
    """Formats projects for display and structured output."""

    def __init__(self):
        """Initialize project formatter with headers and columns."""
        super().__init__()
        self.columns_config = [
            {"name": "ID", "style": "cyan", "width": 10},
            {"name": "Name", "style": "white", "width": 25},
            {"name": "Status", "style": "magenta", "width": 12},
            {"name": "Priority", "style": "yellow", "width": 10},
            {"name": "Owner", "style": "green", "width": 15},
        ]

    def create_table(self) -> Any:
        """Create a rich table with project columns."""
        from rich.table import Table

        table = Table(show_header=True, header_style="bold cyan")
        for col in self.columns_config:
            table.add_column(col["name"], style=col["style"], width=col["width"])
        return table

    def add_row(self, table: Any, item) -> None:
        """Add a single project row to the table.

        Args:
            table: Rich Table object
            item: Project object (dict or object) to add
        """
        from rich.text import Text

        # Handle both dict and object formats
        if isinstance(item, dict):
            project_id = item.get("id", "unknown")[:8]
            project_name = item.get("name", "Unnamed")
            project_status = item.get("status", "unknown")
            project_priority = item.get("priority", "medium")
            project_owner = item.get("owner", "Unassigned")
        else:
            # Handle Project object
            project_id = getattr(item, "id", "unknown")[:8]
            project_name = getattr(item, "name", "Unnamed")
            raw_status = getattr(item, "status", "unknown")
            project_status = (
                str(cast(Any, raw_status).value)
                if hasattr(raw_status, "value")
                else str(raw_status)
            )
            raw_priority = getattr(item, "priority", "medium")
            project_priority = (
                str(cast(Any, raw_priority).value)
                if hasattr(raw_priority, "value")
                else str(raw_priority)
            )
            project_owner = getattr(item, "owner", "Unassigned")

        table.add_row(
            Text(project_id, style="cyan"),
            Text(project_name, style="white"),
            Text(str(project_status), style="magenta"),
            Text(str(project_priority), style="yellow"),
            Text(str(project_owner), style="green"),
        )

    def get_filter_description(self, items: list) -> str:
        """Get human-readable description of filtered projects.

        Args:
            items: List of projects being displayed

        Returns:
            Description string (e.g., "5 active projects")
        """
        count = len(items)
        return f"🎯 {count} project{'s' if count != 1 else ''}"

    def display_items(self, items: list, filter_description: str = "all") -> None:
        """Display projects in a formatted table.

        Args:
            items: List of project objects
            filter_description: Description of filter applied
        """
        if not items:
            console.print(f"🎯 No {filter_description} projects found.", style="yellow")
            console.print(
                "Create one with: roadmap project create 'Project name'", style="dim"
            )
            return

        # Display header with filter info
        header_text = f"🎯 {len(items)} {filter_description} project{'s' if len(items) != 1 else ''}"
        console.print(header_text, style="bold cyan")
        console.print()

        # Rich table display
        table = self.create_table()
        for item in items:
            self.add_row(table, item)

        console.print(table)

    def items_to_table_data(
        self, items: list, title: str = "Projects", description: str = ""
    ) -> TableData:
        """Convert Project list to TableData for structured output.

        Args:
            items: List of project metadata dictionaries or Project objects.
            title: Optional table title.
            description: Optional filter description.

        Returns:
            TableData object ready for rendering in any format.
        """
        columns = [
            ColumnDef(
                name="id",
                display_name="ID",
                type=ColumnType.STRING,
                width=10,
                display_style="cyan",
                sortable=True,
                filterable=True,
            ),
            ColumnDef(
                name="name",
                display_name="Name",
                type=ColumnType.STRING,
                width=25,
                display_style="white",
                sortable=True,
                filterable=True,
            ),
            ColumnDef(
                name="status",
                display_name="Status",
                type=ColumnType.ENUM,
                width=12,
                display_style="magenta",
                enum_values=[s.value for s in ProjectStatus],
                sortable=True,
                filterable=True,
            ),
            ColumnDef(
                name="priority",
                display_name="Priority",
                type=ColumnType.ENUM,
                width=10,
                display_style="yellow",
                enum_values=[p.value for p in Priority],
                sortable=True,
                filterable=True,
            ),
            ColumnDef(
                name="owner",
                display_name="Owner",
                type=ColumnType.STRING,
                width=15,
                display_style="green",
                sortable=True,
                filterable=True,
            ),
        ]

        rows = []
        for project in items:
            # Handle both dict and object formats
            if isinstance(project, dict):
                project_id = project.get("id", "unknown")[:8]
                project_name = project.get("name", "Unnamed")
                project_status = project.get("status", "unknown")
                project_priority = project.get("priority", "medium")
                project_owner = project.get("owner", "Unassigned")
            else:
                # Handle Project object
                project_id = getattr(project, "id", "unknown")[:8]
                project_name = getattr(project, "name", "Unnamed")
                raw_status = getattr(project, "status", "unknown")
                project_status = (
                    str(cast(Any, raw_status).value)
                    if hasattr(raw_status, "value")
                    else str(raw_status)
                )
                raw_priority = getattr(project, "priority", "medium")
                project_priority = (
                    str(cast(Any, raw_priority).value)
                    if hasattr(raw_priority, "value")
                    else str(raw_priority)
                )
                project_owner = getattr(project, "owner", "Unassigned")

            rows.append(
                [
                    project_id,
                    project_name,
                    project_status,
                    project_priority,
                    project_owner,
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
    def projects_to_table_data(
        projects: list, title: str = "Projects", description: str = ""
    ) -> TableData:
        """Convert Project list to TableData for structured output (backward compatible)."""
        return ProjectTableFormatter().items_to_table_data(projects, title, description)
