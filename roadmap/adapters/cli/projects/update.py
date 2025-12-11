"""Update project command."""

import click

from roadmap.adapters.cli.crud import BaseUpdate, EntityType
from roadmap.adapters.cli.crud.entity_builders import ProjectBuilder
from roadmap.adapters.cli.helpers import require_initialized
from roadmap.infrastructure.logging import log_command


class ProjectUpdate(BaseUpdate):
    """Update project command implementation."""

    entity_type = EntityType.PROJECT

    def build_update_dict(self, entity_id: str, **kwargs) -> dict:
        """Build update dictionary for project."""
        return ProjectBuilder.build_update_dict(
            name=kwargs.get("name"),
            description=kwargs.get("description"),
            repository=kwargs.get("repository"),
            status=kwargs.get("status"),
        )


@click.command("update")
@click.argument("project_id")
@click.option("--name", help="Update project name")
@click.option("--description", "-d", help="Update project description")
@click.option("--repository", "-r", help="Update repository URL")
@click.option(
    "--status",
    type=click.Choice(["active", "inactive", "completed"]),
    help="Update project status",
)
@click.pass_context
@require_initialized
@log_command("project_update", entity_type="project", track_duration=True)
def update_project(
    ctx: click.Context,
    project_id: str,
    name: str,
    description: str,
    repository: str,
    status: str,
):
    """Update an existing project."""
    core = ctx.obj["core"]
    updater = ProjectUpdate(core)

    updater.execute(
        entity_id=project_id,
        name=name,
        description=description,
        repository=repository,
        status=status,
    )
