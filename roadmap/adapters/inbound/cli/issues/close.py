"""Close an issue through the target Application boundary."""

import click

from roadmap.adapters.inbound.cli.cli_command_helpers import require_initialized
from roadmap.adapters.inbound.cli.datetime_parser import parse_user_datetime
from roadmap.adapters.inbound.cli.issues.resolution import (
    invoke,
    projection_warning,
    resolve_issue_id,
    timestamp,
)


def _completion_time(value: str | None):
    if value is None:
        return None
    parsed = parse_user_datetime(value, "UTC")
    if parsed is None:
        raise click.ClickException(
            "Invalid date format. Use YYYY-MM-DD or YYYY-MM-DD HH:MM"
        )
    return timestamp(parsed)


@click.command("close")
@click.argument("issue_id")
@click.option("--reason", "-r", help="Reason for closing the issue")
@click.option("--record-time", "-t", is_flag=True, help="Record completion time")
@click.option("--date", help="Completion date (requires --record-time)")
@click.pass_context
@require_initialized
def close_issue(
    ctx: click.Context,
    issue_id: str,
    reason: str | None,
    record_time: bool,
    date: str | None,
) -> None:
    """Close an issue in place; archiving is a separate lifecycle action."""
    if date is not None and not record_time:
        raise click.UsageError("--date requires --record-time")
    core = ctx.obj["core"]
    identity = resolve_issue_id(core, issue_id)
    completed_at = _completion_time(date)
    result = invoke(
        lambda: core.issue_mutations.close(
            identity, completed_at, reason, record_time=record_time
        )
    )
    click.echo(f"Closed issue {identity}")
    projection_warning(result)
