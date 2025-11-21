"""Update progress command."""

import click

from roadmap.domain import Status
from roadmap.shared.console import get_console

console = get_console()


@click.command("progress")
@click.argument("issue_id")
@click.argument("percentage", type=float)
@click.pass_context
def update_progress(ctx: click.Context, issue_id: str, percentage: float):
    """Update the progress percentage for an issue (0-100)."""
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return

    if not 0 <= percentage <= 100:
        console.print(
            "❌ Progress percentage must be between 0 and 100", style="bold red"
        )
        return

    try:
        # Get the issue
        issue = core.get_issue(issue_id)
        if not issue:
            console.print(f"❌ Issue not found: {issue_id}", style="bold red")
            return

        # Update progress
        success = core.update_issue(issue_id, progress_percentage=percentage)

        if success:
            console.print(f"📊 Updated progress: {issue.title}", style="bold green")
            console.print(f"   Progress: {percentage:.0f}%", style="cyan")

            # Auto-update status based on progress
            if percentage == 0:
                status_msg = "Todo"
            elif percentage == 100:
                status_msg = "Consider marking as done"
                console.print(
                    f"   💡 {status_msg}: roadmap issue complete {issue_id}",
                    style="dim",
                )
            else:
                status_msg = "In Progress"
                if issue.status == Status.TODO:
                    core.update_issue(issue_id, status=Status.IN_PROGRESS)
                    console.print(
                        "   Status: Auto-updated to In Progress", style="yellow"
                    )
        else:
            console.print(f"❌ Failed to update progress: {issue_id}", style="bold red")

    except Exception as e:
        console.print(f"❌ Failed to update progress: {e}", style="bold red")
