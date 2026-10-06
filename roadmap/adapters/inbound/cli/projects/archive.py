"""Archive projects through lifecycle metadata."""

import click

from roadmap.adapters.inbound.cli.cli_command_helpers import (
    confirm_override_action,
    echo_archived_list,
    echo_batch_result,
    require_initialized,
    validate_list_mode,
    verbose_message,
)
from roadmap.adapters.inbound.cli.planning_resolution import invoke, projection_warning
from roadmap.domain.types import RetentionState


def _list_archived_projects(core) -> None:
    values = [
        item
        for item in core.planning.all_projects()
        if item.retention is RetentionState.ARCHIVED
    ]
    echo_archived_list("project", values)


def _report_archive_result(result, dry_run: bool) -> None:
    echo_batch_result("project", result.aggregates, dry_run, action="archive")
    projection_warning(result)


@click.command("archive")
@click.argument("project_name", required=False)
@click.option("--all-closed", is_flag=True)
@click.option("--list", "list_archived", is_flag=True)
@click.option("--dry-run", is_flag=True)
@click.option(
    "--force",
    is_flag=True,
    help="Allow non-completed records; legacy confirmation shortcut deprecated for 0.4",
)
@click.option(
    "--yes",
    "-y",
    is_flag=True,
    help="Skip confirmation without bypassing lifecycle guards",
)
@click.option("--verbose", "-v", is_flag=True)
@click.pass_context
@require_initialized
def archive_project(
    ctx,
    project_name: str | None,
    all_closed: bool,
    list_archived: bool,
    dry_run: bool,
    force: bool,
    yes: bool,
    verbose: bool,
) -> None:  # noqa: ARG001
    """Archive projects in place without cascading to milestones or issues."""
    core = ctx.obj["core"]
    validate_list_mode(
        list_archived, (project_name is not None, all_closed, dry_run, force, yes)
    )
    if list_archived:
        verbose_message(verbose, "Listing archived records; lifecycle is unchanged.")
        _list_archived_projects(core)
        return
    if (project_name is None) == (not all_closed):
        raise click.UsageError("Specify exactly one of PROJECT_NAME or --all-closed")
    confirm_override_action(dry_run, force, yes, "Archive the selected project(s)?")
    result = invoke(
        lambda: core.planning.archive_project(
            project_name, all_closed=all_closed, dry_run=dry_run, force=force
        )
    )
    verbose_message(
        verbose,
        f"Validated {len(result.aggregates)} project(s); {'preview only, no writes' if dry_run else 'canonical archive committed'}.",
    )
    _report_archive_result(result, dry_run)
