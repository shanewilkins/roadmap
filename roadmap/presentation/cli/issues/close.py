"""Close issue command - unified replacement for 'closed' and 'finish'."""

from datetime import datetime

import click

from roadmap.presentation.cli.error_logging import log_error_with_context
from roadmap.presentation.cli.logging_decorators import log_command
from roadmap.presentation.cli.performance_tracking import track_database_operation
from roadmap.shared.console import get_console

console = get_console()


@click.command("close")
@click.argument("issue_id")
@click.option("--reason", "-r", help="Reason for closing the issue")
@click.option(
    "--record-time",
    "-t",
    is_flag=True,
    help="Record actual completion time and duration",
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
    """Close an issue (mark as done).

    Unified command that marks an issue as closed and optionally records
    completion metadata like reason and timing information.

    Git-aligned terminology: 'close' is used instead of 'closed' for consistency
    with Git workflows.
    """
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

        # Parse completion date if record_time is enabled
        end_date = None
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

        # Prepare update data
        update_data = {
            "status": "closed",
            "progress_percentage": 100.0,
        }

        if record_time and end_date:
            update_data["actual_end_date"] = end_date

        if reason:
            # Append reason to existing content
            content = issue.content or ""
            completion_note = f"\n\n**Closed:** {reason}"
            update_data["content"] = content + completion_note

        # Update the issue
        with track_database_operation(
            "update", "issue", entity_id=issue_id, warn_threshold_ms=2000
        ):
            success = core.update_issue(issue_id, **update_data)

        if success:
            # Re-fetch issue to display updated values
            updated = core.get_issue(issue_id)
            console.print(f"✅ Closed: {updated.title}", style="bold green")

            if reason:
                console.print(f"   Reason: {reason}", style="cyan")

            if record_time and end_date:
                console.print(
                    f"   Completed: {end_date.strftime('%Y-%m-%d %H:%M')}",
                    style="cyan",
                )

                # Show duration if we have start date
                if updated.actual_start_date:
                    duration = end_date - updated.actual_start_date
                    hours = duration.total_seconds() / 3600
                    console.print(f"   Duration: {hours:.1f} hours", style="cyan")

                    # Compare with estimate
                    if updated.estimated_hours:
                        diff = hours - updated.estimated_hours
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

            console.print("   Status: Closed", style="green")
        else:
            console.print(f"❌ Failed to close issue: {issue_id}", style="bold red")

    except Exception as e:
        log_error_with_context(
            e,
            operation="issue_close",
            entity_type="issue",
            entity_id=issue_id,
            additional_context={"reason": reason, "record_time": record_time},
        )
        console.print(f"❌ Error closing issue: {e}", style="bold red")
