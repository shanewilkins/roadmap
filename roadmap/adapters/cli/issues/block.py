"""Block an issue through the target Application boundary."""

import click

from roadmap.adapters.cli.cli_command_helpers import require_initialized
from roadmap.adapters.cli.issues.resolution import (
    invoke,
    projection_warning,
    resolve_issue_id,
)
from roadmap.domain.types import IssueStatus


@click.command("block")
@click.argument("issue_id")
@click.option("--reason", "-r", help="Reason for blocking")
@click.pass_context
@require_initialized
def block_issue(ctx: click.Context, issue_id: str, reason: str | None) -> None:
    """Mark an issue as blocked."""
    core = ctx.obj["core"]
    identity = resolve_issue_id(core, issue_id)
    result = invoke(
        lambda: core.issue_mutations.transition(identity, IssueStatus.BLOCKED, reason)
    )
    click.echo(f"Blocked issue {identity}")
    projection_warning(result)
