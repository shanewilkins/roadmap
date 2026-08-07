"""View project command."""

import click

from roadmap.adapters.cli.cli_command_helpers import require_initialized
from roadmap.adapters.cli.mappers import ProjectMapper
from roadmap.adapters.cli.presentation.project_presenter import ProjectPresenter
from roadmap.common.console import get_console


def _extract_description_and_objectives(content):
    """Extract description and objectives from project content."""
    if not content:
        return None, None

    content_lines = content.split("\n")
    description_lines = []
    objectives_lines = []
    in_objectives = False

    for line in content_lines:
        if "## Objectives" in line or "## objectives" in line.lower():
            in_objectives = True
            continue
        elif in_objectives and line.startswith("## "):
            in_objectives = False

        if in_objectives:
            objectives_lines.append(line)
        elif not line.startswith("## "):
            description_lines.append(line)

    description = "\n".join(description_lines).strip() or None
    objectives = "\n".join(objectives_lines).strip() or None

    return description, objectives


def _get_project_or_exit(ctx: click.Context, project_id: str):
    """Fetch project by ID or exit with a user-facing error message."""
    core = ctx.obj["core"]
    project = core.projects.get(project_id)
    if project:
        return project

    get_console().print(f"❌ Project '{project_id}' not found.", style="bold red")
    get_console().print(
        "\n💡 Tip: Use 'roadmap project list' to see all available projects.",
        style="dim",
    )
    ctx.exit(1)


def _build_project_milestone_data(core, project) -> tuple[list | None, dict | None]:
    """Build milestone list and progress map for a project."""
    if not project.milestones:
        return None, None

    all_milestones = core.milestones.list()
    milestones = [m for m in all_milestones if m.name in project.milestones]
    milestone_progress = {
        milestone.name: core.milestones.get_progress(milestone.name)
        for milestone in milestones
    }
    return milestones, milestone_progress


def _build_effort_data(project) -> dict[str, float | int | None] | None:
    """Build effort payload for presenter when estimate/actual values exist."""
    if not (project.estimated_hours or project.actual_hours):
        return None
    return {
        "estimated": project.estimated_hours,
        "actual": project.actual_hours,
    }


def _build_comments_text(project) -> str | None:
    """Build formatted comments text with threaded replies for display."""
    if not project.comments:
        return None

    from roadmap.core.services.comment.comment_service import CommentService

    threads = CommentService.build_comment_threads(project.comments)
    chunks: list[str] = []

    top_level_ids = sorted([key for key in threads.keys() if key is not None])
    for top_level_id in top_level_ids:
        for comment in threads.get(top_level_id, []):
            chunks.append(CommentService.format_comment_for_display(comment, indent=0))
            for reply in threads.get(comment.id, []):
                chunks.append(
                    CommentService.format_comment_for_display(reply, indent=1)
                )
            chunks.append("")

    return "\n".join(chunks).rstrip() if chunks else None


def _render_objectives_panel(objectives: str | None) -> None:
    """Render objectives markdown panel when objectives are available."""
    if not objectives:
        return

    from rich.markdown import Markdown
    from rich.panel import Panel

    get_console().print(
        Panel(Markdown(objectives), title="✅ Objectives", border_style="green")
    )


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
    project = _get_project_or_exit(ctx, project_id)

    # Convert project to DTO
    project_dto = ProjectMapper.domain_to_dto(project)

    # Get milestones for display
    milestones, milestone_progress = _build_project_milestone_data(core, project)

    # Build effort data
    effort_data = _build_effort_data(project)

    # Extract description and objectives
    description, objectives = _extract_description_and_objectives(project.content)
    description_content = description

    # Prepare comments if any
    comments_text = _build_comments_text(project)

    # Render using presenter
    presenter = ProjectPresenter()
    presenter.render(
        project_dto,
        milestones=milestones,
        milestone_progress=milestone_progress,
        description_content=description_content,
        comments_text=comments_text,
        effort_data=effort_data,
    )

    _render_objectives_panel(objectives)
