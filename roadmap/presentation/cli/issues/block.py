"""Block issue command."""

import click

from roadmap.shared.console import get_console

console = get_console()


@click.command("block")
@click.argument("issue_id")
@click.option("--reason", "-r", help="Reason for blocking")
@click.pass_context
def block_issue(
    ctx: click.Context,
    issue_id: str,
    reason: str,
):
    """Mark an issue as blocked."""
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

        # Update status to blocked
        updated_issue = core.update_issue(issue_id, status="blocked")

        console.print(f"🚫 Blocked issue: {updated_issue.title}", style="bold red")
        console.print(f"   ID: {updated_issue.id}", style="cyan")
        console.print("   Status: 🚫 Blocked", style="red")

        if reason:
            console.print(f"   Reason: {reason}", style="dim")

    except click.Abort:
        raise
    except Exception as e:
        console.print(f"❌ Failed to block issue: {e}", style="bold red")
