"""
Kanban board organization and display helpers.
"""

from datetime import datetime

from roadmap.domain import Issue


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
            "done": [],
        }

        for issue in milestone_issues:
            if issue.status.value == "done":
                categories["done"].append(issue)
            elif issue.status.value == "blocked":
                categories["blocked"].append(issue)
            elif issue.status.value == "in-progress":
                categories["in_progress"].append(issue)
            elif (
                issue.due_date and issue.due_date < now and issue.status.value != "done"
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
            ("✅ Done", categories["done"], "bold green" if not no_color else "white"),
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
