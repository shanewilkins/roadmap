"""Delete issue command."""

import click

from roadmap.cli.utils import get_console

console = get_console()


@click.command("delete")
@click.argument("issue_id")
@click.option("--yes", is_flag=True, help="Skip confirmation prompt")
@click.pass_context
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
        return

    try:
        # Check if issue exists
        issue = core.get_issue(issue_id)
        if not issue:
            console.print(f"❌ Issue not found: {issue_id}", style="bold red")
            return

        # Confirm deletion if not using --yes flag
        if not yes:
            if not click.confirm(
                f"Are you sure you want to delete issue '{issue.title}'?"
            ):
                console.print("❌ Issue deletion cancelled.", style="yellow")
                return

        # Delete the issue
        core.delete_issue(issue_id)

        console.print(
            f"✅ Permanently deleted issue: {issue.title}", style="bold green"
        )
        console.print(f"   ID: {issue_id}", style="cyan")

    except click.Abort:
        raise
    except Exception as e:
        console.print(f"❌ Failed to delete issue: {e}", style="bold red")
