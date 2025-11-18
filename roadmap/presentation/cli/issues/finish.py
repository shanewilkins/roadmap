"""Finish issue command."""

from datetime import datetime

import click

from roadmap.cli.utils import get_console

console = get_console()


@click.command("finish")
@click.argument("issue_id")
@click.option("--reason", "-r", help="Reason for finishing the issue")
@click.option("--date", help="Completion date (YYYY-MM-DD HH:MM, defaults to now)")
@click.option(
    "--record-time",
    "-t",
    is_flag=True,
    help="Record actual completion time and duration (like old 'complete' command)",
)
@click.pass_context
def finish_issue(
    ctx: click.Context, issue_id: str, reason: str, date: str, record_time: bool
):
    """Finish an issue (record completion time, reason).

    Behaves like the original monolithic `issue finish` command.
    """
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return

    try:
        # Parse completion date
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
            "status": "done",
            "progress_percentage": 100.0,
        }

        if record_time:
            update_data["actual_end_date"] = end_date

        if reason:
            # Append reason to existing content
            issue = core.get_issue(issue_id)
            if not issue:
                console.print(f"❌ Issue not found: {issue_id}", style="bold red")
                return
            content = issue.content or ""
            completion_note = f"\n\n**Finished:** {reason}"
            update_data["content"] = content + completion_note

        # Update the issue
        success = core.update_issue(issue_id, **update_data)

        if success:
            # Re-fetch issue to display updated values
            updated = core.get_issue(issue_id)
            console.print(f"✅ Finished: {updated.title}", style="bold green")

            if reason:
                console.print(f"   Reason: {reason}", style="cyan")

            if record_time:
                end_display = update_data.get("actual_end_date", datetime.now())
                console.print(
                    f"   Completed: {end_display.strftime('%Y-%m-%d %H:%M')}",
                    style="cyan",
                )

                # Show duration if we have start date
                if updated.actual_start_date:
                    duration = end_display - updated.actual_start_date
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

            console.print("   Status: Done", style="green")
        else:
            console.print(f"❌ Failed to finish issue: {issue_id}", style="bold red")

    except Exception as e:
        console.print(f"❌ Error finishing issue: {e}", style="bold red")
