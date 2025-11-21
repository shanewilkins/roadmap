"""View milestone command."""

from datetime import datetime

import click
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from roadmap.shared.console import get_console

console = get_console()


@click.command("view")
@click.argument("milestone_name")
@click.pass_context
def view_milestone(ctx: click.Context, milestone_name: str):
    """Display detailed information about a specific milestone.

    Shows complete milestone details including progress, statistics,
    issues breakdown, description, and goals in a formatted view.

    Example:
        roadmap milestone view v.0.5.0
    """
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return

    # Get the milestone
    milestone = core.get_milestone(milestone_name)
    if not milestone:
        console.print(f"❌ Milestone '{milestone_name}' not found.", style="bold red")
        console.print(
            "\n💡 Tip: Use 'roadmap milestone list' to see all available milestones.",
            style="dim",
        )
        ctx.exit(1)

    # Get all issues for progress calculation
    all_issues = core.list_issues()
    milestone_issues = milestone.get_issues(all_issues)
    progress_data = core.get_milestone_progress(milestone_name)

    # Build header with status badge
    status_color = "green" if milestone.status.value == "closed" else "yellow"

    header = Text()
    header.append(milestone.name, style="bold cyan")
    header.append("\n")
    header.append(f"[{milestone.status.value.upper()}]", style=f"bold {status_color}")

    # Add due date with overdue warning
    if milestone.due_date:
        due_date_str = milestone.due_date.strftime("%Y-%m-%d")
        now = datetime.now()

        # Normalize timezones for comparison
        milestone_due = (
            milestone.due_date.replace(tzinfo=None)
            if milestone.due_date.tzinfo
            else milestone.due_date
        )
        is_overdue = milestone_due < now and milestone.status.value == "open"

        if is_overdue:
            days_overdue = (now - milestone_due).days
            header.append(" • ", style="dim")
            header.append(f"⚠️  OVERDUE by {days_overdue} days", style="bold red")
            header.append(f" (Due: {due_date_str})", style="red")
        else:
            header.append(" • ", style="dim")
            header.append(f"Due: {due_date_str}", style="white")

    console.print(Panel(header, border_style="cyan"))

    # Progress section
    completed = progress_data.get("completed", 0)
    total = progress_data.get("total", 0)
    percentage = (completed / total * 100) if total > 0 else 0

    progress_panel = Table(show_header=False, box=None, padding=(0, 2))
    progress_panel.add_column("Key", style="dim")
    progress_panel.add_column("Value")

    progress_panel.add_row("Issues Complete", f"{completed}/{total}")
    progress_panel.add_row("Percentage", f"{percentage:.1f}%")

    # Show progress panel
    console.print(
        Panel(
            progress_panel,
            title="📊 Progress",
            border_style="green" if percentage > 50 else "yellow",
        )
    )

    # Statistics section
    stats = Table(show_header=False, box=None, padding=(0, 2))
    stats.add_column("Key", style="dim")
    stats.add_column("Value")

    # Get all issues for this milestone
    all_issues = core.list_issues()
    milestone_issues = [i for i in all_issues if i.milestone == milestone_name]

    # Calculate total estimated time
    total_estimated = sum(i.estimated_hours or 0 for i in milestone_issues)
    if total_estimated > 0:
        if total_estimated < 8:
            estimated_display = f"{total_estimated:.1f}h"
        else:
            days = total_estimated / 8
            estimated_display = f"{days:.1f}d ({total_estimated:.1f}h)"
        stats.add_row("Total Estimated", estimated_display)

    # Breakdown by status
    status_counts = {}
    for issue in milestone_issues:
        status = issue.status.value
        status_counts[status] = status_counts.get(status, 0) + 1

    if status_counts:
        breakdown = ", ".join(
            f"{status}: {count}" for status, count in sorted(status_counts.items())
        )
        stats.add_row("Status Breakdown", breakdown)

    if milestone.github_milestone:
        stats.add_row("GitHub Milestone", f"#{milestone.github_milestone}")

    console.print(Panel(stats, title="📈 Statistics", border_style="blue"))

    # Issues table
    if milestone_issues:
        issues_table = Table(show_header=True, header_style="bold magenta")
        issues_table.add_column("ID", style="cyan", width=10)
        issues_table.add_column("Title", style="white")
        issues_table.add_column("Status", width=12)
        issues_table.add_column("Progress", width=12)
        issues_table.add_column("Estimate", width=10)

        for issue in milestone_issues[:10]:  # Show first 10
            status_colors = {
                "todo": "blue",
                "in-progress": "yellow",
                "blocked": "red",
                "review": "magenta",
                "done": "green",
            }
            status_color = status_colors.get(issue.status.value, "white")

            issues_table.add_row(
                issue.id,
                issue.title[:50] + "..." if len(issue.title) > 50 else issue.title,
                f"[{status_color}]{issue.status.value}[/{status_color}]",
                issue.progress_display,
                issue.estimated_time_display,
            )

        if len(milestone_issues) > 10:
            console.print(
                Panel(
                    issues_table,
                    title=f"📋 Issues (Showing 10 of {len(milestone_issues)})",
                    border_style="magenta",
                )
            )
        else:
            console.print(
                Panel(issues_table, title="📋 Issues", border_style="magenta")
            )
    else:
        console.print(
            Panel(
                "[dim]No issues assigned to this milestone[/dim]",
                title="📋 Issues",
                border_style="magenta",
            )
        )

    # Description section
    if milestone.content or milestone.description:
        content_to_display = milestone.content or milestone.description

        # Parse markdown content to extract description and goals
        content_lines = content_to_display.split("\n")
        description_lines = []
        goals_lines = []
        in_goals = False

        for line in content_lines:
            if "## Goals" in line or "## goals" in line.lower():
                in_goals = True
                continue
            elif line.startswith("## ") and in_goals:
                in_goals = False

            if in_goals:
                goals_lines.append(line)
            elif not line.startswith("#"):  # Skip other headers
                description_lines.append(line)

        # Show description
        description = "\n".join(description_lines).strip()
        if description:
            md = Markdown(description)
            console.print(Panel(md, title="📝 Description", border_style="white"))

        # Show goals
        goals = "\n".join(goals_lines).strip()
        if goals:
            md = Markdown(goals)
            console.print(Panel(md, title="🎯 Goals", border_style="green"))
    else:
        console.print(
            Panel(
                "[dim]No description available[/dim]",
                title="📝 Description",
                border_style="white",
            )
        )

    # Metadata footer
    metadata = f"Created: {milestone.created.strftime('%Y-%m-%d')} • Updated: {milestone.updated.strftime('%Y-%m-%d')}"
    console.print(f"\n[dim]{metadata}[/dim]")
    console.print(f"[dim]File: .roadmap/milestones/{milestone.name}.md[/dim]")
