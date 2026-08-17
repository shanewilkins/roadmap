"""Unblock an issue through the target Application boundary."""

import click

from roadmap.adapters.cli.cli_command_helpers import require_initialized
from roadmap.adapters.cli.issues.resolution import (
    invoke,
    projection_warning,
    resolve_issue_id,
)
from roadmap.domain.types import IssueStatus


@click.command("unblock")
@click.argument("issue_id")
@click.option("--reason", "-r", help="Reason for unblocking")
@click.pass_context
@require_initialized
def unblock_issue(ctx: click.Context, issue_id: str, reason: str | None) -> None:
    """Move a blocked issue back to in-progress."""
    core = ctx.obj["core"]
    identity = resolve_issue_id(core, issue_id)
    current = invoke(lambda: core.issue_queries.view(identity)).issue
    if current.status is not IssueStatus.BLOCKED:
        raise click.ClickException(f"Issue '{identity}' is not blocked")
    result = invoke(
        lambda: core.issue_mutations.transition(
            identity, IssueStatus.IN_PROGRESS, reason
        )
    )
    click.echo(f"Unblocked issue {identity}")
    projection_warning(result)
