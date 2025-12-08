"""View milestone command."""

from datetime import datetime

import click
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from roadmap.adapters.cli.helpers import require_initialized
from roadmap.common.console import get_console

console = get_console()


def _filter_milestone_issues(issues, status_filters, priority_filters, only_open):
    """Filter milestone issues by status, priority, and open status."""
    if not (status_filters or priority_filters or only_open):
        return issues

    status_lower = tuple(s.lower() for s in status_filters) if status_filters else ()
    priority_lower = (
        tuple(p.lower() for p in priority_filters) if priority_filters else ()
    )

    def matches_filters(issue):
        if status_lower and issue.status.value not in status_lower:
            return False
        if priority_lower and issue.priority.value not in priority_lower:
            return False
        if only_open and issue.status.value == "closed":
            return False
        return True

    return [issue for issue in issues if matches_filters(issue)]


def _build_milestone_header(milestone):
    """Build header text with milestone name and status."""
    status_color = "green" if milestone.status.value == "closed" else "yellow"

    header = Text()
    header.append(milestone.name, style="bold cyan")
    header.append("\n")
    header.append(f"[{milestone.status.value.upper()}]", style=f"bold {status_color}")

    return header


def _add_due_date_to_header(header, milestone):
    """Add due date info to milestone header."""
    if not milestone.due_date:
        return header

    due_date_str = milestone.due_date.strftime("%Y-%m-%d")
    now = datetime.now()

    milestone_due = (
        milestone.due_date.replace(tzinfo=None)
        if milestone.due_date.tzinfo
        else milestone.due_date
    )
    is_overdue = milestone_due < now and milestone.status.value == "open"

    header.append(" • ", style="dim")
    if is_overdue:
        days_overdue = (now - milestone_due).days
        header.append(f"⚠️  OVERDUE by {days_overdue} days", style="bold red")
        header.append(f" (Due: {due_date_str})", style="red")
    else:
        header.append(f"Due: {due_date_str}", style="white")

    return header


def _display_progress_panel(progress_data):
    """Display milestone progress as a panel."""
    completed = progress_data.get("completed", 0)
    total = progress_data.get("total", 0)
    percentage = (completed / total * 100) if total > 0 else 0

    progress_table = Table(show_header=False, box=None, padding=(0, 2))
    progress_table.add_column("Key", style="dim")
    progress_table.add_column("Value")
    progress_table.add_row("Issues Complete", f"{completed}/{total}")
    progress_table.add_row("Percentage", f"{percentage:.1f}%")

    console.print(
        Panel(
            progress_table,
            title="📊 Progress",
            border_style="green" if percentage > 50 else "yellow",
        )
    )


def _format_estimated_time(total_estimated):
    """Format estimated time display."""
    if total_estimated < 8:
        return f"{total_estimated:.1f}h"
    days = total_estimated / 8
    return f"{days:.1f}d ({total_estimated:.1f}h)"


def _build_status_breakdown(milestone_issues):
    """Build status breakdown text."""
    status_counts = {}
    for issue in milestone_issues:
        status = issue.status.value
        status_counts[status] = status_counts.get(status, 0) + 1

    return ", ".join(
        f"{status}: {count}" for status, count in sorted(status_counts.items())
    )


def _build_statistics_table(milestone_issues, milestone):
    """Build statistics table for milestone."""
    stats = Table(show_header=False, box=None, padding=(0, 2))
    stats.add_column("Key", style="dim")
    stats.add_column("Value")

    total_estimated = sum(i.estimated_hours or 0 for i in milestone_issues)
    if total_estimated > 0:
        stats.add_row("Total Estimated", _format_estimated_time(total_estimated))

    breakdown = _build_status_breakdown(milestone_issues)
    if breakdown:
        stats.add_row("Status Breakdown", breakdown)

    if milestone.github_milestone:
        stats.add_row("GitHub Milestone", f"#{milestone.github_milestone}")

    return stats


