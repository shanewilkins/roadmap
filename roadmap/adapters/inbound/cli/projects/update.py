"""Update canonical projects."""

import click

from roadmap.adapters.inbound.cli.cli_command_helpers import require_initialized
from roadmap.adapters.inbound.cli.planning_resolution import (
    invoke,
    projection_warning,
    resolve_project_id,
)
from roadmap.application.contracts import ProjectUpdateCommand
from roadmap.domain.types import Name, Priority, ProjectStatus


@click.command("update")
@click.argument("project_id")
@click.option("--name")
@click.option("--description", "-d")
@click.option("--repository", "-r")
@click.option("--status", type=click.Choice(["active", "inactive", "completed"]))
@click.option("--owner")
@click.option("--priority", type=click.Choice(["critical", "high", "medium", "low"]))
@click.option("--clear-owner", is_flag=True)
@click.pass_context
@require_initialized
def update_project(
    ctx,
    project_id: str,
    name: str | None,
    description: str | None,
    repository: str | None,
    status: str | None,
    owner: str | None,
    priority: str | None,
    clear_owner: bool,
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
                Name(name) if name is not None else None,
                description,
                repository,
                statuses[status] if status else None,
                priority=Priority(priority) if priority else None,
                owner=owner,
                clear_owner=clear_owner,
            )
        )
    )
    project = result.aggregate
    click.echo(f"Updated project: [{project.id}] {project.name}")
    projection_warning(result)
