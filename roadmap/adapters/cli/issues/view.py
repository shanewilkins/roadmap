"""View a canonical issue through the target application query boundary."""

import click

from roadmap.adapters.cli.cli_command_helpers import require_initialized
from roadmap.adapters.cli.issues.query_presenter import IssueQueryPresenter
from roadmap.application.failures import ApplicationFailure
from roadmap.domain.types import EntityId


def _resolve_prefix(service, supplied: str) -> EntityId:
    try:
        requested = EntityId(supplied)
    except ValueError as error:
        raise click.ClickException(str(error)) from error
    identities = service.ids()
    if requested in identities:
        return requested
    matches: tuple[EntityId, ...] = tuple(
        identity for identity in identities if identity.startswith(requested)
    )
    if not matches:
        raise click.ClickException(f"Issue '{supplied}' was not found")
    if len(matches) > 1:
        raise click.ClickException(
            f"Ambiguous issue ID prefix '{supplied}'; use a complete ID"
        )
    return next(iter(matches))


@click.command("view")
@click.argument("issue_id")
@click.pass_context
@require_initialized
def view_issue(ctx: click.Context, issue_id: str) -> None:
    """Display one issue selected by a complete or unambiguous ID prefix."""
    service = ctx.obj["core"].issue_queries
    identity = _resolve_prefix(service, issue_id)
    try:
        record = service.view(identity)
    except ApplicationFailure as error:
        raise click.ClickException(str(error)) from error
    IssueQueryPresenter().render(record)
