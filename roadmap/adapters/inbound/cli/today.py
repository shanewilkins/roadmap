"""Canonical daily planning view."""

import click

from roadmap.adapters.inbound.cli.cli_command_helpers import require_initialized
from roadmap.adapters.inbound.cli.daily_summary import DailySummaryPresenter
from roadmap.adapters.inbound.cli.instrumentation import verbose_output
from roadmap.adapters.inbound.cli.planning_resolution import invoke


@click.command("today")
@click.option("--verbose", "-v", is_flag=True, help="Show verbose output")
@click.pass_context
@require_initialized
@verbose_output
def today(ctx: click.Context, verbose: bool = False) -> None:  # noqa: ARG001
    """Show assigned work for the next open milestone."""
    core = ctx.obj["core"]
    current_user = core.current_identity.current_identity()
    if not current_user:
        raise click.ClickException(
            "No descriptive identity is configured. Set user identity.name or Git user.name."
        )
    summary = invoke(lambda: core.planning.daily_summary(current_user))
    DailySummaryPresenter().render(summary)
