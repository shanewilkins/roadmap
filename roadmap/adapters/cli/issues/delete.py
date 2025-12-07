"""Delete issue command."""

import click

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
def delete_issue(
    ctx: click.Context,
    issue_id: str,
    yes: bool,
):
    """Delete an issue."""
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        raise click.Abort()

    # Check if issue exists
    issue = core.issues.get(issue_id)
    if not issue:
        console.print(f"❌ Issue not found: {issue_id}", style="bold red")
        raise click.Abort()

    # Confirm deletion if not using --yes flag
    if not yes:
        if not click.confirm(f"Are you sure you want to delete issue '{issue.title}'?"):
            console.print("[yellow]⚠️  Issue deletion cancelled[/yellow]")
            raise click.Abort()

    # Delete the issue
    with track_database_operation("delete", "issue", entity_id=issue_id):
        core.issues.delete(issue_id)

    console.print(f"[green]✅ Permanently deleted issue: {issue.title}[/green]")
    console.print(f"   ID: {issue_id}", style="dim")
