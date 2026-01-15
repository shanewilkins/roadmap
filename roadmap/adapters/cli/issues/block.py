"""Block issue command - thin wrapper around update.

This command is syntactic sugar for: roadmap issue update <ID> --status blocked
"""

import click

from roadmap.adapters.cli.cli_command_helpers import require_initialized
from roadmap.common.cli_errors import handle_cli_errors
from roadmap.core.domain import Status

from .issue_status_helpers import StatusChangeConfig, apply_status_change


@click.command("block")
@click.argument("issue_id")
@click.option("--reason", "-r", help="Reason for blocking")
@click.pass_context
@handle_cli_errors(command_name="issue block")
@require_initialized
def block_issue(
    ctx: click.Context,
    issue_id: str,
    reason: str,
):
    """Mark an issue as blocked (sets status to blocked).

    Syntactic sugar for: roadmap issue update <ID> --status blocked
    """
    core = ctx.obj["core"]

    config = StatusChangeConfig(
        status=Status.BLOCKED,
        emoji="🚫",
        title_verb="Blocked",
        title_style="bold red",
        status_display="🚫 Blocked",
    )
    apply_status_change(core, issue_id, config, reason)