def _build_issues_table(milestone_issues):
    """Build table showing milestone issues."""
    issues_table = Table(show_header=True, header_style="bold magenta")
    issues_table.add_column("ID", style="cyan", width=9)
    issues_table.add_column("Title", style="white", width=20)
    issues_table.add_column("Status", width=11)
    issues_table.add_column("Priority", width=9)
    issues_table.add_column("Assignee", width=12)
    issues_table.add_column("Progress", width=10)
    issues_table.add_column("Estimate", width=10)

    status_colors = {
        "todo": "blue",
        "in-progress": "yellow",
        "blocked": "red",
        "review": "magenta",
        "closed": "green",
    }
    priority_colors = {
        "critical": "bold red",
        "high": "red",
        "medium": "yellow",
        "low": "green",
    }

    for issue in milestone_issues[:10]:
        status_color = status_colors.get(issue.status.value, "white")
        priority_color = priority_colors.get(issue.priority.value, "white")
        assignee_display = issue.assignee if issue.assignee else "[dim]Unassigned[/dim]"

        issues_table.add_row(
            issue.id,
            issue.title[:50] + "..." if len(issue.title) > 50 else issue.title,
            f"[{status_color}]{issue.status.value}[/{status_color}]",
            f"[{priority_color}]{issue.priority.value}[/{priority_color}]",
            assignee_display,
            issue.progress_display,
            issue.estimated_time_display,
        )

    return issues_table


def _extract_description_and_goals(content):
    """Parse milestone content to extract description and goals."""
    content_lines = content.split("\n")
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
        elif not line.startswith("#"):
            description_lines.append(line)

    return "\n".join(description_lines).strip(), "\n".join(goals_lines).strip()


@click.command("view")
@click.argument("milestone_name")
@click.option(
    "--status",
    type=click.Choice(
        ["todo", "in-progress", "blocked", "review", "closed"], case_sensitive=False
    ),
    multiple=True,
    help="Filter issues by status (can specify multiple times)",
)
@click.option(
    "--priority",
    type=click.Choice(["critical", "high", "medium", "low"], case_sensitive=False),
    multiple=True,
    help="Filter issues by priority (can specify multiple times)",
)
@click.option(
    "--only-open",
    is_flag=True,
    help="Show only open issues (excludes closed)",
)
@click.pass_context
@require_initialized
def view_milestone(
    ctx: click.Context,
    milestone_name: str,
    status: tuple,
    priority: tuple,
    only_open: bool,
):
    """Display detailed information about a specific milestone.

    Shows complete milestone details including progress, statistics,
    issues breakdown, description, and goals in a formatted view.

    Use --status and --priority to filter which issues are displayed.

    Examples:
        roadmap milestone view v.0.5.0
        roadmap milestone view v.0.5.0 --status todo --status in-progress
        roadmap milestone view v.0.5.0 --priority high --priority critical
        roadmap milestone view v.0.5.0 --only-open
    """
    core = ctx.obj["core"]

    milestone = core.milestones.get(milestone_name)
    if not milestone:
        console.print(f"❌ Milestone '{milestone_name}' not found.", style="bold red")
        console.print(
            "\n💡 Tip: Use 'roadmap milestone list' to see all available milestones.",
            style="dim",
        )
        ctx.exit(1)

    all_issues = core.issues.list()
    milestone_issues = milestone.get_issues(all_issues)
    milestone_issues = _filter_milestone_issues(
        milestone_issues, status, priority, only_open
    )

    progress_data = core.milestones.get_progress(milestone_name)

    # Display milestone header
    header = _build_milestone_header(milestone)
    header = _add_due_date_to_header(header, milestone)
    console.print(Panel(header, border_style="cyan"))

    # Display progress
    _display_progress_panel(progress_data)

    # Display statistics
    stats = _build_statistics_table(milestone_issues, milestone)
    console.print(Panel(stats, title="📈 Statistics", border_style="blue"))

    # Display issues
    if milestone_issues:
        issues_table = _build_issues_table(milestone_issues)
        title = (
            f"📋 Issues (Showing 10 of {len(milestone_issues)})"
            if len(milestone_issues) > 10
            else "📋 Issues"
        )
        console.print(Panel(issues_table, title=title, border_style="magenta"))
    else:
        console.print(
            Panel(
                "[dim]No issues assigned to this milestone[/dim]",
                title="📋 Issues",
                border_style="magenta",
            )
        )

    # Display description and goals
    if milestone.content or milestone.description:
        content_to_display = milestone.content or milestone.description
        description, goals = _extract_description_and_goals(content_to_display)

        if description:
            md = Markdown(description)
            console.print(Panel(md, title="📝 Description", border_style="white"))

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
