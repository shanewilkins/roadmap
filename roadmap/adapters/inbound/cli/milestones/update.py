"""Update canonical milestones."""

import click

from roadmap.adapters.inbound.cli.cli_command_helpers import require_initialized
from roadmap.adapters.inbound.cli.instrumentation import log_command
from roadmap.adapters.inbound.cli.planning_resolution import (
    date_value,
    invoke,
    projection_warning,
    resolve_milestone_id,
    resolve_project_id,
)
from roadmap.application.contracts import MilestoneUpdateCommand
from roadmap.domain.types import MilestoneStatus, Name


@click.command("update")
@click.argument("milestone_id")
@click.option("--name")
@click.option("--description", "-d")
@click.option("--due-date")
@click.option("--status", type=click.Choice(["open", "closed"]))
@click.option("--project", "-p", default=None)
@click.pass_context
@require_initialized
@log_command("milestone_update", entity_type="milestone", track_duration=True)
def update_milestone(
    ctx,
    milestone_id: str,
    name: str | None,
    description: str | None,
    due_date: str | None,
    status: str | None,
    project: str | None,
) -> None:
    """Update a milestone and its reciprocal project relation."""
    core = ctx.obj["core"]
    result = invoke(
        lambda: core.planning.update_milestone(
            MilestoneUpdateCommand(
                resolve_milestone_id(core, milestone_id),
                Name(name) if name else None,
                description,
                date_value(due_date),
                MilestoneStatus(status) if status else None,
                resolve_project_id(core, project) if project else None,
            )
        )
    )
    milestone = result.aggregate
    click.echo(f"Updated milestone: [{milestone.id}] {milestone.name}")
    projection_warning(result)
