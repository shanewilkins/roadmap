"""Create project command."""

import click

from roadmap.adapters.cli.cli_command_helpers import require_initialized
from roadmap.adapters.cli.crud import BaseCreate, EntityType
from roadmap.adapters.cli.crud.entity_builders import ProjectBuilder
from roadmap.common.logging import (
    log_command,
    verbose_output,
)


class ProjectCreate(BaseCreate):
    """Create project command implementation."""

    entity_type = EntityType.PROJECT

    def build_entity_dict(self, title: str, **kwargs) -> dict:
        """Build entity dictionary for project creation."""
        return ProjectBuilder.build_create_dict(
            name=title,
            description=kwargs.get("description"),
            repository=kwargs.get("repository"),
        )


@click.command("create")
@click.argument("name")
@click.option("--description", "-d", help="Project description")
@click.option("--repository", "-r", help="Repository URL")
@click.pass_context
@require_initialized
@verbose_output
@log_command("project_create", entity_type="project", track_duration=True)
def create_project(
    ctx: click.Context,
    name: str,
    description: str,
    repository: str,
):
    """Create a new project."""
    core = ctx.obj["core"]
    creator = ProjectCreate(core)

    creator.execute(
        title=name,
        description=description,
        repository=repository,
    )
