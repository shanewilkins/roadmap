"""
Core CLI commands: init and status.

These are the fundamental commands needed to get started with Roadmap.
"""

import click

from roadmap.adapters.cli.init import init
from roadmap.adapters.cli.status import health, status
from roadmap.common.logging import get_logger

logger = get_logger(__name__)


@click.group()
@click.pass_context
def core(ctx: click.Context) -> None:
    """Core roadmap commands for initialization and status."""
    if ctx.obj is None:
        ctx.obj = {}


# Register commands
core.add_command(init)
core.add_command(status)
core.add_command(health)
