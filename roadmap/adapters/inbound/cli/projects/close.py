"""Close canonical projects."""

import click

from roadmap.adapters.inbound.cli.cli_command_helpers import require_initialized
from roadmap.adapters.inbound.cli.planning_resolution import (
    invoke,
    projection_warning,
    resolve_project_id,
)


@click.command("close")
@click.argument("project_id")
@click.option(
    "--force", is_flag=True, help="Skip confirmation and open-milestone guard"
)
@click.pass_context
@require_initialized
def close_project(ctx, project_id: str, force: bool) -> None:
    """Mark a project completed without archiving it or its milestones."""
    core = ctx.obj["core"]
    identity = resolve_project_id(core, project_id)
    project = invoke(lambda: core.planning.project(str(identity))).project
    if not force:
        click.confirm(f"Close project '{project.name}'?", abort=True)
    result = invoke(lambda: core.planning.close_project(identity, force=force))
    click.echo(f"Closed project: [{identity}] {project.name}")
    projection_warning(result)
