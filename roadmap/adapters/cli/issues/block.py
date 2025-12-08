"""Block issue command - thin wrapper around update.

This command is syntactic sugar for: roadmap issue update <ID> --status blocked
"""

import click

from roadmap.adapters.cli.helpers import ensure_entity_exists, require_initialized
from roadmap.common.cli_errors import handle_cli_errors
from roadmap.common.console import get_console
from roadmap.core.domain import Status

console = get_console()


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

    # Check if issue exists
    ensure_entity_exists(core, "issue", issue_id)

    # Update status to blocked via core.update_issue
    updated_issue = core.issues.update(issue_id, status=Status.BLOCKED)

    console.print(f"🚫 Blocked issue: {updated_issue.title}", style="bold red")
    console.print(f"   ID: {updated_issue.id}", style="cyan")
    console.print("   Status: 🚫 Blocked", style="red")

    if reason:
        console.print(f"   Reason: {reason}", style="dim")
