"""Update issue command."""

import click

from roadmap.common.console import get_console
from roadmap.common.errors import ErrorHandler, ValidationError
from roadmap.core.services import IssueUpdateService
from roadmap.infrastructure.logging import (
    log_command,
    log_error_with_context,
    track_database_operation,
)


def _get_console():
    """Get console instance at runtime to respect Click's test environment."""
    return get_console()


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
    type=click.Choice(["todo", "in-progress", "blocked", "review", "closed"]),
    help="Update status",
)
@click.option("--assignee", "-a", help="Update assignee")
@click.option("--milestone", "-m", help="Update milestone")
@click.option("--description", "-d", help="Update description")
@click.option("--estimate", "-e", type=float, help="Update estimated time (in hours)")
@click.option("--reason", "-r", help="Reason for the update")
@click.pass_context
@log_command("issue_update", entity_type="issue", track_duration=True)
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
        _get_console().print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return

    try:
        # Create issue update service
        service = IssueUpdateService(core)

        # Check if issue exists
        issue = core.issues.get(issue_id)
        if not issue:
            _get_console().print(f"❌ Issue not found: {issue_id}", style="bold red")
            return

        # Build update dictionary
        updates = service.build_update_dict(
            title,
            priority,
            status,
            assignee,
            milestone,
            description,
            estimate,
        )

        # Check for assignee validation failure
        if assignee is not None and "assignee" not in updates:
            raise click.Abort()

        if not updates:
            _get_console().print("❌ No updates specified", style="bold red")
            raise click.Abort()

        # Update the issue
        with track_database_operation(
            "update", "issue", entity_id=issue_id, warn_threshold_ms=2000
        ):
            updated_issue = core.issues.update(issue_id, **updates)

        # Display results
        service.display_update_result(updated_issue, updates, reason)

    except click.Abort:
        raise
    except Exception as e:
        log_error_with_context(
            e,
            operation="issue_update",
            entity_type="issue",
            entity_id=issue_id,
            additional_context={"title": title},
        )
        error_handler = ErrorHandler()
        error_handler.handle_error(
            ValidationError(
                "Failed to update issue",
                context={"command": "update", "issue_id": issue_id},
                cause=e,
            ),
            exit_on_critical=False,
        )
