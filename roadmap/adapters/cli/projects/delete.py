"""Delete project command."""

import click

from roadmap.adapters.cli.cli_command_helpers import require_initialized
from roadmap.adapters.cli.crud import BaseDelete, EntityType
from roadmap.common.logging import log_command


class ProjectDelete(BaseDelete):
    """Delete project command implementation."""

    entity_type = EntityType.PROJECT


@click.command("delete")
@click.argument("project_id")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt")
@click.pass_context
@require_initialized
@log_command("project_delete", entity_type="project", track_duration=True)
def delete_project(ctx: click.Context, project_id: str, yes: bool):
    """Delete a project."""
    core = ctx.obj["core"]
    deleter = ProjectDelete(core)

    deleter.execute(entity_id=project_id, force=yes)
