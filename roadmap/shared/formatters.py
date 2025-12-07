"""
Shared formatting utilities for display and export.

Consolidates formatting logic for:
- Issue table display (from issue_display.py)
- Issue export (from export_helpers.py)
- Kanban board organization (from kanban_helpers.py)
"""

import csv
import json
from datetime import datetime
from io import StringIO

from rich.table import Table
from rich.text import Text

from roadmap.common.console import get_console
from roadmap.core.domain import Issue, Priority, Status

console = get_console()


# ─────────────────────────────────────────────────────────────────────────────
# Issue Table Display
# ─────────────────────────────────────────────────────────────────────────────


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


# ─────────────────────────────────────────────────────────────────────────────
# Issue Export Formatting
# ─────────────────────────────────────────────────────────────────────────────


class IssueExporter:
    """Format issues for export in various formats."""

    CSV_FIELDS = [
        "id",
        "title",
        "status",
        "assignee",
        "priority",
        "estimated_hours",
        "milestone",
        "created",
        "updated",
    ]

    @staticmethod
    def to_json(issues: list[Issue], serializer_func) -> str:
        """Export issues to JSON format."""
        payload = [serializer_func(i) for i in issues]
        return json.dumps(payload, indent=2)

    @classmethod
    def to_csv(cls, issues: list[Issue], serializer_func) -> str:
        """Export issues to CSV format."""
        buf = StringIO()
        writer = csv.DictWriter(buf, fieldnames=cls.CSV_FIELDS)
        writer.writeheader()

        for issue in issues:
            row = serializer_func(issue)
            # Ensure only fields present
            writer.writerow({f: row.get(f, "") for f in cls.CSV_FIELDS})

        return buf.getvalue()

    @staticmethod
    def to_markdown(issues: list[Issue]) -> str:
        """Export issues to Markdown table format."""
        lines = [
            "| id | title | status | assignee | milestone | estimated |",
            "|---|---|---:|---|---|---:|",
        ]

        for i in issues:
            est = (
                i.estimated_time_display
                if hasattr(i, "estimated_time_display")
                else (i.estimated_hours or "")
            )
            status_val = i.status.value if hasattr(i.status, "value") else i.status
            lines.append(
                f"| {i.id} | {i.title} | {status_val} | {i.assignee or ''} | {i.milestone or ''} | {est} |"
            )

        return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# Kanban Board Organization
# ─────────────────────────────────────────────────────────────────────────────


class KanbanOrganizer:
    """Organizes issues into kanban columns."""

    @staticmethod
    def categorize_issues(milestone_issues: list[Issue]) -> dict:
        """
        Categorize issues into kanban columns.

        Returns:
            Dictionary with keys: overdue, blocked, in_progress, not_started, done
        """
        now = datetime.now()

        categories = {
            "overdue": [],
            "blocked": [],
            "in_progress": [],
            "not_started": [],
            "closed": [],
        }

        for issue in milestone_issues:
            if issue.status.value == "closed":
                categories["closed"].append(issue)
            elif issue.status.value == "blocked":
                categories["blocked"].append(issue)
            elif issue.status.value == "in-progress":
                categories["in_progress"].append(issue)
            elif (
                issue.due_date
                and issue.due_date < now
                and issue.status.value != "closed"
            ):
                categories["overdue"].append(issue)
            else:
                categories["not_started"].append(issue)

        return categories

    @staticmethod
    def create_column_definitions(
        categories: dict, no_color: bool
    ) -> list[tuple[str, list[Issue], str]]:
        """
        Create column definitions for display.

        Returns:
            List of tuples: (column_title, issues, style)
        """
        return [
            (
                "🚨 Overdue",
                categories["overdue"],
                "bold red" if not no_color else "white",
            ),
            (
                "🚫 Blocked",
                categories["blocked"],
                "bold yellow" if not no_color else "white",
            ),
            (
                "🔄 In Progress",
                categories["in_progress"],
                "bold blue" if not no_color else "white",
            ),
            (
                "⏸️  Not Started",
                categories["not_started"],
                "dim white" if not no_color else "white",
            ),
            (
                "✅ Closed",
                categories["closed"],
                "bold green" if not no_color else "white",
            ),
        ]


class KanbanLayout:
    """Handles kanban board layout calculations and rendering."""

    @staticmethod
    def calculate_column_width(num_columns: int) -> int:
        """Calculate column width based on terminal size."""
        try:
            import shutil

            terminal_width = shutil.get_terminal_size().columns
            return max(30, (terminal_width - 5) // num_columns)
        except Exception:
            return 35

    @staticmethod
    def format_issue_cell(issue: Issue, col_width: int, compact: bool) -> str:
        """Format a single issue for display in a kanban cell."""
        if not issue:
            return " " * col_width

        # Truncate title if needed
        max_title_len = col_width - 4
        display_title = (
            issue.title[:max_title_len]
            if len(issue.title) > max_title_len
            else issue.title
        )

        if compact:
            return f"• {display_title:<{col_width - 2}}"
        else:
            priority_emoji = {
                "critical": "🔴",
                "high": "🟠",
                "medium": "🟡",
                "low": "⚪",
            }.get(issue.priority.value, "⚪")
            return f"{priority_emoji} {display_title:<{col_width - 3}}"
