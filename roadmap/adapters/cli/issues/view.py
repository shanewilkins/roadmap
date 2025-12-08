"""View issue command."""

import click
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from roadmap.common.console import get_console

console = get_console()


def _build_issue_header(issue):
    """Build header text with issue title and metadata."""
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
        "low": "blue",
    }

    status_color = status_colors.get(issue.status.value, "white")
    priority_color = priority_colors.get(issue.priority.value, "white")

    header = Text()
    header.append(f"#{issue.id}", style="bold cyan")
    header.append(" • ", style="dim")
    header.append(issue.title, style="bold white")
    header.append("\n")
    header.append(f"[{issue.status.value.upper()}]", style=f"bold {status_color}")
    header.append(" • ", style="dim")
    header.append(issue.priority.value.upper(), style=priority_color)
    header.append(" • ", style="dim")
    header.append(issue.issue_type.value.title(), style="cyan")

    return header


def _build_metadata_table(issue):
    """Build metadata table for issue."""
    metadata = Table(show_header=False, box=None, padding=(0, 2))
    metadata.add_column("Key", style="dim")
    metadata.add_column("Value")

    metadata.add_row("Assignee", issue.assignee or "Unassigned")
    metadata.add_row("Milestone", issue.milestone_name)
    metadata.add_row("Created", issue.created.strftime("%Y-%m-%d %H:%M"))
    metadata.add_row("Updated", issue.updated.strftime("%Y-%m-%d %H:%M"))

    if issue.labels:
        metadata.add_row("Labels", ", ".join(issue.labels))

    if issue.github_issue:
        metadata.add_row("GitHub Issue", f"#{issue.github_issue}")

    return metadata


def _build_timeline_table(issue):
    """Build timeline table for issue."""
    timeline = Table(show_header=False, box=None, padding=(0, 2))
    timeline.add_column("Key", style="dim")
    timeline.add_column("Value")

    timeline.add_row("Estimated", issue.estimated_time_display)
    timeline.add_row("Progress", issue.progress_display)

    if issue.actual_start_date:
        timeline.add_row("Started", issue.actual_start_date.strftime("%Y-%m-%d %H:%M"))

    if issue.actual_end_date:
        timeline.add_row("Completed", issue.actual_end_date.strftime("%Y-%m-%d %H:%M"))
        if issue.actual_duration_hours:
            timeline.add_row("Duration", f"{issue.actual_duration_hours:.1f}h")

    if issue.due_date:
        timeline.add_row("Due Date", issue.due_date.strftime("%Y-%m-%d"))

    return timeline


def _build_dependencies_table(issue):
    """Build dependencies table if exists."""
    if not (issue.depends_on or issue.blocks):
        return None

    deps = Table(show_header=False, box=None, padding=(0, 2))
    deps.add_column("Key", style="dim")
    deps.add_column("Value")

    if issue.depends_on:
        deps.add_row("Depends on", ", ".join(issue.depends_on))
    if issue.blocks:
        deps.add_row("Blocks", ", ".join(issue.blocks))

    return deps


def _build_git_table(issue):
    """Build git integration table if exists."""
    if not (issue.git_branches or issue.git_commits):
        return None

    git = Table(show_header=False, box=None, padding=(0, 2))
    git.add_column("Key", style="dim")
    git.add_column("Value")

    if issue.git_branches:
        git.add_row("Branches", ", ".join(issue.git_branches))

    if issue.git_commits:
        commit_summary = f"{len(issue.git_commits)} commit(s)"
        git.add_row("Commits", commit_summary)

    return git


def _build_handoff_table(issue):
    """Build handoff information table if exists."""
    if not issue.has_been_handed_off:
        return None

    handoff = Table(show_header=False, box=None, padding=(0, 2))
    handoff.add_column("Key", style="dim")
    handoff.add_column("Value")

    handoff.add_row("Previous Assignee", issue.previous_assignee or "N/A")
    if issue.handoff_date:
        handoff.add_row("Handoff Date", issue.handoff_date.strftime("%Y-%m-%d %H:%M"))
    if issue.handoff_notes:
        handoff.add_row("Notes", issue.handoff_notes)

    return handoff


def _extract_description_and_criteria(content):
    """Parse issue content to extract description and acceptance criteria."""
    content_lines = content.split("\n")
    description_lines = []
    acceptance_lines = []
    in_acceptance = False

    for line in content_lines:
        if "## Acceptance Criteria" in line or "## acceptance criteria" in line.lower():
            in_acceptance = True
            continue
        elif line.startswith("## ") and in_acceptance:
            in_acceptance = False

        if in_acceptance:
            acceptance_lines.append(line)
        elif not line.startswith("#"):
            description_lines.append(line)

    description = "\n".join(description_lines).strip()
    acceptance = "\n".join(acceptance_lines).strip()

    return description, acceptance


@click.command("view")
@click.argument("issue_id")
@click.pass_context
def view_issue(ctx: click.Context, issue_id: str):
    """Display detailed information about a specific issue.

    Shows complete issue details including metadata, timeline, dependencies,
    git integration, description, and acceptance criteria in a formatted view.

    Example:
        roadmap issue view abc123def
    """
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return

    issue = core.issues.get(issue_id)
    if not issue:
        console.print(f"❌ Issue '{issue_id}' not found.", style="bold red")
        console.print(
            "\n💡 Tip: Use 'roadmap issue list' to see all available issues.",
            style="dim",
        )
        ctx.exit(1)

    # Display header
    header = _build_issue_header(issue)
    console.print(Panel(header, border_style="cyan"))

    # Display metadata
    metadata = _build_metadata_table(issue)
    console.print(Panel(metadata, title="📋 Metadata", border_style="blue"))

    # Display timeline
    timeline = _build_timeline_table(issue)
    console.print(Panel(timeline, title="⏱️  Timeline", border_style="yellow"))

    # Display dependencies if any
    deps = _build_dependencies_table(issue)
    if deps:
        console.print(Panel(deps, title="🔗 Dependencies", border_style="magenta"))

    # Display git if any
    git = _build_git_table(issue)
    if git:
        console.print(Panel(git, title="🔀 Git Integration", border_style="green"))

    # Display handoff if applicable
    handoff = _build_handoff_table(issue)
    if handoff:
        console.print(Panel(handoff, title="👥 Handoff", border_style="yellow"))

    # Display description and acceptance criteria
    if issue.content:
        description, acceptance = _extract_description_and_criteria(issue.content)

        if description:
            md = Markdown(description)
            console.print(Panel(md, title="📝 Description", border_style="white"))

        if acceptance:
            md = Markdown(acceptance)
            console.print(
                Panel(md, title="✅ Acceptance Criteria", border_style="green")
            )
    else:
        console.print(
            Panel(
                "[dim]No description available[/dim]",
                title="📝 Description",
                border_style="white",
            )
        )
