"""Close milestone command."""

import click

from roadmap.adapters.cli.error_logging import log_error_with_context
from roadmap.adapters.cli.logging_decorators import log_command
from roadmap.adapters.cli.performance_tracking import track_database_operation
from roadmap.common.console import get_console

console = get_console()


@click.command("close")
@click.argument("milestone_name")
@click.option("--force", is_flag=True, help="Skip confirmation prompt")
@click.pass_context
@log_command("milestone_close", entity_type="milestone", track_duration=True)
def close_milestone(ctx: click.Context, milestone_name: str, force: bool):
    """Close a milestone.

    Validates that all issues in the milestone are closed before allowing closure.
    If there are open issues, provides guidance on migration options.
    """
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return

    try:
        # Check if milestone exists
        milestone = core.get_milestone(milestone_name)
        if not milestone:
            console.print(
                f"❌ Failed to close milestone: {milestone_name} not found",
                style="bold red",
            )
            return

        # Get all issues in this milestone
        all_issues = core.list_issues(milestone=milestone_name)

        # Filter for open issues (not closed)
        open_issues = [issue for issue in all_issues if issue.status.value != "closed"]

        # If there are open issues, provide guidance
        if open_issues:
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
            return

        # All issues are closed, proceed with closing milestone
        if not force:
            if not click.confirm(
                f"Close milestone '{milestone_name}'? All {len(all_issues)} issue(s) are completed."
            ):
                console.print("❌ Milestone close cancelled.", style="yellow")
                return

        from roadmap.core.domain import MilestoneStatus

        with track_database_operation("update", "milestone"):
            success = core.update_milestone(
                milestone_name, status=MilestoneStatus.CLOSED
            )

        if success:
            console.print(f"✅ Closed milestone: {milestone_name}", style="bold green")
            console.print(f"   {len(all_issues)} completed issue(s)", style="green")
        else:
            console.print(
                f"❌ Failed to close milestone: {milestone_name}",
                style="bold red",
            )

    except Exception as e:
        log_error_with_context(
            e,
            operation="milestone_close",
            entity_type="milestone",
            additional_context={"milestone_name": milestone_name},
        )
        console.print(f"❌ Failed to close milestone: {e}", style="bold red")
