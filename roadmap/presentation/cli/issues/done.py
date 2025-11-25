"""Done issue command."""

import click

from roadmap.presentation.cli.logging_decorators import log_command
from roadmap.shared.console import get_console

console = get_console()


@click.command("done")
@click.argument("issue_id")
@click.option("--reason", "-r", help="Reason for marking as done")
@click.pass_context
@log_command("issue_done", entity_type="issue", track_duration=True)
def done_issue(
    ctx: click.Context,
    issue_id: str,
    reason: str,
):
    """Mark an issue as done."""
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

        # Update status to done
        updated_issue = core.update_issue(issue_id, status="done")

        console.print(f"✅ Finished: {updated_issue.title}", style="bold green")
        console.print(f"   ID: {updated_issue.id}", style="cyan")

        if reason:
            console.print(f"   Reason: {reason}", style="dim")

    except click.Abort:
        raise
    except Exception as e:
        console.print(f"❌ Failed to mark issue as done: {e}", style="bold red")
