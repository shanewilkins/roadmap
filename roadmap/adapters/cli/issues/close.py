"""Close issue command - thin wrapper around update.

This command is syntactic sugar for: roadmap issue update <ID> --status closed
"""

from datetime import datetime

import click

from roadmap.adapters.cli.helpers import require_initialized
from roadmap.common.console import get_console
from roadmap.core.domain import Status
from roadmap.infrastructure.logging import (
    log_command,
    log_error_with_context,
    track_database_operation,
)

console = get_console()


def _parse_completion_date(date_str: str) -> datetime | None:
    """Parse completion date from string.

    Args:
        date_str: Date string to parse (YYYY-MM-DD HH:MM or YYYY-MM-DD)

    Returns:
        Parsed datetime or None if parsing fails
    """
    if not date_str:
        return None

    try:
        return datetime.strptime(date_str, "%Y-%m-%d %H:%M")
    except ValueError:
        try:
            return datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            return None


def _display_close_details(
    updated_issue,
    end_date: datetime | None,
    estimated_hours: float | None,
) -> None:
    """Display extra completion details (duration, estimate comparison).

    Args:
        updated_issue: Closed issue object
        end_date: Completion date if recorded
        estimated_hours: Estimated hours for comparison
    """
    if not end_date:
        return

    console.print(
        f"   Completed: {end_date.strftime('%Y-%m-%d %H:%M')}",
        style="cyan",
    )

    # Show duration if we have start date
    start_date = updated_issue.actual_start_date
    if start_date:
        duration = end_date - start_date
        hours = duration.total_seconds() / 3600
        console.print(f"   Duration: {hours:.1f} hours", style="cyan")

        # Compare with estimate
        if estimated_hours:
            diff = hours - estimated_hours
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
@require_initialized
def close_issue(
    ctx: click.Context,
    issue_id: str,
    reason: str,
    record_time: bool,
    date: str,
):
    """Close an issue (sets status to closed and progress to 100%).

    Syntactic sugar for: roadmap issue update <ID> --status closed
    """
    core = ctx.obj["core"]

    try:
        # Validate date if provided
        end_date = None
        if record_time:
            if date:
                end_date = _parse_completion_date(date)
                if end_date is None:
                    console.print(
                        "❌ Invalid date format. Use YYYY-MM-DD or YYYY-MM-DD HH:MM",
                        style="bold red",
                    )
                    return
            else:
                end_date = datetime.now()

        # Build update kwargs with status and progress
        update_kwargs = {
            "status": Status.CLOSED,
            "progress_percentage": 100.0,
        }
        if end_date:
            update_kwargs["actual_end_date"] = end_date

        # Use wrapper for status change display
        from roadmap.adapters.cli.helpers import ensure_entity_exists

        # Verify issue exists before updating
        ensure_entity_exists(core, "issue", issue_id)

        # Update the issue
        with track_database_operation(
            "update", "issue", entity_id=issue_id, warn_threshold_ms=2000
        ):
            updated_issue = core.issues.update(issue_id, **update_kwargs)

        if updated_issue:
            # Status line
            console.print(f"✅ Closed: {updated_issue.title}", style="bold green")
            console.print("   Status: Closed", style="green")

            if reason:
                console.print(f"   Reason: {reason}", style="cyan")

            # Extra details (duration, estimate comparison, etc.)
            _display_close_details(
                updated_issue, end_date, updated_issue.estimated_hours
            )
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
