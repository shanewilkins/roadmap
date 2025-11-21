"""Delete milestone command."""

import click

from roadmap.shared.console import get_console

console = get_console()


@click.command("delete")
@click.argument("milestone_name")
@click.option("--force", is_flag=True, help="Skip confirmation prompt")
@click.pass_context
def delete_milestone(ctx: click.Context, milestone_name: str, force: bool):
    """Delete a milestone."""
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return

    try:
        if not force:
            if not click.confirm(
                f"Are you sure you want to delete milestone '{milestone_name}'?"
            ):
                console.print("❌ Milestone deletion cancelled.", style="yellow")
                return

        success = core.delete_milestone(milestone_name)
        if success:
            console.print(f"✅ Deleted milestone: {milestone_name}", style="bold green")
        else:
            console.print(f"❌ Milestone not found: {milestone_name}", style="bold red")
    except Exception as e:
        console.print(f"❌ Failed to delete milestone: {e}", style="bold red")
