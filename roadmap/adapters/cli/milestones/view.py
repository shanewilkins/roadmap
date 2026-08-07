"""View milestone command."""

import click

from roadmap.adapters.cli.cli_command_helpers import require_initialized
from roadmap.adapters.cli.mappers import MilestoneMapper
from roadmap.adapters.cli.presentation.milestone_presenter import MilestonePresenter
from roadmap.common.console import get_console


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
        get_console().print(
            f"❌ Milestone '{milestone_name}' not found.", style="bold red"
        )
        get_console().print(
            "\n💡 Tip: Use 'roadmap milestone list' to see all available milestones.",
            style="dim",
        )
        ctx.exit(1)

    # Convert milestone to DTO
    milestone_dto = MilestoneMapper.domain_to_dto(milestone)

    # Get milestone issues and filter
    all_issues = core.issues.list()
    milestone_issues = milestone.get_issues(all_issues)
    milestone_issues = _filter_milestone_issues(
        milestone_issues, status, priority, only_open
    )

    # Get progress data
    progress_data = core.milestones.get_progress(milestone_name)

    # Extract description and goals
    description_content = milestone.content if milestone.content else None

    # Prepare comments if any
    comments_text = None
    if milestone.comments:
        from roadmap.core.services.comment.comment_service import CommentService

        threads = CommentService.build_comment_threads(milestone.comments)
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
    presenter = MilestonePresenter()
    presenter.render(
        milestone_dto,
        issues=milestone_issues if milestone_issues else None,
        progress_data=progress_data,
        description_content=description_content,
        comments_text=comments_text,
    )

    # Display file info
    get_console().print(f"[dim]File: .roadmap/milestones/{milestone.name}.md[/dim]")
