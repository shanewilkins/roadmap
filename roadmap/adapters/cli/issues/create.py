"""Create issue command."""

import click

from roadmap.adapters.cli.crud import BaseCreate, EntityType
from roadmap.adapters.cli.crud.entity_builders import IssueBuilder
from roadmap.adapters.cli.helpers import require_initialized
from roadmap.common.cli_models import IssueCreateParams, IssueGitParams
from roadmap.infrastructure.logging import (
    log_command,
    verbose_output,
)


class IssueCreate(BaseCreate):
    """Create issue command implementation."""

    entity_type = EntityType.ISSUE

    def build_entity_dict(self, title: str, **kwargs) -> dict:
        """Build entity dictionary for issue creation."""
        from roadmap.core.services import IssueCreationService

        # Resolve and validate assignee (with auto-detection from Git)
        assignee = kwargs.get("assignee")
        service = IssueCreationService(self.core)
        assignee = service.resolve_and_validate_assignee(assignee, auto_detect=True)

        return IssueBuilder.build_create_dict(
            title=title,
            priority=kwargs.get("priority"),
            issue_type=kwargs.get("issue_type"),
            milestone=kwargs.get("milestone"),
            assignee=assignee,
            labels=list(kwargs.get("labels", [])),
            estimate=kwargs.get("estimate"),
            depends_on=list(kwargs.get("depends_on", [])),
            blocks=list(kwargs.get("blocks", [])),
            description=kwargs.get("description"),
        )

    def _display_success(self, entity) -> None:
        """Display success message using presenter."""
        # Use detailed service display which includes assignee, priority, etc.
        from roadmap.core.services import IssueCreationService

        service = IssueCreationService(self.core)
        service.format_created_issue_display(
            entity, milestone=getattr(entity, "milestone", None)
        )

    def post_create_hook(self, entity, **kwargs) -> None:
        """Handle post-creation tasks like Git branch creation."""
        if kwargs.get("git_branch"):
            from roadmap.core.services import IssueCreationService

            service = IssueCreationService(self.core)
            service.create_branch_for_issue(
                entity,
                kwargs.get("branch_name"),
                kwargs.get("checkout", True),
                kwargs.get("force", False),
            )


@click.command("create")
@click.argument("title")
@click.option(
    "--priority",
    "-p",
    type=click.Choice(["critical", "high", "medium", "low"]),
    default="medium",
    help="Issue priority",
)
@click.option(
    "--type",
    "-t",
    "issue_type",
    type=click.Choice(["feature", "bug", "other"]),
    default="other",
    help="Issue type",
)
@click.option("--milestone", "-m", help="Assign to milestone")
@click.option("--assignee", "-a", help="Assign to team member")
@click.option("--labels", "-l", multiple=True, help="Add labels")
@click.option(
    "--estimate", "-e", type=float, help="Estimated time to complete (in hours)"
)
@click.option("--depends-on", multiple=True, help="Issue IDs this depends on")
@click.option("--blocks", multiple=True, help="Issue IDs this blocks")
@click.option("--description", "-d", help="Markdown description of the issue")
@click.option("--git-branch", is_flag=True, help="Create a Git branch for this issue")
@click.option(
    "--checkout/--no-checkout",
    default=True,
    help="Checkout the branch after creation (with --git-branch)",
)
@click.option("--branch-name", default=None, help="Override suggested branch name")
@click.option(
    "--force", is_flag=True, help="Force branch creation even if working tree is dirty"
)
@click.pass_context
@verbose_output
@log_command("issue_create", entity_type="issue", track_duration=True)
@require_initialized
def create_issue(
    ctx: click.Context,
    title: str,
    priority: str,
    issue_type: str,
    milestone: str,
    assignee: str,
    labels: tuple,
    estimate: float,
    depends_on: tuple,
    blocks: tuple,
    description: str,
    git_branch: bool,
    checkout: bool,
    branch_name: str,
    force: bool,
):
    """Create a new issue."""
    core = ctx.obj["core"]
    creator = IssueCreate(core)

    # Create structured parameter objects
    issue_params = IssueCreateParams(
        title=title,
        priority=priority,
        issue_type=issue_type,
        milestone=milestone,
        assignee=assignee,
        labels=labels,
        estimate=estimate,
        depends_on=depends_on,
        blocks=blocks,
        description=description,
    )
    git_params = IssueGitParams(
        git_branch=git_branch,
        checkout=checkout,
        branch_name=branch_name,
        force=force,
    )

    creator.execute(
        title=issue_params.title,
        priority=issue_params.priority,
        issue_type=issue_params.issue_type,
        milestone=issue_params.milestone,
        assignee=issue_params.assignee,
        labels=issue_params.labels,
        estimate=issue_params.estimate,
        depends_on=issue_params.depends_on,
        blocks=issue_params.blocks,
        description=issue_params.description,
        git_branch=git_params.git_branch,
        checkout=git_params.checkout,
        branch_name=git_params.branch_name,
        force=git_params.force,
    )
