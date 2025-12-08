"""Delete issue command."""

import click

from roadmap.adapters.cli.helpers import (
    confirm_action,
    ensure_entity_exists,
    require_initialized,
)
from roadmap.common.cli_errors import handle_cli_errors
from roadmap.common.console import get_console
from roadmap.infrastructure.logging import log_command, track_database_operation

console = get_console()


@click.command("delete")
@click.argument("issue_id")
@click.option("--yes", is_flag=True, help="Skip confirmation prompt")
@click.pass_context
@handle_cli_errors(command_name="issue delete")
@log_command("issue_delete", entity_type="issue", track_duration=True)
@require_initialized
def delete_issue(
    ctx: click.Context,
    issue_id: str,
    yes: bool,
):
    """Delete an issue."""
    core = ctx.obj["core"]

    # Check if issue exists
    issue = ensure_entity_exists(core, "issue", issue_id)

    # Confirm deletion if not using --yes flag
    if not yes and not confirm_action(
        f"Are you sure you want to delete issue '{issue.title}'?",
        default=False,
    ):
        console.print("[yellow]⚠️  Issue deletion cancelled[/yellow]")
        raise click.Abort()

    # Delete the issue
    with track_database_operation("delete", "issue", entity_id=issue_id):
        core.issues.delete(issue_id)

    console.print(f"[green]✅ Permanently deleted issue: {issue.title}[/green]")
    console.print(f"   ID: {issue_id}", style="dim")
