"""Update milestone command."""

from datetime import datetime

import click

from roadmap.cli.utils import get_console

console = get_console()


@click.command("update")
@click.argument("milestone_name")
@click.option("--name", help="Update milestone name")
@click.option("--description", "-d", help="Update milestone description")
@click.option("--due-date", help="Update due date (YYYY-MM-DD format)")
@click.option(
    "--status",
    type=click.Choice(["open", "closed"]),
    help="Set milestone status (open|closed)",
)
@click.option("--clear-due-date", is_flag=True, help="Clear the due date")
@click.pass_context
def update_milestone(
    ctx: click.Context,
    milestone_name: str,
    name: str,
    description: str,
    due_date: str,
    status: str,
    clear_due_date: bool,
):
    """Update an existing milestone."""
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return

    try:
        # Check if milestone exists
        milestone = core.get_milestone(milestone_name)
        if not milestone:
            console.print(f"❌ Milestone not found: {milestone_name}", style="bold red")
            return

        # Build update dict
        updates = {}
        if name:
            updates["name"] = name
        if description:
            updates["description"] = description
        if clear_due_date:
            updates["due_date"] = None
        elif due_date:
            if due_date.lower() == "clear":
                updates["due_date"] = None
            else:
                try:
                    parsed_due_date = datetime.strptime(due_date, "%Y-%m-%d")
                    updates["due_date"] = parsed_due_date
                except ValueError:
                    console.print(
                        "❌ Invalid due date format. Use YYYY-MM-DD (e.g., 2024-12-31)",
                        style="bold red",
                    )
                    return

        if status:
            # Map CLI status string to MilestoneStatus enum
            try:
                from roadmap.domain import MilestoneStatus

                # MilestoneStatus expects 'open' or 'closed' values
                updates["status"] = MilestoneStatus(status)
            except Exception:
                # Fallback to raw string if mapping fails
                updates["status"] = status

        if not updates:
            console.print("❌ No updates specified", style="bold red")
            return

        # Update the milestone
        success = core.update_milestone(milestone_name, **updates)

        if not success:
            console.print(
                f"❌ Failed to update milestone: {milestone_name}", style="bold red"
            )
            return

        # Re-fetch the milestone to show updated values
        updated_milestone = core.get_milestone(updates.get("name", milestone_name))

        console.print(
            f"✅ Updated milestone: {updated_milestone.name}", style="bold green"
        )
        console.print(f"   Description: {updated_milestone.description}", style="cyan")
        if updated_milestone.due_date:
            console.print(
                f"   Due Date: {updated_milestone.due_date.strftime('%Y-%m-%d')}",
                style="yellow",
            )
        elif clear_due_date:
            console.print("   Due Date: Cleared", style="dim")

    except Exception as e:
        console.print(f"❌ Failed to update milestone: {e}", style="bold red")
