"""
Issue display formatting logic for CLI.
"""

from rich.table import Table
from rich.text import Text

from roadmap.cli.utils import get_console
from roadmap.domain import Issue, Priority, Status

console = get_console()


class IssueTableFormatter:
    """Formats issues for display in rich tables."""

    @staticmethod
    def create_issue_table() -> Table:
        """Create a rich table with issue columns."""
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
    def add_issue_row(table: Table, issue: Issue) -> None:
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
            Status.DONE: "green",
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
