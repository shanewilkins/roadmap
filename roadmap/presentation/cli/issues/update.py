"""Update issue command."""

import click

from roadmap.cli.utils import get_console
from roadmap.shared.errors import ErrorHandler, ValidationError

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
    from roadmap.cli.issue_update_helpers import IssueUpdateBuilder, IssueUpdateDisplay

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

        # Build update dictionary
        updates = IssueUpdateBuilder.build_updates(
            title,
            priority,
            status,
            assignee,
            milestone,
            description,
            estimate,
            core,
            console,
        )

        # Check for assignee validation failure
        if assignee is not None and "assignee" not in updates:
            raise click.Abort()

        if not updates:
            console.print("❌ No updates specified", style="bold red")
            raise click.Abort()

        # Update the issue
        updated_issue = core.update_issue(issue_id, **updates)

        # Display results
        IssueUpdateDisplay.show_update_result(updated_issue, updates, reason, console)

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
