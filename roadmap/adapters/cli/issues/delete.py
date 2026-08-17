"""Permanently delete an archived issue."""

import click

from roadmap.adapters.cli.cli_command_helpers import require_initialized
from roadmap.adapters.cli.issues.resolution import invoke, resolve_issue_id
from roadmap.common.logging import log_command


@click.command("delete")
@click.argument("issue_id")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt")
@click.pass_context
@log_command("issue_delete", entity_type="issue", track_duration=True)
@require_initialized
def delete_issue(ctx: click.Context, issue_id: str, yes: bool) -> None:
    """Permanently purge an archived issue after an explicit confirmation."""
    core = ctx.obj["core"]
    identity = resolve_issue_id(core, issue_id)
    issue = invoke(lambda: core.issue_queries.view(identity)).issue
    if not yes:
        click.confirm(
            f"Permanently delete issue {identity} ({issue.title})?", abort=True
        )
    invoke(lambda: core.issue_mutations.purge(identity))
    click.echo(f"Deleted issue {identity}: {issue.title}")
