"""Update issue command."""

import click

from roadmap.adapters.cli.crud import BaseUpdate, EntityType
from roadmap.adapters.cli.crud.entity_builders import IssueBuilder
from roadmap.adapters.cli.helpers import require_initialized
from roadmap.common.cli_models import IssueUpdateParams
from roadmap.infrastructure.logging import (
    log_command,
)


class IssueUpdate(BaseUpdate):
    """Update issue command implementation."""

    entity_type = EntityType.ISSUE

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

    def _display_success(self, entity) -> None:
        """Display detailed success message for issue update."""
        # Display in a similar format to creation but with "Updated"
        try:
            title = self._get_title(entity)
            entity_id = self._get_id(entity)

            self.console.print(f"✅ Updated issue: {title}", style="bold green")
            self.console.print(f"   ID: {entity_id}", style="cyan")
            if hasattr(entity, "issue_type"):
                self.console.print(f"   type: {entity.issue_type.value}", style="blue")
            if hasattr(entity, "priority"):
                self.console.print(
                    f"   priority: {entity.priority.value}", style="yellow"
                )
            if hasattr(entity, "estimated_hours") and entity.estimated_hours:
                self.console.print(
                    f"   estimate: {entity.estimated_time_display}", style="green"
                )
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
