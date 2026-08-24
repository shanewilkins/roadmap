"""Planning-command translation helpers."""

import click

from roadmap.adapters.inbound.cli.datetime_parser import UnifiedDateTimeParser
from roadmap.application.failures import ApplicationFailure
from roadmap.domain.failures import DomainFailure
from roadmap.domain.types import EntityId, Timestamp

__all__ = [
    "date_value",
    "invoke",
    "projection_warning",
    "resolve_milestone_id",
    "resolve_project_id",
]


def resolve_project_id(core, supplied: str) -> EntityId:
    return invoke(lambda: core.planning.resolve_project_id(supplied))


def resolve_milestone_id(core, supplied: str) -> EntityId:
    return invoke(lambda: core.planning.resolve_milestone_id(supplied))


def invoke(operation):
    """Translate stable application/domain failures into Click failures."""
    try:
        return operation()
    except (ApplicationFailure, DomainFailure, ValueError) as error:
        raise click.ClickException(str(error)) from error


def projection_warning(result) -> None:
    if getattr(result, "projection_stale", False):
        click.echo("Warning: SQLite projection is stale; canonical Markdown was saved.")


def date_value(value: str | None) -> Timestamp | None:
    if value is None:
        return None
    parsed = UnifiedDateTimeParser.parse_any_datetime(value)
    if parsed is None:
        raise click.ClickException(f"Invalid date: {value}")
    return Timestamp(parsed)
