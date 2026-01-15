"""Delete milestone command."""

import click

from roadmap.adapters.cli.cli_command_helpers import require_initialized
from roadmap.adapters.cli.crud import BaseDelete, EntityType
from roadmap.infrastructure.logging import log_command


class MilestoneDelete(BaseDelete):
    """Delete milestone command implementation."""

    entity_type = EntityType.MILESTONE


@click.command("delete")
@click.argument("milestone_id")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt")
@click.pass_context
@require_initialized
@log_command("milestone_delete", entity_type="milestone", track_duration=True)
def delete_milestone(ctx: click.Context, milestone_id: str, yes: bool):
    """Delete a milestone."""
    core = ctx.obj["core"]
    deleter = MilestoneDelete(core)

    deleter.execute(entity_id=milestone_id, force=yes)
