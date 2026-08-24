"""Canonical dependency analysis commands."""

import csv
import io
import json
from pathlib import Path

import click

from roadmap.adapters.inbound.cli.analysis.presenter import CriticalPathPresenter
from roadmap.adapters.inbound.cli.cli_command_helpers import require_initialized
from roadmap.adapters.inbound.cli.instrumentation import verbose_output
from roadmap.adapters.inbound.cli.planning_resolution import invoke
from roadmap.application.contracts import CriticalPathResult


@click.group()
def analysis() -> None:
    """Analysis and insights commands."""


@analysis.command("critical-path")
@click.option("--milestone", "-m", help="Analyze one milestone")
@click.option("--include-closed", is_flag=True, help="Include closed issues")
@click.option("--export", type=click.Choice(["json", "csv"]))
@click.option("--output", "-o", type=click.Path(dir_okay=False, path_type=Path))
@click.pass_context
@require_initialized
@verbose_output
def critical_path(
    ctx: click.Context,
    milestone: str | None,
    include_closed: bool,
    export: str | None,
    output: Path | None,
) -> None:
    """Show the longest canonical issue dependency chain."""
    result = invoke(
        lambda: ctx.obj["core"].planning.critical_path(
            milestone=milestone, include_closed=include_closed
        )
    )
    if not result.critical_path:
        suffix = f" In milestone: {milestone}" if milestone else ""
        click.echo(f"No active issues to analyze.{suffix}")
        return
    content = (
        _export(result, export)
        if export is not None
        else CriticalPathPresenter().format_critical_path(result, milestone)
    )
    if output is None:
        click.echo(content)
        return
    try:
        with output.open("x", encoding="utf-8", newline="") as stream:
            stream.write(content)
            if not content.endswith("\n"):
                stream.write("\n")
    except FileExistsError as error:
        raise click.ClickException(
            f"Refusing to overwrite existing export: {output}"
        ) from error
    except OSError as error:
        raise click.ClickException(f"Cannot write export {output}: {error}") from error
    click.echo(f"Exported critical path to {output}", err=True)


def _export(result: CriticalPathResult, format_name: str) -> str:
    if format_name == "json":
        return json.dumps(
            {
                "schema_version": 1,
                "kind": "roadmap.critical-path",
                "critical_path": [
                    {
                        "issue_id": str(node.issue_id),
                        "title": node.issue_title,
                        "duration_hours": node.duration_hours,
                        "dependencies": list(map(str, node.dependencies)),
                        "slack_time": node.slack_time,
                        "is_critical": node.is_critical,
                    }
                    for node in result.critical_path
                ],
                "summary": {
                    "total_duration": result.total_duration,
                    "critical_issue_count": len(result.critical_issue_ids),
                    "blocking_issues": {
                        str(identity): list(map(str, blocked))
                        for identity, blocked in result.blocking_issues
                    },
                    "project_end_date": (
                        result.project_end_at.value.isoformat()
                        if result.project_end_at
                        else None
                    ),
                },
            },
            indent=2,
            sort_keys=True,
        )
    stream = io.StringIO()
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(
        (
            "schema_version",
            "issue_id",
            "title",
            "duration_hours",
            "dependencies",
            "slack_hours",
            "is_critical",
        )
    )
    for node in result.critical_path:
        writer.writerow(
            (
                1,
                node.issue_id,
                node.issue_title,
                node.duration_hours,
                ",".join(map(str, node.dependencies)),
                node.slack_time,
                "yes" if node.is_critical else "no",
            )
        )
    return stream.getvalue().rstrip()
