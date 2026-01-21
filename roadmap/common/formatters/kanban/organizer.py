"""Kanban board organization."""

from datetime import UTC, datetime

from roadmap.core.domain import Issue


class KanbanOrganizer:
    """Organizes issues into kanban columns."""

    @staticmethod
    def categorize_issues(milestone_issues: list[Issue]) -> dict:
        """Categorize issues into kanban columns.

        Returns:
            Dictionary with keys: overdue, blocked, in_progress, not_started, done
        """
        now = datetime.now(UTC)

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
        """Create column definitions for display.

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
