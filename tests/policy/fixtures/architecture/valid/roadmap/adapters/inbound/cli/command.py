"""Valid inbound adapter dependencies."""

import click
from roadmap.adapters.inbound.cli.helper import normalize
from roadmap.application.dto import Request


def request(value: str) -> Request:
    """Translate fixture CLI input."""
    click.echo(normalize(value))
    return Request(value)
