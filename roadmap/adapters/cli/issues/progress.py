"""Update progress command - thin wrapper around update.

This command is syntactic sugar for: roadmap issue update <ID> --progress <PERCENT>
"""

import click

from roadmap.adapters.cli.error_logging import log_error_with_context
from roadmap.adapters.cli.logging_decorators import log_command
from roadmap.adapters.cli.performance_tracking import track_database_operation
from roadmap.common.console import get_console
from roadmap.core.domain import Status

console = get_console()


@click.command("progress")
@click.argument("issue_id")
@click.argument("percentage", type=float)
@click.pass_context
@log_command("issue_progress", entity_type="issue", track_duration=True)
def update_progress(ctx: click.Context, issue_id: str, percentage: float):
    """Update the progress percentage for an issue (0-100).

    Syntactic sugar for: roadmap issue update <ID> --progress <PERCENT>
    """
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
        issue = core.issues.get(issue_id)
        if not issue:
            console.print(f"❌ Issue not found: {issue_id}", style="bold red")
            return

        # Update progress via core.update_issue
        with track_database_operation("update", "issue", entity_id=issue_id):
            updated = core.issues.update(issue_id, progress_percentage=percentage)

        if updated:
            console.print(f"📊 Updated progress: {issue.title}", style="bold green")
            console.print(f"   Progress: {percentage:.0f}%", style="cyan")

            # Auto-update status based on progress
            if percentage == 0:
                status_msg = "Todo"
            elif percentage == 100:
                status_msg = "Consider marking as closed"
                console.print(
                    f"   💡 {status_msg}: roadmap issue close {issue_id}",
                    style="dim",
                )
            else:
                status_msg = "In Progress"
                if issue.status == Status.TODO:
                    core.issues.update(issue_id, status=Status.IN_PROGRESS)
                    console.print(
                        "   Status: Auto-updated to In Progress", style="yellow"
                    )
        else:
            console.print(f"❌ Failed to update progress: {issue_id}", style="bold red")

    except Exception as e:
        log_error_with_context(
            e,
            operation="issue_progress",
            entity_type="issue",
            entity_id=issue_id,
            additional_context={"percentage": percentage},
        )
        console.print(f"❌ Failed to update progress: {e}", style="bold red")
