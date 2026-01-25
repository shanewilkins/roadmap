"""Kanban board layout and rendering."""

from structlog import get_logger

from roadmap.core.domain import Issue

logger = get_logger()


class KanbanLayout:
    """Handles kanban board layout calculations and rendering."""

    @staticmethod
    def calculate_column_width(num_columns: int) -> int:
        """Calculate column width based on terminal size."""
        try:
            import shutil

            terminal_width = shutil.get_terminal_size().columns
            return max(30, (terminal_width - 5) // num_columns)
        except Exception as e:
            logger.debug("terminal_size_calculation_failed", error=str(e))
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
