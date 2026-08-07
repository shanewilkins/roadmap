"""Unblock issue command - thin wrapper around update.

This command is syntactic sugar for: roadmap issue update <ID> --status in-progress
"""

import click

from roadmap.adapters.cli.cli_command_helpers import require_initialized
from roadmap.common.cli_errors import handle_cli_errors
from roadmap.core.domain import Status

from .issue_status_helpers import StatusChangeConfig, apply_status_change


@click.command("unblock")
@click.argument("issue_id")
@click.option("--reason", "-r", help="Reason for unblocking")
@click.pass_context
@handle_cli_errors(command_name="issue unblock")
@require_initialized
def unblock_issue(ctx: click.Context, issue_id: str, reason: str):
    """Unblock an issue by setting status to in-progress.

    Syntactic sugar for: roadmap issue update <ID> --status in-progress
    """
    core = ctx.obj["core"]

    def check_is_blocked(issue):
        """Verify issue is currently blocked before unblocking."""
        status_val = getattr(issue.status, "value", str(issue.status))
        if status_val != "blocked":
            return False, f"Issue is not blocked (current: {status_val})"
        return True, None

    config = StatusChangeConfig(
        status=Status.IN_PROGRESS,
        emoji="✅",
        title_verb="Unblocked",
        title_style="bold green",
        status_display="🔄 In Progress",
        pre_check=check_is_blocked,
    )
    apply_status_change(core, issue_id, config, reason)
