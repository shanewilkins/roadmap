"""Update canonical projects."""

import click

from roadmap.adapters.cli.cli_command_helpers import require_initialized
from roadmap.adapters.cli.planning_resolution import (
    invoke,
    projection_warning,
    resolve_project_id,
)
from roadmap.application.contracts import ProjectUpdateCommand
from roadmap.common.logging import log_command
from roadmap.domain.types import Name, ProjectStatus


@click.command("update")
@click.argument("project_id")
@click.option("--name")
@click.option("--description", "-d")
@click.option("--repository", "-r")
@click.option("--status", type=click.Choice(["active", "inactive", "completed"]))
@click.pass_context
@require_initialized
@log_command("project_update", entity_type="project", track_duration=True)
def update_project(
    ctx,
    project_id: str,
    name: str | None,
    description: str | None,
    repository: str | None,
    status: str | None,
) -> None:
    """Update a project through the Application boundary."""
    core = ctx.obj["core"]
    statuses = {
        "active": ProjectStatus.ACTIVE,
        "inactive": ProjectStatus.ON_HOLD,
        "completed": ProjectStatus.COMPLETED,
    }
    result = invoke(
        lambda: core.planning.update_project(
            ProjectUpdateCommand(
                resolve_project_id(core, project_id),
                Name(name) if name else None,
                description,
                repository,
                statuses[status] if status else None,
            )
        )
    )
    project = result.aggregate
    click.echo(f"Updated project: [{project.id}] {project.name}")
    projection_warning(result)
