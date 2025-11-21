"""Assign issue to milestone command."""

import click

from roadmap.shared.console import get_console

console = get_console()


@click.command("assign")
@click.argument("issue_id")
@click.argument("milestone_name")
@click.pass_context
def assign_milestone(ctx: click.Context, issue_id: str, milestone_name: str):
    """Assign an issue to a milestone."""
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return

    try:
        success = core.assign_issue_to_milestone(issue_id, milestone_name)
        if success:
            console.print(
                f"✅ Assigned issue {issue_id} to milestone '{milestone_name}'",
                style="bold green",
            )
        else:
            console.print(
                f"❌ Failed to assign issue {issue_id} to milestone '{milestone_name}' - issue or milestone not found",
                style="bold red",
            )
    except Exception as e:
        console.print(f"❌ Failed to assign issue: {e}", style="bold red")
