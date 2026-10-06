"""Create canonical projects."""

import click

from roadmap.adapters.inbound.cli.cli_command_helpers import require_initialized
from roadmap.adapters.inbound.cli.planning_resolution import invoke, projection_warning
from roadmap.application.contracts import ProjectCreateCommand
from roadmap.domain.types import Name, Priority


@click.command("create")
@click.option("--title", "-t", required=True, help="Project title")
@click.option("--description", "-d", help="Project description")
@click.option("--repository", "-r", help="Repository URL")
@click.option("--owner")
@click.option(
    "--priority",
    type=click.Choice(["critical", "high", "medium", "low"]),
    default="medium",
)
@click.option("--print-id", is_flag=True)
@click.pass_context
@require_initialized
def create_project(
    ctx,
    title: str,
    description: str | None,
    repository: str | None,
    owner: str | None,
    priority: str,
    print_id: bool,
) -> None:
    """Create a project through the Application boundary."""
    result = invoke(
        lambda: ctx.obj["core"].planning.create_project(
            ProjectCreateCommand(
                Name(title), description or "", repository, owner, Priority(priority)
            )
        )
    )
    project = result.aggregate
    click.echo(
        str(project.id)
        if print_id
        else f"Created project: [{project.id}] {project.name}"
    )
    projection_warning(result)
