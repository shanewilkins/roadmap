"""Archive issues by changing canonical lifecycle metadata."""

import click

from roadmap.adapters.inbound.cli.cli_command_helpers import (
    confirm_override_action,
    echo_batch_result,
    require_initialized,
    validate_list_mode,
    verbose_message,
)
from roadmap.adapters.inbound.cli.issues.resolution import (
    invoke,
    projection_warning,
    resolve_issue_id,
)
from roadmap.application.contracts import IssueListQuery, IssueScope


def _list_archived_issues(core) -> None:
    records = invoke(
        lambda: core.issue_queries.list(IssueListQuery(scope=IssueScope.ARCHIVED))
    ).records
    if not records:
        click.echo("No archived issues.")
    for record in records:
        click.echo(f"{record.issue.id}  {record.issue.title}")


def _report_archive_result(result, dry_run: bool) -> None:
    echo_batch_result(
        "issue",
        result.issues,
        dry_run,
        action="archive",
        label=lambda issue: issue.title,
    )
    projection_warning(result)


@click.command("archive")
@click.argument("issue_id", required=False)
@click.option("--all-closed", is_flag=True, help="Archive every closed issue")
@click.option("--orphaned", is_flag=True, help="Archive issues without milestones")
@click.option("--list", "list_archived", is_flag=True, help="List archived issues")
@click.option("--dry-run", is_flag=True, help="Preview without saving")
@click.option("--force", is_flag=True, help="Allow non-closed issues and skip prompt")
@click.option(
    "--yes",
    "-y",
    is_flag=True,
    help="Skip confirmation without bypassing lifecycle guards",
)
@click.option("--verbose", "-v", is_flag=True)
@click.pass_context
@require_initialized
def archive_issue(
    ctx: click.Context,
    issue_id: str | None,
    all_closed: bool,
    orphaned: bool,
    list_archived: bool,
    dry_run: bool,
    force: bool,
    yes: bool,
    verbose: bool,  # noqa: ARG001
) -> None:
    """Archive issues in place; canonical Markdown files are not moved."""
    core = ctx.obj["core"]
    validate_list_mode(
        list_archived, (issue_id is not None, all_closed, dry_run, force, yes, orphaned)
    )
    if list_archived:
        verbose_message(verbose, "Listing archived records; lifecycle is unchanged.")
        _list_archived_issues(core)
        return
    if sum((issue_id is not None, all_closed, orphaned)) != 1:
        raise click.UsageError(
            "Specify exactly one of ISSUE_ID, --all-closed, or --orphaned"
        )
    identity = resolve_issue_id(core, issue_id) if issue_id else None
    confirm_override_action(dry_run, force, yes, "Archive the selected issue(s)?")
    result = invoke(
        lambda: core.issue_mutations.archive(
            identity,
            all_closed=all_closed,
            orphaned=orphaned,
            force=force,
            dry_run=dry_run,
        )
    )
    verbose_message(
        verbose,
        f"Validated {len(result.issues)} issue(s); {'preview only, no writes' if dry_run else 'canonical archive committed'}.",
    )
    _report_archive_result(result, dry_run)
