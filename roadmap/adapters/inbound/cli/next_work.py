"""Read-only next-work recommendations with reproducible planning time."""

import json
from dataclasses import asdict
from datetime import datetime

import click

from roadmap.adapters.inbound.cli.cli_command_helpers import invoke, require_initialized
from roadmap.application.contracts import NextWorkAction, NextWorkReport
from roadmap.domain.types import Timestamp


def _planning_time(value: str | None) -> Timestamp | None:
    if value is None:
        return None
    try:
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValueError("UTC offset required")
    except ValueError as error:
        raise click.BadParameter(
            "Use an ISO-8601 timestamp with a UTC offset, e.g. 2026-10-23T13:00:00-05:00",
            param_hint="--at",
        ) from error
    return Timestamp(parsed)


def _json(value: object) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    raise TypeError(f"Cannot encode {type(value).__name__}")


def _emit_action(record: NextWorkAction) -> None:
    click.echo(
        f"  {record.action} {record.entity_type}:{record.entity_id}: {record.title}"
    )
    click.echo(
        f"    urgency={record.urgency}; priority={record.effective_priority}; "
        f"unblocking_value={record.unblocking_value}"
    )
    click.echo(f"    Priority sources: {'; '.join(record.priority_sources)}")
    deadline = (
        record.effective_deadline.isoformat()
        if record.effective_deadline is not None
        else "unknown/not supplied in canonical data"
    )
    click.echo(f"    Deadline: {deadline}")
    _emit_details(record)


def _emit_details(record: NextWorkAction) -> None:
    details = (
        ("Deadline sources", record.deadline_sources),
        ("Requirements", record.requirement_ids),
        ("Milestones", record.milestone_ids),
        ("Reasons", record.reasons),
        ("Blockers", record.blockers),
        ("Would unblock", record.unblocks),
    )
    for label, values in details:
        if values:
            click.echo(f"    {label}: {'; '.join(values)}")


def _emit_terminal(report: NextWorkReport) -> None:
    click.echo(f"Next work as of {report.as_of.isoformat()} ({report.policy})")
    click.echo(
        "Order: critical defect, overdue, finish/review, normal; then earliest "
        "deadline, priority, direct unblocking value, action kind, UUID."
    )
    click.echo(
        "Local advice only: provider closure is not verified completion; "
        "missing data is not proof of absent remote constraints."
    )
    sections = (
        ("Current work", report.current_work),
        (
            f"Recommended (showing {len(report.recommended)} of {report.recommended_total})",
            report.recommended,
        ),
        ("Blocked", report.blocked),
    )
    for label, records in sections:
        click.echo(f"{label}: {len(records)}")
        for record in records:
            _emit_action(record)


@click.command("next-work")
@click.option(
    "--at", "planning_time", help="Planning time as ISO-8601 with UTC offset."
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["terminal", "json"]),
    default="terminal",
)
@click.option(
    "--limit", type=click.IntRange(min=1), help="Limit recommendations after ranking."
)
@click.pass_context
@require_initialized
def next_work(
    ctx: click.Context, planning_time: str | None, output_format: str, limit: int | None
) -> None:
    """Explain eligible, current and blocked work without changing it."""
    as_of = _planning_time(planning_time)
    report = invoke(
        lambda: ctx.obj["core"].requirements.next_work(as_of=as_of, limit=limit)
    )
    if output_format == "json":
        click.echo(
            json.dumps(
                {"schema_version": 1, "kind": "roadmap.next-work", **asdict(report)},
                default=_json,
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        _emit_terminal(report)
