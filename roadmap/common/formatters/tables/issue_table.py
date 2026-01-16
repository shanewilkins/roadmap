"""Issue table formatting and display."""

from collections.abc import Sequence
from typing import TYPE_CHECKING, Any

from rich.text import Text

from roadmap.common.console import get_console
from roadmap.common.formatters.base_table_formatter import BaseTableFormatter
from roadmap.common.formatters.tables.column_factory import create_issue_columns
from roadmap.common.models import TableData
from roadmap.common.status_style_manager import StatusStyleManager
from roadmap.core.domain import Issue, Priority

if TYPE_CHECKING:
    pass


def _get_console():
    """Get a fresh console instance for test compatibility."""
    return get_console()


class IssueTableFormatter(BaseTableFormatter[Issue]):
    """Formats issues for display in rich tables."""

    def __init__(self):
        """Initialize issue formatter with headers and columns."""
        self.show_github_ids = False
        self.columns_config = [
            {"name": "ID", "style": "cyan", "width": 8},
            {"name": "Title", "style": "white", "width": 25, "no_wrap": True},
            {"name": "Headline", "style": "white", "width": 30},
            {"name": "Priority", "style": "yellow", "width": 10},
            {"name": "Status", "style": "green", "width": 12},
            {"name": "Progress", "style": "blue", "width": 10},
            {"name": "Assignee", "style": "magenta", "width": 12},
            {"name": "Estimate", "style": "green", "width": 10},
            {"name": "Milestone", "style": "blue", "width": 15},
        ]
        # Add GitHub ID column if needed (will be shown if flag is set)
        self.github_id_column = {"name": "GitHub #", "style": "cyan", "width": 10}

    def create_table(self) -> Any:
        """Create a rich table with issue columns."""
        from rich.table import Table

        table = Table(show_header=True, header_style="bold magenta")
        for col in self.columns_config:
            table.add_column(
                col["name"],
                style=col["style"],
                width=col["width"],
                no_wrap=col.get("no_wrap", False),
            )
        # Add GitHub ID column if showing them
        if self.show_github_ids:
            table.add_column(
                self.github_id_column["name"],
                style=self.github_id_column["style"],
                width=self.github_id_column["width"],
            )
        return table

    def add_row(self, table: Any, item: Issue) -> None:
        """Add a single issue row to the table.

        Args:
            table: Rich Table object
            item: Issue object to add
        """
        priority_style = {
            Priority.CRITICAL: "bold red",
            Priority.HIGH: "red",
            Priority.MEDIUM: "yellow",
            Priority.LOW: "dim",
        }.get(item.priority, "white")

        # Build row cells
        comment_count = 0
        if hasattr(item, "comments") and item.comments:
            try:
                comment_count = len(item.comments)
            except TypeError:
                # Handle Mock objects or other non-sequence types
                comment_count = 0

        comment_display = f"💬 {comment_count}" if comment_count > 0 else "-"

        cells = [
            item.id,
            item.title,
            Text(item.headline or "", style="white"),
            Text(item.priority.value, style=priority_style),
            Text(item.status.value, style=StatusStyleManager.get_style(item.status)),
            Text(
                item.progress_display,
                style="blue" if item.progress_percentage else "dim",
            ),
            Text(
                item.assignee or "Unassigned",
                style="magenta" if item.assignee else "dim",
            ),
            Text(
                item.estimated_time_display,
                style="green" if item.estimated_hours else "dim",
            ),
            Text(item.milestone_name, style="dim" if item.is_backlog else "blue"),
            Text(comment_display, style="cyan" if comment_count > 0 else "dim"),
        ]

        # Add GitHub ID if showing them
        if self.show_github_ids:
            github_id_text = (
                f"#{item.github_issue}" if item.github_issue else Text("-", style="dim")
            )
            cells.append(github_id_text)

        table.add_row(*cells)

    def display_items(self, items: list[Issue], filter_description: str) -> None:
        """Display issues in a formatted table.

        Args:
            items: List of Issue objects
            filter_description: Description of filter applied
        """
        if not items:
            _get_console().print(
                f"📋 No {filter_description} issues found.", style="yellow"
            )
            _get_console().print(
                "Create one with: roadmap issue create 'Issue title'", style="dim"
            )
            return

        # Display header with filter info
        header_text = f"📋 {len(items)} {filter_description} issue{'s' if len(items) != 1 else ''}"
        _get_console().print(header_text, style="bold cyan")
        _get_console().print()

        # Rich table display
        table = self.create_table()
        for item in items:
            self.add_row(table, item)

        _get_console().print(table)

    def get_filter_description(self, items: list[Issue]) -> str:
        """Get human-readable description of filtered issues.

        Args:
            items: List of issues being displayed

        Returns:
            Description string (e.g., "5 open issues")
        """
        count = len(items)
        return f"📋 {count} issue{'s' if count != 1 else ''}"

    def items_to_table_data(
        self, items: list[Issue], title: str = "Issues", description: str = ""
    ) -> TableData:
        """Convert Issue list to TableData for structured output.

        Args:
            items: List of Issue objects.
            title: Optional table title.
            description: Optional filter description.

        Returns:
            TableData object ready for rendering in any format.
        """
        columns = create_issue_columns()

        rows = []
        for item in items:
            comment_count = 0
            if hasattr(item, "comments") and item.comments:
                try:
                    comment_count = len(item.comments)
                except TypeError:
                    # Handle Mock objects or other non-sequence types
                    comment_count = 0

            comment_display = f"💬 {comment_count}" if comment_count > 0 else ""

            rows.append(
                [
                    item.id,
                    item.title,
                    item.priority.value,
                    item.status.value,
                    item.progress_display,
                    item.assignee or "Unassigned",
                    item.estimated_time_display,
                    item.milestone_name,
                    comment_display,
                ]
            )

        return TableData(
            columns=columns,
            rows=rows,
            title=title,
            headline=description,
            total_count=len(items),
            returned_count=len(items),
        )

    # Backward compatibility methods (for existing code that uses static methods)
    @classmethod
    def create_issue_table(cls):
        """Create a rich table with issue columns (backward compatible)."""
        return cls().create_table()

    @classmethod
    def add_issue_row(cls, table, issue: Issue) -> None:
        """Add a single issue row to the table (backward compatible)."""
        cls().add_row(table, issue)

    @classmethod
    def display_issues(cls, issues: list[Issue], filter_description: str) -> None:
        """Display issues in a formatted table (backward compatible)."""
        cls().display_items(issues, filter_description)

    @staticmethod
    def issues_to_table_data(
        issues: Sequence[Issue],
        title: str = "Issues",
        description: str = "",
        show_github_ids: bool = False,
    ) -> TableData:
        """Convert Issue list to TableData for structured output (backward compatible)."""
        formatter = IssueTableFormatter()
        formatter.show_github_ids = show_github_ids
        return formatter.items_to_table_data(list(issues), title, description)

    @staticmethod
    def display_workload_summary(
        assignee_name: str, total_hours: float, status_breakdown: dict
    ) -> None:
        """Display workload summary for an assignee."""
        if total_hours == 0:
            return

        # Format total time display
        if total_hours < 1:
            total_display = f"{total_hours * 60:.0f}m"
        elif total_hours <= 24:
            total_display = f"{total_hours:.1f}h"
        else:
            total_display = f"{total_hours / 8:.1f}d"

        _get_console().print()
        _get_console().print(
            f"Total estimated time for {assignee_name}: {total_display}",
            style="bold blue",
        )

        # Show status breakdown
        _get_console().print("Workload breakdown:", style="bold")
        for status, data in status_breakdown.items():
            if data["count"] > 0:
                if data["hours"] > 0:
                    if data["hours"] < 1:
                        time_display = f"{data['hours'] * 60:.0f}m"
                    elif data["hours"] <= 24:
                        time_display = f"{data['hours']:.1f}h"
                    else:
                        time_display = f"{data['hours'] / 8:.1f}d"
                    _get_console().print(
                        f"  {status}: {data['count']} issues ({time_display})"
                    )
                else:
                    _get_console().print(f"  {status}: {data['count']} issues")
