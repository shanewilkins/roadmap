"""Issue table formatting and display."""

from rich.text import Text

from roadmap.common.console import get_console
from roadmap.common.output_models import ColumnDef, ColumnType, TableData
from roadmap.core.domain import Issue, Priority, Status

console = get_console()


class IssueTableFormatter:
    """Formats issues for display in rich tables."""

    @staticmethod
    def create_issue_table():
        """Create a rich table with issue columns."""
        from rich.table import Table

        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("ID", style="cyan", width=8)
        table.add_column("Title", style="white", width=25, no_wrap=False)
        table.add_column("Priority", style="yellow", width=10)
        table.add_column("Status", style="green", width=12)
        table.add_column("Progress", style="blue", width=10)
        table.add_column("Assignee", style="magenta", width=12)
        table.add_column("Estimate", style="green", width=10)
        table.add_column("Milestone", style="blue", width=15)
        return table

    @staticmethod
    def add_issue_row(table, issue: Issue) -> None:
        """Add a single issue row to the table."""
        priority_style = {
            Priority.CRITICAL: "bold red",
            Priority.HIGH: "red",
            Priority.MEDIUM: "yellow",
            Priority.LOW: "dim",
        }.get(issue.priority, "white")

        status_style = {
            Status.TODO: "white",
            Status.IN_PROGRESS: "yellow",
            Status.BLOCKED: "red",
            Status.REVIEW: "blue",
            Status.CLOSED: "green",
        }.get(issue.status, "white")

        table.add_row(
            issue.id,
            issue.title,
            Text(issue.priority.value, style=priority_style),
            Text(issue.status.value, style=status_style),
            Text(
                issue.progress_display,
                style="blue" if issue.progress_percentage else "dim",
            ),
            Text(
                issue.assignee or "Unassigned",
                style="magenta" if issue.assignee else "dim",
            ),
            Text(
                issue.estimated_time_display,
                style="green" if issue.estimated_hours else "dim",
            ),
            Text(issue.milestone_name, style="dim" if issue.is_backlog else "blue"),
        )

    @classmethod
    def display_issues(cls, issues: list[Issue], filter_description: str) -> None:
        """Display issues in a formatted table."""
        if not issues:
            console.print(f"📋 No {filter_description} issues found.", style="yellow")
            console.print(
                "Create one with: roadmap issue create 'Issue title'", style="dim"
            )
            return

        # Display header with filter info
        header_text = f"📋 {len(issues)} {filter_description} issue{'s' if len(issues) != 1 else ''}"
        console.print(header_text, style="bold cyan")
        console.print()

        # Rich table display
        table = cls.create_issue_table()
        for issue in issues:
            cls.add_issue_row(table, issue)

        console.print(table)

    @staticmethod
    def issues_to_table_data(
        issues: list[Issue], title: str = "Issues", description: str = ""
    ) -> TableData:
        """Convert Issue list to TableData for structured output.

        Args:
            issues: List of Issue objects.
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
                width=8,
                display_style="cyan",
                sortable=True,
                filterable=True,
            ),
            ColumnDef(
                name="title",
                display_name="Title",
                type=ColumnType.STRING,
                width=25,
                display_style="white",
                sortable=True,
                filterable=True,
            ),
            ColumnDef(
                name="priority",
                display_name="Priority",
                type=ColumnType.ENUM,
                width=10,
                display_style="yellow",
                enum_values=["critical", "high", "medium", "low"],
                sortable=True,
                filterable=True,
            ),
            ColumnDef(
                name="status",
                display_name="Status",
                type=ColumnType.ENUM,
                width=12,
                display_style="green",
                enum_values=["todo", "in-progress", "blocked", "review", "closed"],
                sortable=True,
                filterable=True,
            ),
            ColumnDef(
                name="progress",
                display_name="Progress",
                type=ColumnType.STRING,
                width=10,
                display_style="blue",
                sortable=False,
                filterable=False,
            ),
            ColumnDef(
                name="assignee",
                display_name="Assignee",
                type=ColumnType.STRING,
                width=12,
                display_style="magenta",
                sortable=True,
                filterable=True,
            ),
            ColumnDef(
                name="estimate",
                display_name="Estimate",
                type=ColumnType.STRING,
                width=10,
                display_style="green",
                sortable=True,
                filterable=False,
            ),
            ColumnDef(
                name="milestone",
                display_name="Milestone",
                type=ColumnType.STRING,
                width=15,
                display_style="blue",
                sortable=True,
                filterable=True,
            ),
        ]

        rows = []
        for issue in issues:
            rows.append(
                [
                    issue.id,
                    issue.title,
                    issue.priority.value,
                    issue.status.value,
                    issue.progress_display,
                    issue.assignee or "Unassigned",
                    issue.estimated_time_display,
                    issue.milestone_name,
                ]
            )

        return TableData(
            columns=columns,
            rows=rows,
            title=title,
            description=description,
            total_count=len(issues),
            returned_count=len(issues),
        )

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

        console.print()
        console.print(
            f"Total estimated time for {assignee_name}: {total_display}",
            style="bold blue",
        )

        # Show status breakdown
        console.print("Workload breakdown:", style="bold")
        for status, data in status_breakdown.items():
            if data["count"] > 0:
                if data["hours"] > 0:
                    if data["hours"] < 1:
                        time_display = f"{data['hours'] * 60:.0f}m"
                    elif data["hours"] <= 24:
                        time_display = f"{data['hours']:.1f}h"
                    else:
                        time_display = f"{data['hours'] / 8:.1f}d"
                    console.print(
                        f"  {status}: {data['count']} issues ({time_display})"
                    )
                else:
                    console.print(f"  {status}: {data['count']} issues")
