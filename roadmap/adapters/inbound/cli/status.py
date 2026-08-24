"""Deterministic roadmap status and workspace-health entry points."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import click

from roadmap.adapters.inbound.cli.cli_command_helpers import require_initialized
from roadmap.adapters.inbound.cli.console import get_console
from roadmap.adapters.inbound.cli.health.commands import check_health, health
from roadmap.adapters.inbound.cli.models import ColumnDef, ColumnType, TableData
from roadmap.adapters.inbound.cli.output_formatter import OutputFormatter
from roadmap.domain.types import (
    IssueStatus,
    MilestoneStatus,
    ProjectStatus,
    RetentionState,
)


@click.command()
@click.option("--verbose", "verbose", "-v", is_flag=True)
@click.option(
    "--format",
    "format_name",
    "-f",
    type=click.Choice(["rich", "plain", "json", "csv", "markdown"]),
    default="rich",
)
@click.option(
    "--output",
    "output",
    "-o",
    type=click.Path(dir_okay=False, writable=True, path_type=Path),
)
@click.pass_context
@require_initialized
def status(
    ctx: click.Context, verbose: bool, format_name: str, output: Path | None
) -> None:
    """Show a deterministic snapshot of canonical Roadmap entities."""
    del verbose
    try:
        tables = _build_snapshot_tables(ctx.obj["core"].planning)
        _render_snapshot_tables(
            tables, ["entities", "issue_status"], format_name, output
        )
    except click.ClickException:
        raise
    except Exception as error:
        raise click.ClickException(f"Cannot build roadmap status: {error}") from error


def _render_snapshot_tables(
    tables_by_name: dict[str, TableData],
    ordered_names: list[str],
    format_name: str,
    output_path: Path | None,
) -> None:
    normalized = format_name.casefold()
    export_format = "plain" if normalized == "rich" else normalized
    if output_path is not None:
        content = _format_snapshot_content(tables_by_name, ordered_names, export_format)
        try:
            with output_path.open("x", encoding="utf-8", newline="") as stream:
                stream.write(content)
        except FileExistsError as error:
            raise click.ClickException(
                f"Refusing to overwrite existing output: {output_path}"
            ) from error
        except OSError as error:
            raise click.ClickException(
                f"Cannot write status output {output_path}: {error}"
            ) from error
        click.echo(f"Saved status to {output_path}", err=True)
        return
    if normalized == "rich":
        click.secho("Roadmap Status", bold=True)
        for index, name in enumerate(ordered_names):
            get_console().print(OutputFormatter(tables_by_name[name]).to_rich())
            if index < len(ordered_names) - 1:
                click.echo()
        return
    click.echo(
        _format_snapshot_content(tables_by_name, ordered_names, normalized), nl=False
    )


def _format_snapshot_content(
    tables_by_name: dict[str, TableData], ordered_names: list[str], format_name: str
) -> str:
    if format_name == "json":
        return (
            json.dumps(
                {
                    "schema_version": 1,
                    "kind": "roadmap.status",
                    "tables": {
                        name: tables_by_name[name].to_dict() for name in ordered_names
                    },
                },
                indent=2,
                sort_keys=True,
                default=str,
            )
            + "\n"
        )
    parts: list[str] = []
    for name in ordered_names:
        table = tables_by_name[name]
        formatter = OutputFormatter(table)
        if format_name == "plain":
            parts.append(formatter.to_plain_text())
        elif format_name == "csv":
            parts.extend((f"# {table.title or name}", formatter.to_csv().rstrip()))
        elif format_name == "markdown":
            parts.append(formatter.to_markdown())
        else:
            raise click.ClickException(f"Unsupported status format: {format_name}")
    return "\n\n".join(part for part in parts if part) + "\n"


def _build_snapshot_tables(planning) -> dict[str, TableData]:
    projects = planning.all_projects()
    milestones = planning.all_milestones()
    issues = planning.all_issues()
    visible_projects = tuple(
        item for item in projects if item.retention is RetentionState.VISIBLE
    )
    visible_milestones = tuple(
        item for item in milestones if item.retention is RetentionState.VISIBLE
    )
    visible_issues = tuple(
        item for item in issues if item.retention is RetentionState.VISIBLE
    )
    project_counts = Counter(item.status for item in visible_projects)
    milestone_counts = Counter(item.status for item in visible_milestones)
    issue_counts = Counter(item.status for item in visible_issues)
    archived_projects = sum(
        item.retention is RetentionState.ARCHIVED for item in projects
    )
    archived_milestones = sum(
        item.retention is RetentionState.ARCHIVED for item in milestones
    )
    archived_issues = sum(item.retention is RetentionState.ARCHIVED for item in issues)
    project_open = sum(
        project_counts[item]
        for item in (
            ProjectStatus.PLANNING,
            ProjectStatus.ACTIVE,
            ProjectStatus.ON_HOLD,
        )
    )
    project_closed = sum(
        project_counts[item]
        for item in (ProjectStatus.COMPLETED, ProjectStatus.CANCELLED)
    )
    milestone_open = milestone_counts[MilestoneStatus.OPEN]
    milestone_closed = milestone_counts[MilestoneStatus.CLOSED]
    issue_open = sum(
        issue_counts[item]
        for item in (
            IssueStatus.TODO,
            IssueStatus.IN_PROGRESS,
            IssueStatus.BLOCKED,
            IssueStatus.REVIEW,
        )
    )
    issue_closed = issue_counts[IssueStatus.CLOSED]
    entity_rows = [
        ["Projects", project_open, project_closed, archived_projects, len(projects)],
        [
            "Milestones",
            milestone_open,
            milestone_closed,
            archived_milestones,
            len(milestones),
        ],
        ["Issues", issue_open, issue_closed, archived_issues, len(issues)],
        [
            "Total",
            project_open + milestone_open + issue_open,
            project_closed + milestone_closed + issue_closed,
            archived_projects + archived_milestones + archived_issues,
            len(projects) + len(milestones) + len(issues),
        ],
    ]
    entities = TableData(
        columns=[
            ColumnDef("entity", "Entity", ColumnType.STRING, width=12),
            ColumnDef("open", "Open", ColumnType.INTEGER, width=6),
            ColumnDef("closed", "Closed", ColumnType.INTEGER, width=7),
            ColumnDef("archived", "Archived", ColumnType.INTEGER, width=9),
            ColumnDef("total", "Total", ColumnType.INTEGER, width=6),
        ],
        rows=entity_rows,
        title="Entities",
    )
    status_rows = [[item.value, issue_counts[item]] for item in IssueStatus]
    status_rows.extend((["archived", archived_issues], ["Total", len(issues)]))
    issue_status = TableData(
        columns=[
            ColumnDef("status", "Status", ColumnType.STRING, width=14),
            ColumnDef("count", "Count", ColumnType.INTEGER, width=7),
        ],
        rows=status_rows,
        title="Issue Status",
    )
    return {"entities": entities, "issue_status": issue_status}


__all__ = ["check_health", "health", "status"]
