"""Update issue command."""

import click

from roadmap.cli.utils import get_console
from roadmap.error_handling import ErrorHandler, ValidationError
from roadmap.models import Priority

console = get_console()


@click.command("update")
@click.argument("issue_id")
@click.option("--title", help="Update issue title")
@click.option(
    "--priority",
    "-p",
    type=click.Choice(["critical", "high", "medium", "low"]),
    help="Update priority",
)
@click.option(
    "--status",
    "-s",
    type=click.Choice(["todo", "in-progress", "blocked", "review", "done"]),
    help="Update status",
)
@click.option("--assignee", "-a", help="Update assignee")
@click.option("--milestone", "-m", help="Update milestone")
@click.option("--description", "-d", help="Update description")
@click.option("--estimate", "-e", type=float, help="Update estimated time (in hours)")
@click.option("--reason", "-r", help="Reason for the update")
@click.pass_context
def update_issue(
    ctx: click.Context,
    issue_id: str,
    title: str,
    priority: str,
    status: str,
    assignee: str,
    milestone: str,
    description: str,
    estimate: float,
    reason: str,
):
    """Update an existing issue."""
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

        # Build update dict
        updates = {}
        if title:
            updates["title"] = title
        if priority:
            updates["priority"] = Priority(priority)
        if status:
            updates["status"] = status
        if assignee is not None:
            # Convert empty string to None for proper unassignment
            if assignee == "":
                updates["assignee"] = None
            else:
                # Validate assignee before updating
                is_valid, result = core.validate_assignee(assignee)
                if not is_valid:
                    console.print(f"❌ Invalid assignee: {result}", style="bold red")
                    raise click.Abort()
                elif result and "Warning:" in result:
                    console.print(f"⚠️  {result}", style="bold yellow")
                    updates["assignee"] = assignee
                else:
                    canonical_assignee = core.get_canonical_assignee(assignee)
                    if canonical_assignee != assignee:
                        console.print(
                            f"🔄 Resolved '{assignee}' to '{canonical_assignee}'",
                            style="dim",
                        )
                    updates["assignee"] = canonical_assignee
        if milestone:
            updates["milestone"] = milestone
        if description:
            updates["description"] = description
        if estimate is not None:
            updates["estimated_hours"] = estimate

        if not updates:
            console.print("❌ No updates specified", style="bold red")
            raise click.Abort()

        # Update the issue
        updated_issue = core.update_issue(issue_id, **updates)

        console.print(f"✅ Updated issue: {updated_issue.title}", style="bold green")
        console.print(f"   ID: {updated_issue.id}", style="cyan")

        # Show what was updated
        for field, value in updates.items():
            if field == "estimated_hours":
                display_value = updated_issue.estimated_time_display
                console.print(f"   estimate: {display_value}", style="cyan")
            elif field in [
                "title",
                "priority",
                "status",
                "assignee",
                "milestone",
                "description",
            ]:
                console.print(f"   {field}: {value}", style="cyan")

        if reason:
            console.print(f"   reason: {reason}", style="dim")

    except click.Abort:
        raise
    except Exception as e:
        error_handler = ErrorHandler()
        error_handler.handle_error(
            ValidationError(
                "Failed to update issue",
                context={"command": "update", "issue_id": issue_id},
                cause=e,
            ),
            exit_on_critical=False,
        )
