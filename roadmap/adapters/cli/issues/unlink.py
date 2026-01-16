"""Unlink GitHub issue command."""

import click

from roadmap.adapters.cli.cli_command_helpers import require_initialized
from roadmap.adapters.cli.cli_error_handlers import handle_cli_error
from roadmap.common.console import get_console
from roadmap.common.formatters.text.operations import (
    format_operation_failure,
    format_operation_success,
)
from roadmap.common.logging import (
    log_command,
    track_database_operation,
)

console = get_console()


@click.command("unlink-github")
@click.argument("issue_id")
@click.pass_context
@log_command("issue_unlink", entity_type="issue", track_duration=True)
@require_initialized
def unlink_github_issue(ctx: click.Context, issue_id: str) -> None:
    """Remove GitHub link from a local issue.

    Args:
        issue_id: ID of the local issue to unlink
    """
    core = ctx.obj["core"]

    try:
        # Get the issue
        issue = core.issues.get(issue_id)
        if not issue:
            lines = format_operation_failure(
                action="unlink",
                entity_id=issue_id,
                error="Issue not found",
            )
            for line in lines:
                console.print(line, style="bold red")
            return

        # Check if issue is linked
        if issue.github_issue is None:
            console.print(
                f"⚠️  Issue '{issue_id}' is not linked to GitHub",
                style="yellow",
            )
            return

        # Store the GitHub ID for display
        github_id = issue.github_issue

        # Remove the link
        with track_database_operation(
            "update", "issue", entity_id=issue_id, warn_threshold_ms=2000
        ):
            updated_issue = core.issues.update(issue_id, github_issue=None)

        if updated_issue:
            extra_details = {
                "GitHub Issue": f"#{github_id}",
                "Local Issue": issue_id,
            }
            lines = format_operation_success(
                emoji="✅",
                action="Unlinked",
                entity_title=updated_issue.title,
                entity_id=issue_id,
                extra_details=extra_details,
            )
            for line in lines:
                console.print(
                    line, style="bold green" if "Unlinked" in line else "cyan"
                )
        else:
            lines = format_operation_failure(
                action="unlink",
                entity_id=issue_id,
                error="Failed to update issue",
            )
            for line in lines:
                console.print(line, style="bold red")

    except Exception as e:
        handle_cli_error(
            error=e,
            operation="unlink_github_issue",
            entity_type="issue",
            entity_id=issue_id,
            context={},
            fatal=True,
        )
        lines = format_operation_failure(
            action="unlink",
            entity_id=issue_id,
            error=str(e),
        )
        for line in lines:
            console.print(line, style="bold red")
