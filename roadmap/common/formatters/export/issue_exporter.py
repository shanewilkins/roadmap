"""Issue export functionality."""

import csv
import json
from collections.abc import Sequence
from io import StringIO

from roadmap.common.formatters.output import OutputFormatter
from roadmap.common.formatters.tables import IssueTableFormatter
from roadmap.core.domain import Issue


class IssueExporter:
    """
    Export issues to various formats.

    Supports two export styles:
    1. Unified export() - recommended for production use
    2. Legacy to_json/to_csv/to_markdown - for backward compatibility
    """

    # Legacy CSV fields definition
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
    def export(issues: Sequence[Issue], format_type: str, title: str = "Issues") -> str:
        """
        Export issues using the unified OutputFormatter.

        Converts issues to TableData and uses OutputFormatter for consistent
        rendering across all formats.

        Args:
            issues: List of Issue objects
            format_type: One of 'json', 'csv', 'markdown'
            title: Optional table title

        Returns:
            Formatted string ready for output
        """
        table_data = IssueTableFormatter.issues_to_table_data(issues, title=title)  # type: ignore
        formatter = OutputFormatter(table_data)

        if format_type == "json":
            return formatter.to_json()
        elif format_type == "csv":
            return formatter.to_csv()
        elif format_type == "markdown":
            return formatter.to_markdown()
        else:
            raise ValueError(
                f"Unknown format: {format_type}. Use 'json', 'csv', or 'markdown'."
            )

    @staticmethod
    def to_json(issues: Sequence[Issue], serializer_func) -> str:
        """Legacy JSON export with custom serializer (for backward compatibility)."""
        payload = [serializer_func(i) for i in issues]
        return json.dumps(payload, indent=2)

    @classmethod
    def to_csv(cls, issues: Sequence[Issue], serializer_func) -> str:
        """Legacy CSV export with custom serializer (for backward compatibility)."""
        buf = StringIO()
        writer = csv.DictWriter(buf, fieldnames=cls.CSV_FIELDS)
        writer.writeheader()
        for issue in issues:
            row = serializer_func(issue)
            writer.writerow({f: row.get(f, "") for f in cls.CSV_FIELDS})
        return buf.getvalue()

    @staticmethod
    def to_markdown(issues: Sequence[Issue]) -> str:
        """Legacy Markdown export (for backward compatibility)."""
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
