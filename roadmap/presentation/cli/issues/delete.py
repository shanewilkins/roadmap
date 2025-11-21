"""Delete issue command."""

import click

from roadmap.shared.console import get_console
from roadmap.shared.cli_errors import CLIErrorHandler, handle_cli_errors

console = get_console()
error_handler = CLIErrorHandler()


@click.command("delete")
@click.argument("issue_id")
@click.option("--yes", is_flag=True, help="Skip confirmation prompt")
@click.pass_context
@handle_cli_errors(command_name="issue delete")
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
        if not click.confirm(
            f"Are you sure you want to delete issue '{issue.title}'?"
        ):
            error_handler.handle_warning("Issue deletion cancelled")
            raise click.Abort()

    # Delete the issue
    core.delete_issue(issue_id)

    error_handler.handle_success(
        f"Permanently deleted issue: {issue.title}",
        console,
        {"ID": issue_id},
    )
