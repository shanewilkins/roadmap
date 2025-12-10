"""
Shared formatting utilities for display and export.

This module consolidates:
- Issue export (JSON, CSV, Markdown)
- Kanban board organization and layout
- Table formatter re-exports (for backward compatibility)

Note: Table formatters (Issue/Project/Milestone) are now in:
- roadmap.shared.formatters.tables.issue_table
- roadmap.shared.formatters.tables.project_table
- roadmap.shared.formatters.tables.milestone_table
"""

import csv
import json
from datetime import datetime
from io import StringIO

from roadmap.common.console import get_console
from roadmap.core.domain import Issue

# Re-export formatters from their new locations to avoid duplicate code
# and maintain backward compatibility
from roadmap.shared.formatters.tables import (
    IssueTableFormatter,
    MilestoneTableFormatter,
    ProjectTableFormatter,
)

console = get_console()


# ─────────────────────────────────────────────────────────────────────────────
# Issue Export
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


__all__ = [
    "IssueTableFormatter",
    "ProjectTableFormatter",
    "MilestoneTableFormatter",
    "IssueExporter",
    "KanbanOrganizer",
    "KanbanLayout",
]
