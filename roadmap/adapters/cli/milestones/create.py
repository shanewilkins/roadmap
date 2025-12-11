"""Create milestone command."""

import click

from roadmap.adapters.cli.crud import BaseCreate, EntityType
from roadmap.adapters.cli.crud.entity_builders import MilestoneBuilder
from roadmap.adapters.cli.helpers import require_initialized
from roadmap.infrastructure.logging import (
    log_command,
    verbose_output,
)


class MilestoneCreate(BaseCreate):
    """Create milestone command implementation."""

    entity_type = EntityType.MILESTONE

    def build_entity_dict(self, title: str, **kwargs) -> dict:
        """Build entity dictionary for milestone creation."""
        return MilestoneBuilder.build_create_dict(
            name=title,
            description=kwargs.get("description"),
            due_date=kwargs.get("due_date"),
        )


@click.command("create")
@click.argument("name")
@click.option("--description", "-d", default="", help="Milestone description")
@click.option("--due-date", help="Due date for milestone (YYYY-MM-DD format)")
@click.pass_context
@require_initialized
@verbose_output
@log_command("milestone_create", entity_type="milestone", track_duration=True)
def create_milestone(ctx: click.Context, name: str, description: str, due_date: str):
    """Create a new milestone."""
    core = ctx.obj["core"]
    creator = MilestoneCreate(core)

    creator.execute(
        title=name,
        description=description,
        due_date=due_date,
    )
