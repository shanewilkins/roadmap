"""Unblock issue command."""

import click

from roadmap.shared.cli_errors import handle_cli_errors
from roadmap.shared.console import get_console

console = get_console()


@click.command("unblock")
@click.argument("issue_id")
@click.option("--reason", "-r", help="Reason for unblocking")
@click.pass_context
@handle_cli_errors(command_name="issue unblock")
def unblock_issue(ctx: click.Context, issue_id: str, reason: str):
    """Unblock an issue by setting it to in-progress status."""
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        raise click.Abort()

    issue = core.get_issue(issue_id)
    if not issue:
        console.print(f"❌ Issue not found: {issue_id}", style="bold red")
        raise click.Abort()

    if issue.status and getattr(issue.status, "value", str(issue.status)) != "blocked":
        console.print(
            f"[yellow]⚠️  Issue is not blocked (current status: {issue.status.value if hasattr(issue.status, 'value') else issue.status})[/yellow]"
        )
        return

    success = core.update_issue(
        issue_id,
        status="in-progress",
        content=(issue.content or "")
        + (f"\n\n**Unblocked:** {reason}" if reason else ""),
    )

    if success:
        updated = core.get_issue(issue_id)
        console.print(f"✅ Unblocked issue: {updated.title}", style="bold green")
        console.print(f"   ID: {issue_id}", style="cyan")
        console.print("   Status: 🔄 In Progress", style="yellow")
        if reason:
            console.print(f"   Reason: {reason}", style="cyan")
    else:
        console.print(f"❌ Failed to unblock issue: {issue_id}", style="bold red")
        raise click.Abort()
