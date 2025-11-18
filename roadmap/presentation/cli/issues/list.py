"""List issues command."""

import click
from rich.table import Table
from rich.text import Text

from roadmap.cli.utils import get_console
from roadmap.error_handling import ErrorHandler, ValidationError
from roadmap.models import Priority, Status

console = get_console()


@click.command("list")
@click.option("--milestone", "-m", help="Filter by milestone")
@click.option("--backlog", is_flag=True, help="Show only backlog issues (no milestone)")
@click.option(
    "--unassigned",
    is_flag=True,
    help="Show only unassigned issues (alias for --backlog)",
)
@click.option("--open", is_flag=True, help="Show only open issues (not done)")
@click.option("--blocked", is_flag=True, help="Show only blocked issues")
@click.option(
    "--next-milestone", is_flag=True, help="Show issues for the next upcoming milestone"
)
@click.option("--assignee", "-a", help="Filter by assignee")
@click.option("--my-issues", is_flag=True, help="Show only issues assigned to me")
@click.option(
    "--status",
    "-s",
    type=click.Choice(["todo", "in-progress", "blocked", "review", "done"]),
    help="Filter by status",
)
@click.option(
    "--priority",
    "-p",
    type=click.Choice(["critical", "high", "medium", "low"]),
    help="Filter by priority",
)
@click.pass_context
def list_issues(
    ctx: click.Context,
    milestone: str,
    backlog: bool,
    unassigned: bool,
    open: bool,
    blocked: bool,
    next_milestone: bool,
    assignee: str,
    my_issues: bool,
    status: str,
    priority: str,
):
    """List all issues with various filtering options."""
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return

    try:
        # Check for conflicting filters
        assignee_filters = [assignee is not None, my_issues]
        if sum(bool(f) for f in assignee_filters) > 1:
            console.print(
                "❌ Cannot combine --assignee and --my-issues filters", style="bold red"
            )
            return

        exclusive_filters = [backlog, unassigned, next_milestone, milestone is not None]
        if sum(bool(f) for f in exclusive_filters) > 1:
            console.print(
                "❌ Cannot combine --backlog, --unassigned, --next-milestone, and --milestone filters",
                style="bold red",
            )
            return

        # Handle special assignee filters first
        if my_issues:
            issues = core.get_my_issues()
            filter_description = "my"
        elif assignee:
            issues = core.get_assigned_issues(assignee)
            filter_description = f"assigned to {assignee}"
        # Get base set of issues
        elif backlog or unassigned:
            # Show only backlog/unassigned issues
            issues = core.get_backlog_issues()
            filter_description = "backlog"
        elif next_milestone:
            # Show issues for next milestone
            next_ms = core.get_next_milestone()
            if not next_ms:
                console.print(
                    "📋 No upcoming milestones with due dates found.", style="yellow"
                )
                console.print(
                    "Create one with: roadmap milestone create 'Milestone name' --due-date YYYY-MM-DD",
                    style="dim",
                )
                return
            issues = core.get_milestone_issues(next_ms.name)
            filter_description = f"next milestone ({next_ms.name})"
        elif milestone:
            # Show issues for specific milestone
            issues = core.get_milestone_issues(milestone)
            filter_description = f"milestone '{milestone}'"
        else:
            # Show all issues
            issues = core.list_issues()
            filter_description = "all"

        # Apply additional filters
        if open:
            issues = [i for i in issues if i.status != Status.DONE]
            filter_description += " open"

        if blocked:
            issues = [i for i in issues if i.status == Status.BLOCKED]
            filter_description += " blocked"

        if status:
            issues = [i for i in issues if i.status == Status(status)]
            filter_description += f" {status}"

        if priority:
            issues = [i for i in issues if i.priority == Priority(priority)]
            filter_description += f" {priority} priority"

        # Show results
        if not issues:
            console.print(f"📋 No {filter_description} issues found.", style="yellow")
            console.print(
                "Create one with: roadmap issue create 'Issue title'", style="dim"
            )
            return

        # Display header with filter info
        header_text = f"📋 {len(issues)} {filter_description} issue{'s' if len(issues) != 1 else ''}"
        console.print(header_text, style="bold cyan")
        console.print()

        # Rich table display
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("ID", style="cyan", width=8)
        table.add_column("Title", style="white", width=25, no_wrap=False)
        table.add_column("Priority", style="yellow", width=10)
        table.add_column("Status", style="green", width=12)
        table.add_column("Progress", style="blue", width=10)
        table.add_column("Assignee", style="magenta", width=12)
        table.add_column("Estimate", style="green", width=10)
        table.add_column("Milestone", style="blue", width=15)

        for issue in issues:
            priority_style = {
                Priority.CRITICAL: "bold red",
                Priority.HIGH: "red",
                Priority.MEDIUM: "yellow",
                Priority.LOW: "dim",
            }.get(issue.priority, "white")

            status_style = {
                Status.TODO: "white",
                Status.IN_PROGRESS: "yellow",
                Status.BLOCKED: "red",
                Status.REVIEW: "blue",
                Status.DONE: "green",
            }.get(issue.status, "white")

            table.add_row(
                issue.id,
                issue.title,
                Text(issue.priority.value, style=priority_style),
                Text(issue.status.value, style=status_style),
                Text(
                    issue.progress_display,
                    style="blue" if issue.progress_percentage else "dim",
                ),
                Text(
                    issue.assignee or "Unassigned",
                    style="magenta" if issue.assignee else "dim",
                ),
                Text(
                    issue.estimated_time_display,
                    style="green" if issue.estimated_hours else "dim",
                ),
                Text(issue.milestone_name, style="dim" if issue.is_backlog else "blue"),
            )

        console.print(table)

        # Show time aggregation for assignee filters
        if assignee or my_issues:
            assignee_name = assignee if assignee else "you"

            # Calculate totals
            total_hours = sum(issue.estimated_hours or 0 for issue in issues)
            sum(
                issue.estimated_hours or 0
                for issue in issues
                if issue.status.value != "done"
            )

            if total_hours > 0:
                # Format total time display
                if total_hours < 1:
                    total_display = f"{total_hours * 60:.0f}m"
                elif total_hours <= 24:
                    total_display = f"{total_hours:.1f}h"
                else:
                    total_display = f"{total_hours / 8:.1f}d"

                console.print()
                console.print(
                    f"Total estimated time for {assignee_name}: {total_display}",
                    style="bold blue",
                )

                # Show status breakdown
                status_counts = {}
                for issue in issues:
                    status = issue.status.value
                    if status not in status_counts:
                        status_counts[status] = {"count": 0, "hours": 0}
                    status_counts[status]["count"] += 1
                    status_counts[status]["hours"] += issue.estimated_hours or 0

                console.print("Workload breakdown:", style="bold")
                for status, data in status_counts.items():
                    if data["count"] > 0:
                        if data["hours"] > 0:
                            if data["hours"] < 1:
                                time_display = f"{data['hours'] * 60:.0f}m"
                            elif data["hours"] <= 24:
                                time_display = f"{data['hours']:.1f}h"
                            else:
                                time_display = f"{data['hours'] / 8:.1f}d"
                            console.print(
                                f"  {status}: {data['count']} issues ({time_display})"
                            )
                        else:
                            console.print(f"  {status}: {data['count']} issues")

    except Exception as e:
        error_handler = ErrorHandler()
        error_handler.handle_error(
            ValidationError(
                "Failed to list issues", context={"command": "list"}, cause=e
            ),
            exit_on_critical=False,
        )
