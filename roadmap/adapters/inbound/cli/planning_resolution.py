"""Planning-command translation helpers."""

import click

from roadmap.adapters.inbound.cli.cli_command_helpers import invoke, projection_warning
from roadmap.adapters.inbound.cli.datetime_parser import UnifiedDateTimeParser
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


def date_value(value: str | None) -> Timestamp | None:
    if value is None:
        return None
    parsed = UnifiedDateTimeParser.parse_any_datetime(value)
    if parsed is None:
        raise click.ClickException(f"Invalid date: {value}")
    return Timestamp(parsed)
