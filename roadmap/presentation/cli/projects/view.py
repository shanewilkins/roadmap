"""View project command."""

import click
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from roadmap.shared.console import get_console

console = get_console()


@click.command("view")
@click.argument("project_id")
@click.pass_context
def view_project(ctx: click.Context, project_id: str):
    """Display detailed information about a specific project.

    Shows complete project details including metadata, milestones,
    objectives, and description in a formatted view.

    Example:
        roadmap project view abc123def
    """
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return

    # Get the project
    project = core.get_project(project_id)
    if not project:
        console.print(f"❌ Project '{project_id}' not found.", style="bold red")
        console.print(
            "\n💡 Tip: Use 'roadmap project list' to see all available projects.",
            style="dim",
        )
        ctx.exit(1)

    # Build header with status badge
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

    # Header section
    header = Text()
    header.append(f"#{project.id}", style="bold cyan")
    header.append(" • ", style="dim")
    header.append(project.name, style="bold white")
    header.append("\n")
    header.append(f"[{project.status.value.upper()}]", style=f"bold {status_color}")
    header.append(" • ", style="dim")
    header.append(project.priority.value.upper(), style=priority_color)

    console.print(Panel(header, border_style="cyan"))

    # Metadata table
    metadata = Table(show_header=False, box=None, padding=(0, 2))
    metadata.add_column("Key", style="dim")
    metadata.add_column("Value")

    metadata.add_row("Owner", project.owner or "Unassigned")

    if project.start_date:
        metadata.add_row("Start Date", project.start_date.strftime("%Y-%m-%d"))

    if project.target_end_date:
        metadata.add_row("Target End", project.target_end_date.strftime("%Y-%m-%d"))

    if project.actual_end_date:
        metadata.add_row("Actual End", project.actual_end_date.strftime("%Y-%m-%d"))

    metadata.add_row("Created", project.created.strftime("%Y-%m-%d"))
    metadata.add_row("Updated", project.updated.strftime("%Y-%m-%d"))

    console.print(Panel(metadata, title="📋 Metadata", border_style="blue"))

    # Effort section
    if project.estimated_hours or project.actual_hours:
        effort = Table(show_header=False, box=None, padding=(0, 2))
        effort.add_column("Key", style="dim")
        effort.add_column("Value")

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

        console.print(Panel(effort, title="⏱️  Effort", border_style="yellow"))

    # Milestones section
    if project.milestones:
        all_milestones = core.list_milestones()

        milestones_table = Table(show_header=True, header_style="bold magenta")
        milestones_table.add_column("Milestone", style="cyan")
        milestones_table.add_column("Status", width=10)
        milestones_table.add_column("Progress", width=12)
        milestones_table.add_column("Due Date", width=12)

        for milestone_name in project.milestones:
            milestone = next(
                (m for m in all_milestones if m.name == milestone_name), None
            )
            if milestone:
                progress_data = core.get_milestone_progress(milestone_name)
                completed = progress_data.get("completed", 0)
                total = progress_data.get("total", 0)
                progress_str = f"{completed}/{total}"

                status_color = (
                    "green" if milestone.status.value == "closed" else "yellow"
                )
                due_date_str = (
                    milestone.due_date.strftime("%Y-%m-%d")
                    if milestone.due_date
                    else "-"
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

    # Description and objectives section
    if project.content or project.description:
        content_to_display = project.content or project.description

        # Parse markdown content to extract description and objectives
        content_lines = content_to_display.split("\n")
        description_lines = []
        objectives_lines = []
        in_objectives = False

        for line in content_lines:
            if "## Objectives" in line or "## objectives" in line.lower():
                in_objectives = True
                continue
            elif line.startswith("## ") and in_objectives:
                in_objectives = False

            if in_objectives:
                objectives_lines.append(line)
            elif not line.startswith("#"):  # Skip other headers
                description_lines.append(line)

        # Show description
        description = "\n".join(description_lines).strip()
        if description:
            md = Markdown(description)
            console.print(Panel(md, title="📝 Description", border_style="white"))

        # Show objectives
        objectives = "\n".join(objectives_lines).strip()
        if objectives:
            md = Markdown(objectives)
            console.print(Panel(md, title="✅ Objectives", border_style="green"))
    else:
        console.print(
            Panel(
                "[dim]No description available[/dim]",
                title="📝 Description",
                border_style="white",
            )
        )

    # Footer with file location
    console.print(
        f"\n[dim]File: .roadmap/projects/{project.id}-{project.name.lower().replace(' ', '-')}.md[/dim]"
    )
