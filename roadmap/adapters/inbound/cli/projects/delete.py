"""Permanently delete archived projects."""

import click

from roadmap.adapters.inbound.cli.cli_command_helpers import require_initialized
from roadmap.adapters.inbound.cli.instrumentation import log_command
from roadmap.adapters.inbound.cli.planning_resolution import invoke, resolve_project_id


@click.command("delete")
@click.argument("project_id")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt")
@click.pass_context
@require_initialized
@log_command("project_delete", entity_type="project", track_duration=True)
def delete_project(ctx, project_id: str, yes: bool) -> None:
    """Purge an archived, unreferenced project."""
    core = ctx.obj["core"]
    identity = resolve_project_id(core, project_id)
    project = invoke(
        lambda: core.planning.project(str(identity), include_archived=True)
    ).project
    if not yes:
        click.confirm(
            f"Permanently delete project {identity} ({project.name})?", abort=True
        )
    invoke(lambda: core.planning.purge_project(identity))
    click.echo(f"Deleted project {identity}: {project.name}")
