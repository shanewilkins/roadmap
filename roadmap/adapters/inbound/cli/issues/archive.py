"""Archive issues by changing canonical lifecycle metadata."""

import click

from roadmap.adapters.inbound.cli.cli_command_helpers import require_initialized
from roadmap.adapters.inbound.cli.instrumentation import log_command, verbose_output
from roadmap.adapters.inbound.cli.issues.resolution import (
    invoke,
    projection_warning,
    resolve_issue_id,
)
from roadmap.application.contracts import IssueListQuery, IssueScope


@click.command("archive")
@click.argument("issue_id", required=False)
@click.option("--all-closed", is_flag=True, help="Archive every closed issue")
@click.option("--orphaned", is_flag=True, help="Archive issues without milestones")
@click.option("--list", "list_archived", is_flag=True, help="List archived issues")
@click.option("--dry-run", is_flag=True, help="Preview without saving")
@click.option("--force", is_flag=True, help="Allow non-closed issues and skip prompt")
@click.option("--verbose", "-v", is_flag=True)
@click.pass_context
@verbose_output
@log_command("issue_archive", entity_type="issue", track_duration=True)
@require_initialized
def archive_issue(
    ctx: click.Context,
    issue_id: str | None,
    all_closed: bool,
    orphaned: bool,
    list_archived: bool,
    dry_run: bool,
    force: bool,
    verbose: bool,  # noqa: ARG001
) -> None:
    """Archive issues in place; canonical Markdown files are not moved."""
    core = ctx.obj["core"]
    if list_archived:
        records = invoke(
            lambda: core.issue_queries.list(IssueListQuery(scope=IssueScope.ARCHIVED))
        ).records
        if not records:
            click.echo("No archived issues.")
        for record in records:
            click.echo(f"{record.issue.id}  {record.issue.title}")
        return
    if sum((issue_id is not None, all_closed, orphaned)) != 1:
        raise click.UsageError(
            "Specify exactly one of ISSUE_ID, --all-closed, or --orphaned"
        )
    identity = resolve_issue_id(core, issue_id) if issue_id else None
    if not dry_run and not force:
        click.confirm("Archive the selected issue(s)?", abort=True)
    result = invoke(
        lambda: core.issue_mutations.archive(
            identity,
            all_closed=all_closed,
            orphaned=orphaned,
            force=force,
            dry_run=dry_run,
        )
    )
    verb = "Would archive" if dry_run else "Archived"
    for issue in result.issues:
        click.echo(f"{verb} issue {issue.id}: {issue.title}")
    if not result.issues:
        click.echo("No matching issues.")
    projection_warning(result)
