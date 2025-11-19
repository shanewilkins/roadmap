"""
Issue export formatting helpers.
"""

import csv
import json
from io import StringIO

from roadmap.domain import Issue


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
