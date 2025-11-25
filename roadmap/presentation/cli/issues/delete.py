"""Delete issue command."""

import click

from roadmap.presentation.cli.logging_decorators import log_command
from roadmap.presentation.cli.performance_tracking import track_database_operation
from roadmap.shared.cli_errors import handle_cli_errors
from roadmap.shared.console import get_console

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
    issue = core.get_issue(issue_id)
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
        core.delete_issue(issue_id)

    console.print(f"[green]✅ Permanently deleted issue: {issue.title}[/green]")
    console.print(f"   ID: {issue_id}", style="dim")
