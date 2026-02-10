"""Create milestone command."""

import re

import click

from roadmap.adapters.cli.cli_command_helpers import require_initialized
from roadmap.adapters.cli.crud import BaseCreate, EntityType
from roadmap.adapters.cli.crud.entity_builders import MilestoneBuilder
from roadmap.common.logging import (
    log_command,
    verbose_output,
)


def _validate_milestone_name(name: str) -> tuple[bool, str | None]:
    """Validate milestone name against naming conventions.

    Args:
        name: The milestone name to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check for invalid characters
    if not re.match(r"^[a-zA-Z0-9_\-\.]+$", name):
        return (
            False,
            "Milestone name contains invalid characters. Use only: letters, numbers, hyphens, underscores, dots",
        )

    # Check for version patterns with dots (should use hyphens instead)
    if re.match(r"^v\d+\.\d+", name):  # e.g., v1.0., v1.0.2, v2.0
        suggested = name.replace(".", "-")
        return (
            False,
            f"Version milestones should use hyphens, not dots.\n"
            f"  Current:  {name}\n"
            f"  Suggested: {suggested}",
        )

    # Valid milestone name
    return True, None


class MilestoneCreate(BaseCreate):
    """Create milestone command implementation."""

    entity_type = EntityType.MILESTONE

    def build_entity_dict(self, title: str, **kwargs) -> dict:
        """Build entity dictionary for milestone creation."""
        create_dict = MilestoneBuilder.build_create_dict(
            name=title,
            description=kwargs.get("description"),
            due_date=kwargs.get("due_date"),
        )

        # Add project_id if provided or auto-detected
        if kwargs.get("project_id"):
            create_dict["project_id"] = kwargs.get("project_id")

        return create_dict


@click.command("create")
@click.option("--title", "-t", required=True, help="Milestone title")
@click.option("--description", "-d", default="", help="Milestone description")
@click.option("--due-date", help="Due date for milestone (YYYY-MM-DD format)")
@click.option("--project", "-p", default=None, help="Project ID to assign milestone to")
@click.pass_context
@require_initialized
@verbose_output
@log_command("milestone_create", entity_type="milestone", track_duration=True)
def create_milestone(
    ctx: click.Context,
    title: str,
    description: str,
    due_date: str,
    project: str | None,
):
    """Create a new milestone."""
    # Validate milestone name against naming conventions
    is_valid, error_msg = _validate_milestone_name(title)
    if not is_valid:
        if error_msg is None:
            error_msg = "Invalid milestone name"
        raise click.ClickException(error_msg)

    core = ctx.obj["core"]
    creator = MilestoneCreate(core)

    # Auto-detect project if not provided
    project_id = project
    if not project_id:
        from roadmap.common.configuration import ConfigManager

        # Try to get default project from config
        config_manager = ConfigManager(core.config_file)
        config = config_manager.load()

        if config.behavior.default_project_id:
            project_id = config.behavior.default_project_id
            click.echo(
                f"ℹ️  Assigning milestone to default project: {project_id}", err=False
            )
        else:
            # Check how many projects exist
            all_projects = list(core.projects.list())
            if all_projects:
                # Projects exist but no default - need clarification
                if len(all_projects) > 1:
                    raise click.ClickException(
                        f"Multiple projects found ({len(all_projects)}). Please specify project with --project flag.\n"
                        f"Available projects: {', '.join(p.id for p in all_projects)}"
                    )
                else:
                    # Auto-assign to the only project
                    project_id = all_projects[0].id
                    click.echo(
                        f"ℹ️  Assigning milestone to project: {all_projects[0].name} ({project_id})",
                        err=False,
                    )
            # If no projects exist, that's OK - milestone can be created without a project

    creator.execute(
        title=title,
        description=description,
        due_date=due_date,
        project_id=project_id,
    )
