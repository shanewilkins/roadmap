"""Canonical daily planning view."""

import os

import click

from roadmap.adapters.cli.cli_command_helpers import require_initialized
from roadmap.adapters.cli.planning_resolution import invoke
from roadmap.adapters.cli.presentation.daily_summary_presenter import (
    DailySummaryPresenter,
)
from roadmap.common.logging import verbose_output


@click.command("today")
@click.option("--verbose", "-v", is_flag=True, help="Show verbose output")
@click.pass_context
@require_initialized
@verbose_output
def today(ctx: click.Context, verbose: bool = False) -> None:  # noqa: ARG001
    """Show assigned work for the next open milestone."""
    core = ctx.obj["core"]
    current_user = os.getenv("ROADMAP_USER") or core.team.get_current_user()
    if not current_user:
        raise click.ClickException(
            "No user configured. Initialize Roadmap or set ROADMAP_USER."
        )
    summary = invoke(lambda: core.planning.daily_summary(current_user))
    DailySummaryPresenter().render(summary)
