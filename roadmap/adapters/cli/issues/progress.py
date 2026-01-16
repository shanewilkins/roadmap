"""Update progress command - thin wrapper around update.

This command is syntactic sugar for: roadmap issue update <ID> --progress <PERCENT>
"""

import click

from roadmap.adapters.cli.cli_command_helpers import (
    ensure_entity_exists,
    require_initialized,
)
from roadmap.adapters.cli.cli_error_handlers import handle_cli_error
from roadmap.common.console import get_console
from roadmap.common.formatters.text.operations import (
    format_operation_failure,
    format_operation_success,
)
from roadmap.core.domain import Status
from roadmap.infrastructure.logging import (
    log_command,
    track_database_operation,
)

console = get_console()


@click.command("progress")
@click.argument("issue_id")
@click.argument("percentage", type=float)
@click.pass_context
@log_command("issue_progress", entity_type="issue", track_duration=True)
@require_initialized
def update_progress(ctx: click.Context, issue_id: str, percentage: float):
    """Update the progress percentage for an issue (0-100).

    Syntactic sugar for: roadmap issue update <ID> --progress <PERCENT>
    """
    core = ctx.obj["core"]

    if not 0 <= percentage <= 100:
        console.print(
            "❌ Progress percentage must be between 0 and 100", style="bold red"
        )
        return

    try:
        # Get the issue
        issue = ensure_entity_exists(core, "issue", issue_id)

        # Update progress via core.update_issue
        with track_database_operation("update", "issue", entity_id=issue_id):
            updated = core.issues.update(issue_id, progress_percentage=percentage)

        if updated:
            # Build extra details for display
            extra_details = {"Progress": f"{percentage:.0f}%"}

            # Auto-update status based on progress
            if percentage == 0:
                extra_details["Note"] = "Resetting to todo"
            elif percentage == 100:
                extra_details["Tip"] = "roadmap issue close to mark complete"
            else:
                if issue.status == Status.TODO:
                    core.issues.update(issue_id, status=Status.IN_PROGRESS)
                    extra_details["Status"] = "Auto-updated to In Progress"

            # Display success with formatter
            lines = format_operation_success(
                emoji="📊",
                action="Updated progress",
                entity_title=issue.title,
                entity_id=issue_id,
                extra_details=extra_details,
            )
            for line in lines:
                console.print(line, style="bold green" if "Updated" in line else "cyan")
        else:
            lines = format_operation_failure(
                action="update progress",
                entity_id=issue_id,
                error="No changes made",
            )
            for line in lines:
                console.print(line, style="bold red")

    except Exception as e:
        handle_cli_error(
            error=e,
            operation="update_issue_progress",
            entity_type="issue",
            entity_id=issue_id,
            context={"percentage": percentage},
            fatal=True,
        )
        lines = format_operation_failure(
            action="update progress",
            entity_id=issue_id,
            error=str(e),
        )
        for line in lines:
            console.print(line, style="bold red")
