"""Restore archived issues through canonical lifecycle metadata."""

import click

from roadmap.adapters.inbound.cli.cli_command_helpers import require_initialized
from roadmap.adapters.inbound.cli.issues.resolution import (
    invoke,
    projection_warning,
    resolve_issue_id,
)
from roadmap.domain.types import IssueStatus


@click.command("restore")
@click.argument("issue_id", required=False)
@click.option("--all", "restore_all", is_flag=True, help="Restore every archive")
@click.option(
    "--status",
    type=click.Choice(["todo", "in-progress", "blocked", "review", "closed"]),
)
@click.option("--dry-run", is_flag=True, help="Preview without saving")
@click.option("--force", is_flag=True, help="Skip confirmation prompt")
@click.option("--verbose", "-v", is_flag=True)
@click.pass_context
@require_initialized
def restore_issue(
    ctx: click.Context,
    issue_id: str | None,
    restore_all: bool,
    status: str | None,
    dry_run: bool,
    force: bool,
    verbose: bool,  # noqa: ARG001
) -> None:
    """Restore archived issues without moving their Markdown files."""
    if (issue_id is None) == (not restore_all):
        raise click.UsageError("Specify exactly one of ISSUE_ID or --all")
    core = ctx.obj["core"]
    identity = resolve_issue_id(core, issue_id) if issue_id else None
    if not dry_run and not force:
        click.confirm("Restore the selected issue(s)?", abort=True)
    result = invoke(
        lambda: core.issue_mutations.restore(
            identity,
            restore_all=restore_all,
            status=IssueStatus(status) if status else None,
            dry_run=dry_run,
        )
    )
    verb = "Would restore" if dry_run else "Restored"
    for issue in result.issues:
        click.echo(f"{verb} issue {issue.id}: {issue.title}")
    if not result.issues:
        click.echo("No matching issues.")
    projection_warning(result)
