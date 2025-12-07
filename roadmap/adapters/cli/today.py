"""Today command - daily workflow summary."""

import click

from roadmap.adapters.cli.presentation.daily_summary_presenter import (
    DailySummaryPresenter,
)
from roadmap.adapters.cli.services.daily_summary_service import DailySummaryService
from roadmap.common.console import get_console
from roadmap.infrastructure.logging import verbose_output

console = get_console()


@click.command("today")
@click.option("--verbose", "-v", is_flag=True, help="Show verbose output")
@click.pass_context
@verbose_output
def today(ctx: click.Context, verbose: bool):
    """Show your daily workflow summary for the upcoming milestone.

    Displays your assigned issues for the next upcoming milestone:
    - Current in-progress issues assigned to you
    - Overdue issues
    - High-priority tasks to start
    - Today's completed work

    Only shows issues assigned to you in the upcoming milestone.

    Example:
        roadmap today
    """
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return

    try:
        # Use service to get daily summary data
        service = DailySummaryService(core)
        data = service.get_daily_summary_data()

        # Use presenter to render the data
        DailySummaryPresenter.render(data)

    except ValueError as e:
        console.print(f"❌ {e}", style="bold red")
    except Exception as e:
        console.print(f"❌ Failed to generate daily summary: {e}", style="bold red")
        import traceback

        console.print(traceback.format_exc(), style="dim")
