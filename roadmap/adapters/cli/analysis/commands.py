"""Analysis commands for roadmap insights and reporting."""

import json
from pathlib import Path

import click

from roadmap.common.console import get_console
from roadmap.core.services.critical_path_calculator import CriticalPathCalculator
from roadmap.infrastructure.logging import verbose_output

console = get_console()


@click.group()
def analysis():
    """Analysis and insights commands."""
    pass


@analysis.command("critical-path")
@click.option(
    "--milestone",
    "-m",
    help="Analyze critical path for specific milestone only",
)
@click.option(
    "--include-closed",
    is_flag=True,
    help="Include closed issues in analysis (configurable via config.behavior.include_closed_in_critical_path)",
)
@click.option(
    "--export",
    type=click.Choice(["json", "csv"]),
    help="Export format instead of displaying ASCII graph",
)
@click.option(
    "--output",
    "-o",
    help="Output file path for export",
)
@click.pass_context
@verbose_output
def critical_path(
    ctx: click.Context,
    milestone: str | None,
    include_closed: bool,
    export: str | None,
    output: str | None,
):
    """Analyze critical path of issues and dependencies.

    Displays the longest dependency chain in your roadmap and identifies
    the issues that have the most impact on project completion.

    By default, shows an ASCII dependency graph with a summary of key metrics.
    """
    core = _get_core(ctx)
    if not core or not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.",
            style="bold red",
        )
        return

    # Get configuration
    config = core.config_manager.get_config()
    include_closed_default = (
        config.behavior.include_closed_in_critical_path
        if hasattr(config, "behavior")
        else False
    )
    include_closed_flag = include_closed or include_closed_default

    # Load issues
    issues = core.issue_manager.get_all_issues()

    # Filter by milestone if specified
    if milestone:
        issues = [i for i in issues if i.milestone == milestone]

    # Filter closed issues unless explicitly included
    if not include_closed_flag:
        issues = [i for i in issues if i.status != "closed"]

    if not issues:
        console.print(
            f"ℹ️  No active issues to analyze.{f' In milestone: {milestone}' if milestone else ''}",
            style="yellow",
        )
        return

    # Calculate critical path
    calculator = CriticalPathCalculator()
    result = calculator.calculate_critical_path(issues)

    # Output results
    if export:
        _export_critical_path(result, issues, export, output)
    else:
        _display_critical_path(result, milestone)


def _get_core(ctx: click.Context):
    """Get RoadmapCore from context."""
    try:
        return ctx.obj.get("core") if ctx.obj else None
    except (AttributeError, TypeError):
        return None


def _display_critical_path(result, milestone: str | None = None):
    """Display critical path as ASCII graph with summary."""
    from roadmap.adapters.cli.analysis.presenter import CriticalPathPresenter

    presenter = CriticalPathPresenter()
    output = presenter.format_critical_path(result, milestone)
    console.print(output)


def _export_critical_path(result, issues: list, format: str, output_path: str | None):
    """Export critical path data to file or stdout."""
    if format == "json":
        data = _format_json_export(result, issues)
        output_str = json.dumps(data, indent=2, default=str)
    elif format == "csv":
        output_str = _format_csv_export(result, issues)
    else:
        console.print("❌ Unsupported export format", style="bold red")
        return

    if output_path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(output_str)
        console.print(f"✅ Exported to {path}", style="bold green")
    else:
        console.print(output_str)


def _format_json_export(result, issues: list) -> dict:
    """Format critical path data as JSON."""
    return {
        "critical_path": [
            {
                "issue_id": node.issue_id,
                "title": node.issue_title,
                "duration_hours": node.duration_hours,
                "is_critical": node.is_critical,
                "slack_time": node.slack_time,
            }
            for node in result.critical_path
        ],
        "summary": {
            "total_duration": result.total_duration,
            "critical_issue_count": len(result.critical_issue_ids),
            "blocking_issues": result.blocking_issues,
            "project_end_date": result.project_end_date.isoformat()
            if result.project_end_date
            else None,
        },
    }


def _format_csv_export(result, issues: list) -> str:
    """Format critical path data as CSV."""
    lines = [
        "issue_id,title,duration_hours,dependencies,slack_hours,is_critical,status"
    ]

    for issue in issues:
        deps = ",".join(issue.depends_on) if issue.depends_on else ""
        # Find corresponding node
        node = next((n for n in result.critical_path if n.issue_id == issue.id), None)
        slack = f"{node.slack_time:.1f}" if node else "N/A"
        critical = "yes" if issue.id in result.critical_issue_ids else "no"

        lines.append(
            f'"{issue.id}","{issue.title}",{issue.estimated_hours or 0},"{deps}",{slack},{critical},{issue.status}'
        )

    return "\n".join(lines)
