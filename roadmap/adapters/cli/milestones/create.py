"""Create canonical milestones."""

import re

import click

from roadmap.adapters.cli.cli_command_helpers import require_initialized
from roadmap.adapters.cli.planning_resolution import (
    date_value,
    invoke,
    projection_warning,
    resolve_project_id,
)
from roadmap.application.contracts import MilestoneCreateCommand
from roadmap.common.logging import log_command, verbose_output
from roadmap.domain.types import Name


def _validate_milestone_name(name: str) -> tuple[bool, str | None]:
    if not re.match(r"^[a-zA-Z0-9_\-\.]+$", name):
        return (
            False,
            "Milestone name contains invalid characters. Use only: letters, numbers, hyphens, underscores, dots",
        )
    if re.match(r"^v\d+\.\d+", name):
        return (
            False,
            f"Version milestones should use hyphens, not dots.\n  Current:  {name}\n  Suggested: {name.replace('.', '-')}",
        )
    return True, None


@click.command("create")
@click.option("--title", "-t", required=True, help="Milestone title")
@click.option("--description", "-d", default="", help="Milestone description")
@click.option("--due-date", help="Due date for milestone (YYYY-MM-DD format)")
@click.option("--project", "-p", default=None, help="Project ID")
@click.pass_context
@require_initialized
@verbose_output
@log_command("milestone_create", entity_type="milestone", track_duration=True)
def create_milestone(
    ctx, title: str, description: str, due_date: str | None, project: str | None
) -> None:
    """Create a milestone and link it to a project atomically."""
    valid, error = _validate_milestone_name(title)
    if not valid:
        raise click.ClickException(error or "Invalid milestone name")
    core = ctx.obj["core"]
    project_id = resolve_project_id(core, project) if project else None
    if project_id is None:
        visible = tuple(
            item
            for item in core.planning.all_projects()
            if item.retention.value == "visible"
        )
        if len(visible) == 1:
            project_id = visible[0].id
            click.echo(
                f"Assigning milestone to project: {visible[0].name} ({project_id})"
            )
        elif len(visible) > 1:
            raise click.ClickException(
                f"Multiple projects found ({len(visible)}). Please specify project with --project flag."
            )
    result = invoke(
        lambda: core.planning.create_milestone(
            MilestoneCreateCommand(
                Name(title), description, date_value(due_date), project_id
            )
        )
    )
    milestone = result.aggregate
    click.echo(f"Created milestone: [{milestone.id}] {milestone.name}")
    projection_warning(result)
