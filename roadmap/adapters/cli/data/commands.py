"""Deterministic canonical issue exports."""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path
from typing import Any

import click

from roadmap.adapters.cli.cli_command_helpers import require_initialized
from roadmap.adapters.cli.planning_resolution import invoke
from roadmap.application.contracts import IssueListQuery, IssueQueryRecord, IssueScope

EXPORT_SCHEMA_VERSION = 1
CSV_FIELDS = (
    "schema_version",
    "id",
    "title",
    "status",
    "retention",
    "priority",
    "issue_type",
    "assignee",
    "milestone_id",
    "estimated_hours",
    "due_at",
    "created",
    "updated",
    "labels",
    "depends_on",
    "blocks",
)


@click.group()
def data() -> None:
    """Export and inspect canonical Roadmap data."""


@data.command("export")
@click.option(
    "--format",
    "format_name",
    type=click.Choice(["json", "csv", "markdown"]),
    default="json",
    show_default=True,
)
@click.option("--output", "-o", type=click.Path(dir_okay=False, path_type=Path))
@click.option("--filter", "filter_value", help="One documented key=value filter")
@click.pass_context
@require_initialized
def export(
    ctx: click.Context, format_name: str, output: Path | None, filter_value: str | None
) -> None:
    """Export canonical issues without provider or projection metadata."""
    result = invoke(lambda: ctx.obj["core"].issue_queries.list(_query(filter_value)))
    records = tuple(sorted(result.records, key=lambda item: str(item.issue.id)))
    content = _render(records, format_name)
    if output is None:
        click.echo(content, nl=False)
        return
    try:
        with output.open("x", encoding="utf-8", newline="") as stream:
            stream.write(content)
    except FileExistsError as error:
        raise click.ClickException(
            f"Refusing to overwrite existing export: {output}"
        ) from error
    except OSError as error:
        raise click.ClickException(f"Cannot write export {output}: {error}") from error
    click.echo(f"Exported {len(records)} issues to {output}", err=True)


def _query(value: str | None) -> IssueListQuery:
    if value is None:
        return IssueListQuery(scope=IssueScope.ALL)
    if "=" not in value:
        raise click.BadParameter("filter must use key=value", param_hint="--filter")
    key, expected = (part.strip() for part in value.split("=", 1))
    if not key or not expected:
        raise click.BadParameter("filter must use key=value", param_hint="--filter")
    if key == "status":
        return IssueListQuery(
            scope=IssueScope.ALL,
            open_only=expected == "open",
            status=None if expected == "open" else expected,
        )
    if key == "priority":
        return IssueListQuery(scope=IssueScope.ALL, priority=expected)
    if key == "issue_type":
        return IssueListQuery(scope=IssueScope.ALL, issue_type=expected)
    if key == "assignee":
        return IssueListQuery(scope=IssueScope.ALL, assignee=expected)
    if key == "retention":
        try:
            return IssueListQuery(scope=IssueScope(expected))
        except ValueError as error:
            raise click.BadParameter(
                "retention must be visible, closed, archived, or all",
                param_hint="--filter",
            ) from error
    raise click.BadParameter(
        "supported filter keys are status, priority, issue_type, assignee, and retention",
        param_hint="--filter",
    )


def _timestamp(value: Any) -> str | None:
    return None if value is None else value.value.isoformat()


def _issue_record(record: IssueQueryRecord) -> dict[str, Any]:
    issue = record.issue
    return {
        "schema_version": EXPORT_SCHEMA_VERSION,
        "id": str(issue.id),
        "title": str(issue.title),
        "headline": issue.headline,
        "content": issue.content,
        "status": issue.status.value,
        "retention": issue.retention.value,
        "priority": issue.priority.value,
        "issue_type": issue.issue_type.value,
        "assignee": issue.assignee,
        "milestone_id": str(issue.relations.milestone_id)
        if issue.relations.milestone_id is not None
        else None,
        "depends_on": sorted(map(str, issue.relations.depends_on)),
        "blocks": sorted(map(str, issue.relations.blocks)),
        "labels": sorted(issue.labels),
        "estimated_hours": issue.estimated_hours,
        "due_at": _timestamp(issue.due_at),
        "progress_percentage": issue.progress_percentage,
        "actual_start_at": _timestamp(issue.actual_start_at),
        "actual_end_at": _timestamp(issue.actual_end_at),
        "git_branches": sorted(issue.git_branches),
        "created": _timestamp(issue.created),
        "updated": _timestamp(issue.updated),
        "comments": [
            {
                "id": comment.id,
                "author": comment.author,
                "body": comment.body,
                "created_at": _timestamp(comment.created_at),
                "updated_at": _timestamp(comment.updated_at),
                "in_reply_to": comment.in_reply_to,
            }
            for comment in sorted(issue.comments, key=lambda item: item.id)
        ],
        "history": [
            {"action": event.action, "at": _timestamp(event.at), "reason": event.reason}
            for event in issue.history
        ],
    }


def _render(records: tuple[IssueQueryRecord, ...], format_name: str) -> str:
    rows = [_issue_record(record) for record in records]
    if format_name == "json":
        return (
            json.dumps(
                {
                    "schema_version": EXPORT_SCHEMA_VERSION,
                    "kind": "roadmap.issue-export",
                    "issues": rows,
                },
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n"
        )
    if format_name == "csv":
        stream = io.StringIO(newline="")
        writer = csv.DictWriter(stream, fieldnames=CSV_FIELDS, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    field: json.dumps(
                        row[field], ensure_ascii=False, separators=(",", ":")
                    )
                    if field in {"labels", "depends_on", "blocks"}
                    else row[field]
                    for field in CSV_FIELDS
                }
            )
        return stream.getvalue()
    lines = [
        "---",
        f"schema_version: {EXPORT_SCHEMA_VERSION}",
        "kind: roadmap.issue-export",
        "---",
        "",
        "| ID | Title | Status | Priority | Assignee | Milestone |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        cells = (
            row["id"],
            row["title"],
            row["status"],
            row["priority"],
            row["assignee"] or "",
            row["milestone_id"] or "",
        )
        lines.append("| " + " | ".join(_markdown(cell) for cell in cells) + " |")
    return "\n".join(lines) + "\n"


def _markdown(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", "<br>")
