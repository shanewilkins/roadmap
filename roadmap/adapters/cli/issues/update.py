"""Update issue command."""

import click

from roadmap.adapters.cli.cli_command_helpers import require_initialized
from roadmap.adapters.cli.crud import BaseUpdate, EntityType
from roadmap.adapters.cli.crud.entity_builders import IssueBuilder
from roadmap.adapters.cli.presentation.crud_presenter import UpdatePresenter
from roadmap.common.logging import (
    log_command,
)
from roadmap.common.models import IssueUpdateParams


class IssueUpdate(BaseUpdate):
    """Update issue command implementation."""

    entity_type = EntityType.ISSUE

    def __init__(self, core):
        """Initialize IssueUpdate."""
        super().__init__(core)
        self._current_update_dict = {}
        self._current_reason = None

    def build_update_dict(self, entity_id: str, **kwargs) -> dict:
        """Build update dictionary for issue."""
        return IssueBuilder.build_update_dict(
            title=kwargs.get("title"),
            priority=kwargs.get("priority"),
            status=kwargs.get("status"),
            assignee=kwargs.get("assignee"),
            milestone=kwargs.get("milestone"),
            description=kwargs.get("description"),
            estimate=kwargs.get("estimate"),
        )

    def execute(self, entity_id: str, **kwargs):
        """Execute update and display results using proper formatter.

        Overrides parent to store update_dict and reason for display.
        """
        # Store for use in _display_success
        self._current_update_dict = self.build_update_dict(
            entity_id=entity_id, **kwargs
        )
        self._current_reason = kwargs.get("reason")

        # Call parent execute which will call _display_success
        return super().execute(entity_id=entity_id, **kwargs)

    def _display_success(self, entity) -> None:
        """Display success message using presenter."""
        presenter = UpdatePresenter()
        presenter.render(entity, self._current_update_dict)


@click.command("update")
@click.argument("issue_id")
@click.option("--title", help="Update issue title")
@click.option(
    "--priority",
    "-p",
    type=click.Choice(["critical", "high", "medium", "low"]),
    help="Update priority",
)
@click.option(
    "--status",
    "-s",
    type=click.Choice(["todo", "in-progress", "blocked", "review", "closed"]),
    help="Update status",
)
@click.option("--assignee", "-a", help="Update assignee")
@click.option("--milestone", "-m", help="Update milestone")
@click.option("--description", "-d", help="Update description")
@click.option("--estimate", "-e", type=float, help="Update estimated time (in hours)")
@click.option("--reason", "-r", help="Reason for the update")
@click.pass_context
@log_command("issue_update", entity_type="issue", track_duration=True)
@require_initialized
def update_issue(
    ctx: click.Context,
    issue_id: str,
    title: str,
    priority: str,
    status: str,
    assignee: str,
    milestone: str,
    description: str,
    estimate: float,
    reason: str,
):
    """Update an existing issue."""
    core = ctx.obj["core"]
    updater = IssueUpdate(core)

    # Create structured parameter object
    params = IssueUpdateParams(
        issue_id=issue_id,
        title=title,
        priority=priority,
        status=status,
        assignee=assignee,
        milestone=milestone,
        content=description,
        estimate=estimate,
        reason=reason,
    )

    updater.execute(
        entity_id=params.issue_id,
        title=params.title,
        priority=params.priority,
        status=params.status,
        assignee=params.assignee,
        milestone=params.milestone,
        content=params.content,
        estimate=params.estimate,
        reason=params.reason,
    )
