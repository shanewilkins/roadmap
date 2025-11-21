"""Today command - daily workflow summary."""

from datetime import datetime

import click
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from roadmap.domain.issue import Status
from roadmap.shared.console import get_console

console = get_console()


@click.command("today")
@click.pass_context
def today(ctx: click.Context):
    """Show your daily workflow summary.

    Displays:
    - Current in-progress issues assigned to you
    - Overdue issues
    - Upcoming high-priority tasks
    - Today's completed work

    This is your daily standup command - quick overview of what you're working on.

    Example:
        roadmap today
    """
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return

    try:
        # Get user identity
        config = core.load_config()
        current_user = None
        if config and hasattr(config, "github") and config.github:
            current_user = getattr(config.github, "username", None)

        # Get all issues
        all_issues = core.list_issues()

        # Filter issues assigned to current user
        if current_user:
            my_issues = [i for i in all_issues if i.assignee == current_user]
        else:
            # If no user configured, show all issues
            my_issues = all_issues

        # Categorize issues
        in_progress = [i for i in my_issues if i.status == Status.IN_PROGRESS]
        overdue = [
            i
            for i in my_issues
            if i.due_date
            and i.due_date.replace(tzinfo=None) < datetime.now()
            and i.status != Status.DONE
        ]
        blocked = [i for i in my_issues if i.status == Status.BLOCKED]
        todo_high_priority = [
            i
            for i in my_issues
            if i.status == Status.TODO and i.priority.value in ["critical", "high"]
        ][:3]  # Top 3
        completed_today = [
            i
            for i in my_issues
            if i.status == Status.DONE
            and i.actual_end_date
            and i.actual_end_date.date() == datetime.now().date()
        ]

        # Build header
        header = Text()
        if current_user:
            header.append("Daily Summary for ", style="dim")
            header.append(current_user, style="bold cyan")
        else:
            header.append("Daily Summary", style="bold cyan")
        header.append(f"\n{datetime.now().strftime('%A, %B %d, %Y')}", style="dim")

        console.print(Panel(header, border_style="cyan"))

        # Section 1: Currently In Progress
        if in_progress:
            progress_table = Table(
                show_header=True,
                header_style="bold yellow",
                title="🚀 In Progress",
                title_style="bold yellow",
            )
            progress_table.add_column("ID", style="cyan", width=10)
            progress_table.add_column("Title", style="white")
            progress_table.add_column("Progress", width=12)
            progress_table.add_column("Milestone", width=15)

            for issue in in_progress:
                progress_table.add_row(
                    issue.id,
                    issue.title[:60] + "..." if len(issue.title) > 60 else issue.title,
                    issue.progress_display,
                    issue.milestone or "Backlog",
                )

            console.print(progress_table)
            console.print()
        else:
            console.print(
                Panel(
                    "[dim]No issues currently in progress[/dim]",
                    title="🚀 In Progress",
                    title_align="left",
                    border_style="yellow",
                )
            )
            console.print()

        # Section 2: Overdue Items (if any)
        if overdue:
            overdue_table = Table(
                show_header=True,
                header_style="bold red",
                title="⚠️  Overdue",
                title_style="bold red",
            )
            overdue_table.add_column("ID", style="cyan", width=10)
            overdue_table.add_column("Title", style="white")
            overdue_table.add_column("Due Date", width=12, style="red")
            overdue_table.add_column("Priority", width=10)

            for issue in overdue:
                days_overdue = (
                    datetime.now() - issue.due_date.replace(tzinfo=None)
                ).days
                overdue_table.add_row(
                    issue.id,
                    issue.title[:50] + "..." if len(issue.title) > 50 else issue.title,
                    f"{issue.due_date.strftime('%Y-%m-%d')} ({days_overdue}d)",
                    issue.priority.value,
                )

            console.print(overdue_table)
            console.print()

        # Section 3: Blocked Items (if any)
        if blocked:
            blocked_table = Table(
                show_header=True,
                header_style="bold red",
                title="🚫 Blocked",
                title_style="bold red",
            )
            blocked_table.add_column("ID", style="cyan", width=10)
            blocked_table.add_column("Title", style="white")
            blocked_table.add_column("Milestone", width=15)

            for issue in blocked:
                blocked_table.add_row(
                    issue.id,
                    issue.title[:60] + "..." if len(issue.title) > 60 else issue.title,
                    issue.milestone or "Backlog",
                )

            console.print(blocked_table)
            console.print()

        # Section 4: Up Next (high priority todos)
        if todo_high_priority:
            next_table = Table(
                show_header=True,
                header_style="bold blue",
                title="📋 Up Next (High Priority)",
                title_style="bold blue",
            )
            next_table.add_column("ID", style="cyan", width=10)
            next_table.add_column("Title", style="white")
            next_table.add_column("Priority", width=10)
            next_table.add_column("Estimate", width=10)

            for issue in todo_high_priority:
                priority_color = (
                    "bold red" if issue.priority.value == "critical" else "red"
                )
                next_table.add_row(
                    issue.id,
                    issue.title[:55] + "..." if len(issue.title) > 55 else issue.title,
                    f"[{priority_color}]{issue.priority.value}[/{priority_color}]",
                    issue.estimated_time_display,
                )

            console.print(next_table)
            console.print()

        # Section 5: Completed Today
        if completed_today:
            done_table = Table(
                show_header=True,
                header_style="bold green",
                title="✅ Completed Today",
                title_style="bold green",
            )
            done_table.add_column("ID", style="cyan", width=10)
            done_table.add_column("Title", style="white")
            done_table.add_column("Completed", width=12)

            for issue in completed_today:
                done_table.add_row(
                    issue.id,
                    issue.title[:60] + "..." if len(issue.title) > 60 else issue.title,
                    issue.actual_end_date.strftime("%H:%M"),
                )

            console.print(done_table)
            console.print()

        # Summary footer
        summary = Text()
        summary.append("\n📊 Summary: ", style="bold")
        summary.append(f"{len(in_progress)} in progress", style="yellow")
        summary.append(" • ", style="dim")
        summary.append(f"{len(overdue)} overdue", style="red" if overdue else "dim")
        summary.append(" • ", style="dim")
        summary.append(f"{len(blocked)} blocked", style="red" if blocked else "dim")
        summary.append(" • ", style="dim")
        summary.append(f"{len(completed_today)} completed today", style="green")

        console.print(summary)

        # Helpful tips
        if not in_progress and todo_high_priority:
            console.print(
                f"\n💡 Tip: Start work on an issue with: [cyan]roadmap issue start {todo_high_priority[0].id}[/cyan]",
                style="dim",
            )
        elif overdue:
            console.print(
                f"\n💡 Tip: View overdue issue details with: [cyan]roadmap issue view {overdue[0].id}[/cyan]",
                style="dim",
            )

    except Exception as e:
        console.print(f"❌ Failed to generate daily summary: {e}", style="bold red")
        import traceback

        console.print(traceback.format_exc(), style="dim")
