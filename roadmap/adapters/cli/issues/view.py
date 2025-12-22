"""View issue command."""

import click

from roadmap.adapters.cli.dtos import IssueDTO
from roadmap.adapters.cli.helpers import ensure_entity_exists, require_initialized
from roadmap.adapters.cli.mappers import IssueMapper
from roadmap.adapters.cli.presentation.issue_presenter import IssuePresenter


@click.command("view")
@click.argument("issue_id")
@click.pass_context
@require_initialized
def view_issue(ctx: click.Context, issue_id: str):
    """Display detailed information about a specific issue.

    Shows complete issue details including metadata, timeline, description,
    and acceptance criteria in a formatted view.

    Example:
        roadmap issue view abc123def
    """
    core = ctx.obj["core"]

    # Retrieve the domain issue from the repository
    issue = ensure_entity_exists(core, "issue", issue_id)

    # Convert domain issue to DTO for presentation
    issue_dto = IssueMapper.domain_to_dto(issue)

    # Use presenter to render the issue
    presenter = IssuePresenter()
    presenter.render(issue_dto)

