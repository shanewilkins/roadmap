"""View a canonical issue through the target application query boundary."""

import click

from roadmap.adapters.inbound.cli.cli_command_helpers import require_initialized
from roadmap.adapters.inbound.cli.issues.query_presenter import IssueQueryPresenter
from roadmap.adapters.inbound.cli.issues.resolution import resolve_issue_id
from roadmap.application.failures import ApplicationFailure


@click.command("view")
@click.argument("issue_id")
@click.pass_context
@require_initialized
def view_issue(ctx: click.Context, issue_id: str) -> None:
    """Display one issue selected by a complete or unambiguous ID prefix."""
    core = ctx.obj["core"]
    service = core.issue_queries
    identity = resolve_issue_id(core, issue_id)
    try:
        record = service.view(identity)
    except ApplicationFailure as error:
        raise click.ClickException(str(error)) from error
    IssueQueryPresenter().render(record)
