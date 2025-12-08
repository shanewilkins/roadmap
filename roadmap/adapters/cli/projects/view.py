"""View project command."""

import click
from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text

from roadmap.adapters.cli.helpers import require_initialized
from roadmap.adapters.cli.presentation.table_builders import (
    create_list_table,
    create_metadata_table,
)
from roadmap.common.console import get_console

console = get_console()


def _build_project_header(project):
    """Build the project header with status and priority badges."""
    status_colors = {
        "planning": "blue",
        "active": "green",
        "on-hold": "yellow",
        "completed": "bold green",
        "cancelled": "red",
    }
    status_color = status_colors.get(project.status.value, "white")

    priority_colors = {
        "critical": "bold red",
        "high": "red",
        "medium": "yellow",
        "low": "blue",
    }
    priority_color = priority_colors.get(project.priority.value, "white")

    header = Text()
    header.append(f"#{project.id}", style="bold cyan")
    header.append(" • ", style="dim")
    header.append(project.name, style="bold white")
    header.append("\n")
    header.append(f"[{project.status.value.upper()}]", style=f"bold {status_color}")
    header.append(" • ", style="dim")
    header.append(project.priority.value.upper(), style=priority_color)

    return header


def _build_metadata_table(project):
    """Build metadata table with project dates."""
    metadata = create_metadata_table()

    metadata.add_row("Owner", project.owner or "Unassigned")

    if project.start_date:
        metadata.add_row("Start Date", project.start_date.strftime("%Y-%m-%d"))

    if project.target_end_date:
        metadata.add_row("Target End", project.target_end_date.strftime("%Y-%m-%d"))

    if project.actual_end_date:
        metadata.add_row("Actual End", project.actual_end_date.strftime("%Y-%m-%d"))

    metadata.add_row("Created", project.created.strftime("%Y-%m-%d"))
    metadata.add_row("Updated", project.updated.strftime("%Y-%m-%d"))

    return metadata


def _build_effort_table(project):
    """Build effort/hours table if data exists."""
    if not (project.estimated_hours or project.actual_hours):
        return None

    effort = create_metadata_table()

    if project.estimated_hours:
        if project.estimated_hours < 8:
            estimated_display = f"{project.estimated_hours:.1f}h"
        else:
            days = project.estimated_hours / 8
            estimated_display = f"{days:.1f}d ({project.estimated_hours:.1f}h)"
        effort.add_row("Estimated", estimated_display)

    if project.actual_hours:
        if project.actual_hours < 8:
            actual_display = f"{project.actual_hours:.1f}h"
        else:
            days = project.actual_hours / 8
            actual_display = f"{days:.1f}d ({project.actual_hours:.1f}h)"
        effort.add_row("Actual", actual_display)

    return effort


def _build_milestones_table(core, project):
    """Build milestones table if milestones exist."""
    if not project.milestones:
        return None

    all_milestones = core.milestones.list()

    columns = [
        ("Milestone", "cyan", None),
        ("Status", None, 10),
        ("Progress", None, 12),
        ("Due Date", None, 12),
    ]
    milestones_table = create_list_table(columns)

    for milestone_name in project.milestones:
        milestone = next((m for m in all_milestones if m.name == milestone_name), None)
        if milestone:
            progress_data = core.milestones.get_progress(milestone_name)
            completed = progress_data.get("completed", 0)
            total = progress_data.get("total", 0)
            progress_str = f"{completed}/{total}"

            status_color = "green" if milestone.status.value == "closed" else "yellow"
            due_date_str = (
                milestone.due_date.strftime("%Y-%m-%d") if milestone.due_date else "-"
            )

            milestones_table.add_row(
                milestone_name,
                f"[{status_color}]{milestone.status.value}[/{status_color}]",
                progress_str,
                due_date_str,
            )
        else:
            milestones_table.add_row(
                milestone_name,
                "[dim]not found[/dim]",
                "-",
                "-",
            )

    return milestones_table


def _is_objectives_header(line):
    """Check if line is objectives header."""
    return "## Objectives" in line or "## objectives" in line.lower()


def _is_other_header(line):
    """Check if line is a header (but not objectives)."""
    return line.startswith("## ")


def _extract_description_and_objectives(content):
    """Extract description and objectives from project content."""
    if not content:
        return None, None

    content_lines = content.split("\n")
    description_lines = []
    objectives_lines = []
    in_objectives = False

    for line in content_lines:
        if _is_objectives_header(line):
            in_objectives = True
            continue
        elif in_objectives and _is_other_header(line):
            in_objectives = False

        if in_objectives:
            objectives_lines.append(line)
        elif not _is_other_header(line):
            description_lines.append(line)

    description = "\n".join(description_lines).strip() or None
    objectives = "\n".join(objectives_lines).strip() or None

    return description, objectives


@click.command("view")
@click.argument("project_id")
@click.pass_context
@require_initialized
def view_project(ctx: click.Context, project_id: str):
    """Display detailed information about a specific project.

    Shows complete project details including metadata, milestones,
    objectives, and description in a formatted view.

    Example:
        roadmap project view abc123def
    """
    core = ctx.obj["core"]

    project = core.projects.get(project_id)
    if not project:
        console.print(f"❌ Project '{project_id}' not found.", style="bold red")
        console.print(
            "\n💡 Tip: Use 'roadmap project list' to see all available projects.",
            style="dim",
        )
        ctx.exit(1)

    # Display header
    header = _build_project_header(project)
    console.print(Panel(header, border_style="cyan"))

    # Display metadata
    metadata = _build_metadata_table(project)
    console.print(Panel(metadata, title="📋 Metadata", border_style="blue"))

    # Display effort if available
    effort = _build_effort_table(project)
    if effort:
        console.print(Panel(effort, title="⏱️  Effort", border_style="yellow"))

    # Display milestones
    milestones_table = _build_milestones_table(core, project)
    if milestones_table:
        console.print(
            Panel(milestones_table, title="🎯 Milestones", border_style="magenta")
        )
    else:
        console.print(
            Panel(
                "[dim]No milestones assigned to this project[/dim]",
                title="🎯 Milestones",
                border_style="magenta",
            )
        )

    # Display description and objectives
    content_to_display = project.content or project.description
    description, objectives = _extract_description_and_objectives(content_to_display)

    if description:
        md = Markdown(description)
        console.print(Panel(md, title="📝 Description", border_style="white"))
    else:
        console.print(
            Panel(
                "[dim]No description available[/dim]",
                title="📝 Description",
                border_style="white",
            )
        )

    if objectives:
        md = Markdown(objectives)
        console.print(Panel(md, title="✅ Objectives", border_style="green"))

    # Footer with file location
    console.print(
        f"\n[dim]File: .roadmap/projects/{project.id}-{project.name.lower().replace(' ', '-')}.md[/dim]"
    )
