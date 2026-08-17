"""Issue identity and input conversion at the CLI boundary."""

from collections.abc import Iterable

import click

from roadmap.application.failures import ApplicationFailure
from roadmap.domain.failures import DomainFailure
from roadmap.domain.types import EntityId, Timestamp


def resolve_issue_id(core, supplied: str) -> EntityId:
    """Resolve a complete or unambiguous issue identity prefix."""
    try:
        requested = EntityId(supplied)
    except ValueError as error:
        raise click.ClickException(str(error)) from error
    identities: tuple[EntityId, ...] = tuple(core.issue_queries.ids())
    if requested in identities:
        return requested
    matches: tuple[EntityId, ...] = tuple(
        item for item in identities if item.startswith(requested)
    )
    if not matches:
        raise click.ClickException(f"Issue '{supplied}' was not found")
    if len(matches) > 1:
        raise click.ClickException(
            f"Ambiguous issue ID prefix '{supplied}'; use a complete ID"
        )
    return next(iter(matches))


def resolve_issue_ids(core, supplied: Iterable[str]) -> tuple[EntityId, ...]:
    return tuple(resolve_issue_id(core, item) for item in supplied)


def entity_id(value: str | None) -> EntityId | None:
    if value is None:
        return None
    try:
        return EntityId(value)
    except ValueError as error:
        raise click.ClickException(str(error)) from error


def timestamp(value) -> Timestamp:
    try:
        return Timestamp(value)
    except ValueError as error:
        raise click.ClickException(str(error)) from error


def invoke(operation):
    """Translate stable application/domain failures into Click failures."""
    try:
        return operation()
    except (ApplicationFailure, DomainFailure, ValueError) as error:
        raise click.ClickException(str(error)) from error


def projection_warning(result) -> None:
    if getattr(result, "projection_stale", False):
        click.echo("Warning: SQLite projection is stale; canonical Markdown was saved.")
