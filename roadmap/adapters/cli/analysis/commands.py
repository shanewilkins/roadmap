"""Analysis commands for roadmap insights and reporting."""

import json
from pathlib import Path

import click
from structlog import get_logger

from roadmap.common.console import get_console
from roadmap.common.logging import verbose_output
from roadmap.core.services.issue_helpers.issue_filters import IssueQueryService
from roadmap.core.services.utils.critical_path_calculator import CriticalPathCalculator

console = get_console()
logger = get_logger()


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
    help="Include closed issues in analysis",
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
    try:
        logger.debug(
            "Starting critical path analysis",
            extra={
                "milestone": milestone,
                "include_closed": include_closed,
                "export": export,
            },
        )

        core = _get_core(ctx)
        if not core or not core.is_initialized():
            logger.warning("Roadmap not initialized", severity="operational")
            console.print(
                "❌ Roadmap not initialized. Run 'roadmap init' first.",
                style="bold red",
            )
            return

        # Load issues using query service
        logger.debug("Loading issues from query service")
        try:
            query_service = IssueQueryService(core)
            if milestone:
                logger.debug(f"Filtering issues for milestone: {milestone}")
                issues_domain, filter_desc = query_service.get_filtered_issues(
                    milestone=milestone
                )
            else:
                logger.debug("Loading all issues")
                issues_domain, filter_desc = query_service.get_filtered_issues()
        except Exception as e:
            logger.error(
                "failed_to_load_issues",
                error=str(e),
                severity="operational",
                exc_info=True,
            )
            console.print(f"❌ Failed to load issues: {str(e)}", style="bold red")
            return

        logger.debug(f"Loaded {len(issues_domain)} issues")

        # Filter closed issues unless explicitly included
        if not include_closed:
            original_count = len(issues_domain)
            issues_domain = [i for i in issues_domain if i.status != "closed"]
            filtered_count = original_count - len(issues_domain)
            if filtered_count > 0:
                logger.debug(
                    f"Filtered out {filtered_count} closed issues, {len(issues_domain)} remaining"
                )

        if not issues_domain:
            logger.info(
                "No active issues to analyze",
                extra={"milestone": milestone, "include_closed": include_closed},
            )
            console.print(
                f"ℹ️  No active issues to analyze.{f' In milestone: {milestone}' if milestone else ''}",
                style="yellow",
            )
            return

        # Calculate critical path
        logger.debug(f"Calculating critical path for {len(issues_domain)} issues")
        try:
            calculator = CriticalPathCalculator()
            result = calculator.calculate_critical_path(issues_domain)
            logger.debug(
                "Critical path calculation complete",
                extra={
                    "total_duration": result.total_duration,
                    "critical_issues": len(result.critical_issue_ids),
                },
            )
        except Exception as e:
            logger.error(
                f"Critical path calculation failed: {str(e)}",
                error=str(e),
                severity="operational",
                exc_info=True,
            )
            console.print(
                f"❌ Critical path calculation failed: {str(e)}", style="bold red"
            )
            return

        # Output results
        logger.debug(f"Outputting results - export format: {export or 'display'}")
        if export:
            _export_critical_path(result, issues_domain, export, output)
        else:
            _display_critical_path(result, milestone)

        logger.info("Critical path analysis completed successfully")

    except Exception as e:
        logger.error(
            f"Unexpected error in critical path command: {str(e)}",
            error=str(e),
            severity="operational",
            exc_info=True,
        )
        console.print(f"❌ Unexpected error: {str(e)}", style="bold red")


def _get_core(ctx: click.Context):
    """Get RoadmapCore from context.

    Args:
        ctx: Click context object

    Returns:
        RoadmapCore instance or None if not available
    """
    try:
        return ctx.obj.get("core") if ctx.obj else None
    except (AttributeError, TypeError) as e:
        logger.warning(
            f"Failed to get core from context: {str(e)}",
            error=str(e),
            severity="operational",
        )
        return None


def _display_critical_path(result, milestone: str | None = None):
    """Display critical path as ASCII graph with summary.

    Args:
        result: CriticalPathResult from calculator
        milestone: Optional milestone name for context
    """
    try:
        logger.debug("Formatting critical path for display")
        from roadmap.adapters.cli.analysis.presenter import CriticalPathPresenter

        presenter = CriticalPathPresenter()
        output = presenter.format_critical_path(result, milestone)
        console.print(output)
        logger.debug("Critical path displayed successfully")
    except Exception as e:
        logger.error(
            f"Failed to format critical path display: {str(e)}",
            error=str(e),
            severity="operational",
            exc_info=True,
        )
        console.print(f"❌ Failed to format output: {str(e)}", style="bold red")


def _export_critical_path(result, issues: list, format: str, output_path: str | None):
    """Export critical path data to file or stdout.

    Args:
        result: CriticalPathResult from calculator
        issues: List of Issue domain objects
        format: Export format ('json' or 'csv')
        output_path: Optional file path for export
    """
    try:
        logger.debug(f"Exporting critical path to {format}")

        if format == "json":
            data = _format_json_export(result, issues)
            output_str = json.dumps(data, indent=2, default=str)
        elif format == "csv":
            output_str = _format_csv_export(result, issues)
        else:
            logger.error(
                f"Unsupported export format: {format}", severity="config_error"
            )
            console.print("❌ Unsupported export format", style="bold red")
            return

        if output_path:
            try:
                path = Path(output_path)
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(output_str)
                logger.info(f"Exported critical path to {path}")
                console.print(f"✅ Exported to {path}", style="bold green")
            except OSError as e:
                logger.error(
                    f"Failed to write export file: {str(e)}",
                    error=str(e),
                    severity="operational",
                    exc_info=True,
                )
                console.print(
                    f"❌ Failed to write export file: {str(e)}", style="bold red"
                )
        else:
            logger.debug("Outputting export to stdout")
            console.print(output_str)

    except Exception as e:
        logger.error(
            f"Export failed: {str(e)}",
            error=str(e),
            severity="operational",
            exc_info=True,
        )
        console.print(f"❌ Export failed: {str(e)}", style="bold red")


def _format_json_export(result, issues: list) -> dict:
    """Format critical path data as JSON.

    Args:
        result: CriticalPathResult from calculator
        issues: List of Issue domain objects

    Returns:
        Dictionary with critical path and summary data
    """
    try:
        logger.debug("Formatting critical path as JSON")
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
    except Exception as e:
        logger.error(
            f"JSON formatting failed: {str(e)}",
            error=str(e),
            severity="operational",
            exc_info=True,
        )
        raise


def _format_csv_export(result, issues: list) -> str:
    """Format critical path data as CSV.

    Args:
        result: CriticalPathResult from calculator
        issues: List of Issue domain objects

    Returns:
        CSV-formatted string
    """
    try:
        logger.debug("Formatting critical path as CSV")
        lines = [
            "issue_id,title,duration_hours,dependencies,slack_hours,is_critical,status"
        ]

        for issue in issues:
            deps = ",".join(issue.depends_on) if issue.depends_on else ""
            # Find corresponding node
            node = next(
                (n for n in result.critical_path if n.issue_id == issue.id), None
            )
            slack = f"{node.slack_time:.1f}" if node else "N/A"
            critical = "yes" if issue.id in result.critical_issue_ids else "no"

            lines.append(
                f'"{issue.id}","{issue.title}",{issue.estimated_hours or 0},"{deps}",{slack},{critical},{issue.status}'
            )

        return "\n".join(lines)
    except Exception as e:
        logger.error(
            f"CSV formatting failed: {str(e)}",
            error=str(e),
            severity="operational",
            exc_info=True,
        )
        raise
