"""Update milestone command."""

import click

from roadmap.adapters.cli.crud import BaseUpdate, EntityType
from roadmap.adapters.cli.crud.entity_builders import MilestoneBuilder
from roadmap.adapters.cli.helpers import require_initialized
from roadmap.infrastructure.logging import log_command


class MilestoneUpdate(BaseUpdate):
    """Update milestone command implementation."""

    entity_type = EntityType.MILESTONE

    def build_update_dict(self, entity_id: str, **kwargs) -> dict:
        """Build update dictionary for milestone."""
        return MilestoneBuilder.build_update_dict(
            name=kwargs.get("name"),
            description=kwargs.get("description"),
            due_date=kwargs.get("due_date"),
            status=kwargs.get("status"),
        )


@click.command("update")
@click.argument("milestone_id")
@click.option("--name", help="Update milestone name")
@click.option("--description", "-d", help="Update milestone description")
@click.option("--due-date", help="Update due date (YYYY-MM-DD format)")
@click.option(
    "--status",
    type=click.Choice(["open", "closed"]),
    help="Set milestone status (open|closed)",
)
@click.pass_context
@require_initialized
@log_command("milestone_update", entity_type="milestone", track_duration=True)
def update_milestone(
    ctx: click.Context,
    milestone_id: str,
    name: str,
    description: str,
    due_date: str,
    status: str,
):
    """Update an existing milestone."""
    core = ctx.obj["core"]
    updater = MilestoneUpdate(core)

    updater.execute(
        entity_id=milestone_id,
        name=name,
        description=description,
        due_date=due_date,
        status=status,
    )
