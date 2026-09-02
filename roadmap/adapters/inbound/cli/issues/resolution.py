"""Issue identity and input conversion at the CLI boundary."""

from collections.abc import Iterable

import click

from roadmap.adapters.inbound.cli.cli_command_helpers import invoke, projection_warning
from roadmap.domain.types import EntityId, Timestamp

__all__ = [
    "entity_id",
    "invoke",
    "projection_warning",
    "resolve_issue_id",
    "resolve_issue_ids",
    "timestamp",
]


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
