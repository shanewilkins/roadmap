"""Close milestone command."""

import click

from roadmap.adapters.cli.helpers import require_initialized
from roadmap.common.console import get_console
from roadmap.common.formatters import format_operation_failure, format_operation_success
from roadmap.infrastructure.logging import (
    log_command,
    log_error_with_context,
    track_database_operation,
)

console = get_console()


def _display_open_issues(milestone_name: str, open_issues: list) -> None:
    """Display open issues in milestone and provide guidance.

    Args:
        milestone_name: Name of milestone
        open_issues: List of open issues
    """
    console.print(
        f"\n⚠️  Cannot close milestone: {len(open_issues)} open issue(s) remain",
        style="bold yellow",
    )
    console.print(f"\n📋 Open issues in '{milestone_name}':", style="cyan")

    for issue in open_issues[:10]:  # Show first 10
        console.print(
            f"   • {issue.id[:8]} - {issue.title} [{issue.status.value}]",
            style="dim",
        )

    if len(open_issues) > 10:
        console.print(f"   ... and {len(open_issues) - 10} more", style="dim")

    console.print(
        "\n💡 Options to proceed:",
        style="cyan",
    )
    console.print(
        "   1. Close the open issues: roadmap issue close <issue_id>",
        style="dim",
    )
    console.print(
        "   2. Migrate to backlog: roadmap issue update <issue_id> --milestone ''",
        style="dim",
    )
    console.print(
        "   3. Move to a different milestone: roadmap issue update <issue_id> --milestone 'New Milestone'",
        style="dim",
    )
    console.print(
        f"   4. Use --force to close anyway (not recommended): roadmap milestone close '{milestone_name}' --force",
        style="dim",
    )


def _confirm_milestone_close(
    milestone_name: str, total_issues: int, force: bool
) -> bool:
    """Confirm milestone closure with user.

    Args:
        milestone_name: Name of milestone
        total_issues: Total number of issues
        force: Skip confirmation if True

    Returns:
        True if user confirmed or force is True
    """
    if force:
        return True

    return click.confirm(
        f"Close milestone '{milestone_name}'? All {total_issues} issue(s) are completed."
    )


def _close_milestone_in_db(core, milestone_name: str) -> bool:
    """Close milestone in database.

    Args:
        core: RoadmapCore instance
        milestone_name: Name of milestone

    Returns:
        True if successful
    """
    from roadmap.core.domain import MilestoneStatus

    with track_database_operation("update", "milestone"):
        return core.milestones.update(milestone_name, status=MilestoneStatus.CLOSED)


@click.command("close")
@click.argument("milestone_name")
@click.option("--force", is_flag=True, help="Skip confirmation prompt")
@click.pass_context
@require_initialized
@log_command("milestone_close", entity_type="milestone", track_duration=True)
def close_milestone(ctx: click.Context, milestone_name: str, force: bool):
    """Close a milestone.

    Validates that all issues in the milestone are closed before allowing closure.
    If there are open issues, provides guidance on migration options.
    """
    core = ctx.obj["core"]

    try:
        # Check if milestone exists
        milestone = core.milestones.get(milestone_name)
        if not milestone:
            lines = format_operation_failure(
                "Close", milestone_name, "Milestone not found"
            )
            for line in lines:
                console.print(line, style="bold red")
            return

        # Get all issues in this milestone
        all_issues = core.issues.list(milestone=milestone_name)

        # Filter for open issues (not closed)
        open_issues = [issue for issue in all_issues if issue.status.value != "closed"]

        # If there are open issues, provide guidance and return
        if open_issues:
            _display_open_issues(milestone_name, open_issues)
            return

        # All issues are closed, confirm and proceed
        if not _confirm_milestone_close(milestone_name, len(all_issues), force):
            console.print("❌ Milestone close cancelled.", style="yellow")
            return

        # Close milestone in database
        success = _close_milestone_in_db(core, milestone_name)

        if success:
            extra_details = {"Completed issues": str(len(all_issues))}
            lines = format_operation_success(
                "✅", "Closed", milestone_name, "", None, extra_details
            )
            for line in lines:
                console.print(line, style="green")
        else:
            lines = format_operation_failure(
                "Close", milestone_name, "Failed to update status"
            )
            for line in lines:
                console.print(line, style="bold red")

    except Exception as e:
        log_error_with_context(
            e,
            operation="milestone_close",
            entity_type="milestone",
            additional_context={"milestone_name": milestone_name},
        )
        lines = format_operation_failure("Close", milestone_name, str(e))
        for line in lines:
            console.print(line, style="bold red")
