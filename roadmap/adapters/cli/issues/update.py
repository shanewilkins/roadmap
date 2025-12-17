"""Update issue command."""

import click

from roadmap.adapters.cli.crud import BaseUpdate, EntityType
from roadmap.adapters.cli.crud.entity_builders import IssueBuilder
from roadmap.adapters.cli.helpers import require_initialized
from roadmap.common.cli_models import IssueUpdateParams
from roadmap.common.update_constants import DISPLAYABLE_UPDATE_FIELDS
from roadmap.infrastructure.logging import (
    log_command,
)


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
        """Display detailed success message for issue update."""
        # Use the same display logic as IssueUpdateService.display_update_result
        try:
            self.console.print(f"✅ Updated issue: {entity.title}", style="bold green")
            self.console.print(f"   ID: {entity.id}", style="cyan")

            # Show what was updated
            for field, value in self._current_update_dict.items():
                if field == "estimated_hours":
                    # Use the value directly from the update dict, not from entity
                    # This avoids stale cache/file read issues
                    hours = value
                    if hours is None:
                        display_value = "Not estimated"
                    elif hours < 1:
                        minutes = int(hours * 60)
                        display_value = f"{minutes}m"
                    elif hours < 8:
                        display_value = f"{hours:.1f}h"
                    else:
                        days = hours / 8
                        display_value = f"{days:.1f}d"
                    self.console.print(f"   estimate: {display_value}", style="cyan")
                elif field in DISPLAYABLE_UPDATE_FIELDS:
                    # Format enum values to show just the string value
                    display_value = value.value if hasattr(value, "value") else value
                    self.console.print(f"   {field}: {display_value}", style="cyan")

            if self._current_reason:
                self.console.print(f"   reason: {self._current_reason}", style="dim")
        except (AttributeError, TypeError):
            # Fallback for mocks or incomplete entities
            title = self._get_title(entity)
            entity_id = self._get_id(entity)
            self.console.print(
                f"✅ Updated issue: {title} [{entity_id}]",
                style="green",
            )


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
        description=description,
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
        description=params.description,
        estimate=params.estimate,
        reason=params.reason,
    )
