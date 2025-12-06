"""Close issue command - thin wrapper around update.

This command is syntactic sugar for: roadmap issue update <ID> --status closed
Delegates to update command for consistent business logic.
"""

from datetime import datetime

import click

from roadmap.adapters.cli.error_logging import log_error_with_context
from roadmap.adapters.cli.logging_decorators import log_command
from roadmap.adapters.cli.performance_tracking import track_database_operation
from roadmap.common.console import get_console
from roadmap.core.domain import Status

console = get_console()


@click.command("close")
@click.argument("issue_id")
@click.option("--reason", "-r", help="Reason for closing the issue")
@click.option(
    "--record-time",
    "-t",
    is_flag=True,
    help="Record actual completion time",
)
@click.option(
    "--date",
    help="Completion date (YYYY-MM-DD HH:MM, defaults to now)",
)
@click.pass_context
@log_command("issue_close", entity_type="issue", track_duration=True)
def close_issue(
    ctx: click.Context,
    issue_id: str,
    reason: str,
    record_time: bool,
    date: str,
):
    """Close an issue (sets status to closed and progress to 100%).

    Syntactic sugar for: roadmap issue update <ID> --status closed

    Options like --reason and --record-time add metadata to the update.
    """
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return

    try:
        # Check if issue exists
        issue = core.issues.get(issue_id)
        if not issue:
            console.print(f"❌ Issue not found: {issue_id}", style="bold red")
            return

        # Build update kwargs
        update_kwargs = {
            "status": Status.CLOSED,
            "progress_percentage": 100.0,
        }

        # Parse completion date if record_time is enabled
        if record_time:
            if date:
                try:
                    end_date = datetime.strptime(date, "%Y-%m-%d %H:%M")
                except ValueError:
                    try:
                        end_date = datetime.strptime(date, "%Y-%m-%d")
                    except ValueError:
                        console.print(
                            "❌ Invalid date format. Use YYYY-MM-DD or YYYY-MM-DD HH:MM",
                            style="bold red",
                        )
                        return
            else:
                end_date = datetime.now()

            update_kwargs["actual_end_date"] = end_date

        # Update the issue (this delegates to core.update_issue)
        with track_database_operation(
            "update", "issue", entity_id=issue_id, warn_threshold_ms=2000
        ):
            updated_issue = core.issues.update(issue_id, **update_kwargs)

        if updated_issue:
            console.print(f"✅ Closed: {updated_issue.title}", style="bold green")
            console.print("   Status: Closed", style="green")

            if reason:
                console.print(f"   Reason: {reason}", style="cyan")

            if record_time and update_kwargs.get("actual_end_date"):
                end_date = update_kwargs["actual_end_date"]
                console.print(
                    f"   Completed: {end_date.strftime('%Y-%m-%d %H:%M')}",
                    style="cyan",
                )

                # Show duration if we have start date
                if updated_issue.actual_start_date:
                    duration = end_date - updated_issue.actual_start_date
                    hours = duration.total_seconds() / 3600
                    console.print(f"   Duration: {hours:.1f} hours", style="cyan")

                    # Compare with estimate
                    if updated_issue.estimated_hours:
                        diff = hours - updated_issue.estimated_hours
                        if abs(diff) > 0.5:
                            if diff > 0:
                                console.print(
                                    f"   Over estimate by: {diff:.1f} hours",
                                    style="yellow",
                                )
                            else:
                                console.print(
                                    f"   Under estimate by: {abs(diff):.1f} hours",
                                    style="green",
                                )
                        else:
                            console.print("   ✅ Right on estimate!", style="green")
        else:
            console.print(f"❌ Failed to close issue: {issue_id}", style="bold red")

    except Exception as e:
        log_error_with_context(
            e,
            operation="issue_close",
            entity_type="issue",
            entity_id=issue_id,
            additional_context={"reason": reason},
        )
        console.print(f"❌ Error closing issue: {e}", style="bold red")
