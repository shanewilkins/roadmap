"""Close issue command - thin wrapper around update.

This command is syntactic sugar for: roadmap issue update <ID> --status closed

SEMANTICS:
- Close: Changes status to 'closed', keeps files in place (no file movement), archived=false
- Archive: Moves files to archive directory AND sets archived=true flag (signals sync to delete remotely)

This separation allows for flexible status management without workspace reorganization.
"""

from datetime import UTC, datetime

import click
from structlog import get_logger

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
from roadmap.core.domain import Status

console = get_console()
logger = get_logger()


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
    except ValueError as e:
        from roadmap.common.logging import get_logger

        logger = get_logger(__name__)
        logger.debug(
            "datetime_parse_failed",
            date_str=date_str,
            error=str(e),
            action="parse_close_date",
        )
        try:
            return datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError as e:
            logger.debug(
                "completion_date_parse_failed", date_str=date_str, error=str(e)
            )
            return None


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
                end_date = datetime.now(UTC)

        # Build update kwargs with status and progress
        update_kwargs = {
            "status": Status.CLOSED,
            "progress_percentage": 100.0,
        }
        if end_date:
            update_kwargs["actual_end_date"] = end_date

        # Use wrapper for status change display
        from roadmap.adapters.cli.cli_command_helpers import ensure_entity_exists

        # Verify issue exists before updating
        ensure_entity_exists(core, "issue", issue_id)

        # Update the issue
        with track_database_operation(
            "update", "issue", entity_id=issue_id, warn_threshold_ms=2000
        ):
            updated_issue = core.issues.update(issue_id, **update_kwargs)

        if updated_issue:
            # Build extra details
            extra_details = {
                "Status": "Closed",
                "Progress": "100%",
            }

            if reason:
                extra_details["Reason"] = reason

            # Add duration info if we have dates
            if end_date:
                extra_details["Completed"] = end_date.strftime("%Y-%m-%d %H:%M")
                start_date = updated_issue.actual_start_date
                if start_date:
                    duration = end_date - start_date
                    hours = duration.total_seconds() / 3600
                    extra_details["Duration"] = f"{hours:.1f} hours"

                    # Compare with estimate
                    if updated_issue.estimated_hours:
                        diff = hours - updated_issue.estimated_hours
                        if abs(diff) > 0.5:
                            if diff > 0:
                                extra_details["Variance"] = f"Over by {diff:.1f} hours"
                            else:
                                extra_details["Variance"] = (
                                    f"Under by {abs(diff):.1f} hours"
                                )
                        else:
                            extra_details["Variance"] = "On target"

            # Use formatter
            lines = format_operation_success(
                emoji="✅",
                action="Closed",
                entity_title=updated_issue.title,
                entity_id=issue_id,
                extra_details=extra_details,
            )
            for line in lines:
                console.print(line, style="bold green" if "Closed" in line else "cyan")
        else:
            lines = format_operation_failure(
                action="close",
                entity_id=issue_id,
                error="Failed to update status",
            )
            for line in lines:
                console.print(line, style="bold red")

    except Exception as e:
        handle_cli_error(
            error=e,
            operation="close_issue",
            entity_type="issue",
            entity_id=issue_id,
            context={"reason": reason},
            fatal=True,
        )
        lines = format_operation_failure(
            action="close",
            entity_id=issue_id,
            error=str(e),
        )
        for line in lines:
            console.print(line, style="bold red")
