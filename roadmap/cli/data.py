"""Data management CLI commands."""

import csv
import json

import click

from roadmap.cli.utils import get_console
from roadmap.domain import Issue

console = get_console()


@click.group()
def data():
    """Data export, import, and reporting."""
    pass


def _serialize_issue(issue: Issue) -> dict:
    """Convert an Issue model to a JSON-serializable dict."""
    # Use pydantic's dict but convert datetimes to isoformat strings
    d = issue.dict()
    for k, v in d.items():
        if hasattr(v, "isoformat"):
            try:
                d[k] = v.isoformat()
            except Exception:
                d[k] = str(v)
    return d


@data.command("export")
@click.option(
    "--format",
    type=click.Choice(["json", "csv", "markdown"]),
    default="json",
    help="Export format",
)
@click.option("--output", "-o", help="Output file path")
@click.option("--filter", help="Filter criteria (simple key=value)")
@click.pass_context
def export(ctx: click.Context, format: str, output: str, filter: str):
    """Export roadmap issues to JSON, CSV or Markdown.

    The --filter argument supports a simple key=value filter (e.g. assignee=alice).
    """
    console.print(f"📊 Exporting issues in {format} format...", style="bold blue")

    # Try to obtain core from context
    core = None
    try:
        core = ctx.obj.get("core") if ctx.obj else None
    except Exception:
        core = None

    if core is None:
        # Try to discover an existing roadmap in the current directory
        try:
            from roadmap.application.core import RoadmapCore

            core = RoadmapCore.find_existing_roadmap()
        except Exception:
            core = None

    if core is None or not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first or run this command inside a roadmap.",
            style="bold red",
        )
        return

    # Load issues
    try:
        issues = core.list_issues()
    except Exception as e:
        console.print(f"❌ Failed to list issues: {e}", style="bold red")
        return

    # Apply simple filter if provided
    if filter:
        try:
            key, val = filter.split("=", 1)
            key = key.strip()
            val = val.strip()
            issues = [
                i for i in issues if str(getattr(i, key, "")).lower() == val.lower()
            ]
        except Exception:
            console.print("⚠️  Unable to parse filter, ignoring.", style="yellow")

    if not issues:
        console.print("ℹ️  No issues to export.", style="yellow")
        return

    # Prepare output
    try:
        if format == "json":
            payload = [_serialize_issue(i) for i in issues]
            out_text = json.dumps(payload, indent=2)

        elif format == "csv":
            # Choose a canonical set of fields
            fields = [
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
            # Build CSV lines in-memory
            from io import StringIO

            buf = StringIO()
            writer = csv.DictWriter(buf, fieldnames=fields)
            writer.writeheader()
            for i in issues:
                row = _serialize_issue(i)
                # Ensure only fields present
                writer.writerow({f: row.get(f, "") for f in fields})
            out_text = buf.getvalue()

        else:  # markdown
            lines: list[str] = []
            lines.append("| id | title | status | assignee | milestone | estimated |")
            lines.append("|---|---|---:|---|---|---:|")
            for i in issues:
                est = (
                    i.estimated_time_display
                    if hasattr(i, "estimated_time_display")
                    else (i.estimated_hours or "")
                )
                lines.append(
                    f"| {i.id} | {i.title} | {i.status.value if hasattr(i.status, 'value') else i.status} | {i.assignee or ''} | {i.milestone or ''} | {est} |"
                )
            out_text = "\n".join(lines)

        # Write to file or print
        if output:
            with open(output, "w", encoding="utf-8") as f:
                f.write(out_text)
            console.print(
                f"✅ Exported {len(issues)} issues to {output}", style="bold green"
            )
        else:
            console.print(out_text)

    except Exception as e:
        console.print(f"❌ Failed to export issues: {e}", style="bold red")


@data.command("generate-report")
@click.option(
    "--type",
    type=click.Choice(["summary", "detailed", "analytics"]),
    default="summary",
    help="Report type",
)
@click.option("--output", "-o", help="Output file path")
@click.pass_context
def generate_report(ctx: click.Context, type: str, output: str):
    """Generate detailed reports and analytics."""
    console.print(f"📈 Generating {type} report...", style="bold blue")
    # Implementation would go here
    console.print(
        "✅ Report generation functionality will be implemented", style="green"
    )
