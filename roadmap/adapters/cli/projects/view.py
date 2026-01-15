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
        get_console().print(f"❌ Project '{project_id}' not found.", style="bold red")
        get_console().print(
            "\n💡 Tip: Use 'roadmap project list' to see all available projects.",
            style="dim",
        )
        ctx.exit(1)

    # Convert project to DTO
    project_dto = ProjectMapper.domain_to_dto(project)

    # Get milestones for display
    milestones = None
    milestone_progress = None
    if project.milestones:
        all_milestones = core.milestones.list()
        milestones = [m for m in all_milestones if m.name in project.milestones]
        milestone_progress = {
            m.name: core.milestones.get_progress(m.name) for m in milestones
        }

    # Build effort data
    effort_data = None
    if project.estimated_hours or project.actual_hours:
        effort_data = {
            "estimated": project.estimated_hours,
            "actual": project.actual_hours,
        }

    # Extract description and objectives
    description, objectives = _extract_description_and_objectives(project.content)
    description_content = description

    # Prepare comments if any
    comments_text = None
    if project.comments:
        from roadmap.core.services.comment.comment_service import CommentService

        threads = CommentService.build_comment_threads(project.comments)
        comment_text = ""

        top_level_ids = [k for k in threads.keys() if k is not None]
        for top_level_id in sorted(top_level_ids):
            for comment in threads.get(top_level_id, []):
                comment_text += (
                    CommentService.format_comment_for_display(comment, indent=0) + "\n"
                )

                if comment.id in threads:
                    for reply in threads[comment.id]:
                        comment_text += (
                            CommentService.format_comment_for_display(reply, indent=1)
                            + "\n"
                        )

                comment_text += "\n"

        comments_text = comment_text.rstrip()

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

    # Display objectives if present
    if objectives:
        from rich.markdown import Markdown
        from rich.panel import Panel

        md = Markdown(objectives)
        get_console().print(Panel(md, title="✅ Objectives", border_style="green"))
