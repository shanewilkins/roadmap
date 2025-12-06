"""Data management commands for export and reporting."""

import click

from roadmap.adapters.cli.logging_decorators import verbose_output
from roadmap.common.console import get_console
from roadmap.core.domain import Issue

console = get_console()


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


@click.group()
def data():
    """Data export, import, and reporting."""
    pass


@data.command("export")
@click.option(
    "--format",
    type=click.Choice(["json", "csv", "markdown"]),
    default="json",
    help="Export format",
)
@click.option("--output", "-o", help="Output file path")
@click.option("--filter", help="Filter criteria (simple key=value)")
@click.option("--verbose", "-v", is_flag=True, help="Show verbose output")
@click.pass_context
@verbose_output
def export(ctx: click.Context, format: str, output: str, filter: str, verbose: bool):
    """Export roadmap issues to JSON, CSV or Markdown.

    The --filter argument supports a simple key=value filter (e.g. assignee=alice).
    """
    console.print(f"📊 Exporting issues in {format} format...", style="bold blue")

    # Get core and issues
    core = _get_core(ctx)
    if not core or not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first or run this command inside a roadmap.",
            style="bold red",
        )
        return

    issues = _load_and_filter_issues(core, filter)
    if not issues:
        console.print("ℹ️  No issues to export.", style="yellow")
        return

    # Format and output
    _export_and_write(issues, format, output)


def _get_core(ctx: click.Context):
    """Get RoadmapCore from context or discover existing roadmap."""
    try:
        core = ctx.obj.get("core") if ctx.obj else None
    except Exception:
        core = None

    if core is None:
        try:
            from roadmap.infrastructure.core import RoadmapCore

            core = RoadmapCore.find_existing_roadmap()
        except Exception:
            core = None

    return core


def _load_and_filter_issues(core, filter_str: str):
    """Load issues and apply filter if provided."""
    try:
        issues = core.issues.list()
    except Exception as e:
        console.print(f"❌ Failed to list issues: {e}", style="bold red")
        return []

    if filter_str:
        try:
            key, val = filter_str.split("=", 1)
            key = key.strip()
            val = val.strip()
            issues = [
                i for i in issues if str(getattr(i, key, "")).lower() == val.lower()
            ]
        except Exception:
            console.print("⚠️  Unable to parse filter, ignoring.", style="yellow")

    return issues


def _export_and_write(issues, format_type: str, output_path: str):
    """Format issues and write to file or stdout."""
    from roadmap.adapters.cli.export_helpers import IssueExporter

    try:
        if format_type == "json":
            out_text = IssueExporter.to_json(issues, _serialize_issue)
        elif format_type == "csv":
            out_text = IssueExporter.to_csv(issues, _serialize_issue)
        else:  # markdown
            out_text = IssueExporter.to_markdown(issues)

        # Write to file or print
        if output_path:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(out_text)
            console.print(
                f"✅ Exported {len(issues)} issues to {output_path}", style="bold green"
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
@click.option("--verbose", "-v", is_flag=True, help="Show verbose output")
@click.pass_context
@verbose_output
def generate_report(ctx: click.Context, type: str, output: str, verbose: bool):
    """Generate detailed reports and analytics."""
    console.print(f"📈 Generating {type} report...", style="bold blue")
    # Implementation would go here
    console.print(
        "✅ Report generation functionality will be implemented", style="green"
    )
