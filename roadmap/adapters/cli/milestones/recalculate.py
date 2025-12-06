"""Recalculate milestone progress command."""

import click

from roadmap.common.console import get_console

console = get_console()


@click.command("recalculate")
@click.argument("milestone_name", required=False)
@click.option(
    "--method",
    type=click.Choice(["effort_weighted", "count_based"]),
    default="effort_weighted",
    help="Calculation method",
)
@click.pass_context
def recalculate_milestone_progress(
    ctx: click.Context, milestone_name: str, method: str
):
    """Recalculate progress for a milestone or all milestones."""
    core = ctx.obj["core"]

    try:
        # Import the progress engine
        from roadmap.core.services.progress_service import (
            ProgressCalculationEngine,
        )

        # Load all data
        all_issues = core.list_issues()
        all_milestones = core.list_milestones()

        # Create progress engine
        engine = ProgressCalculationEngine(method=method)

        if milestone_name:
            # Recalculate specific milestone
            milestone = core.get_milestone(milestone_name)
            if not milestone:
                console.print(
                    f"❌ Milestone '{milestone_name}' not found", style="bold red"
                )
                return

            old_progress = milestone.calculated_progress
            updated = engine.update_milestone_progress(milestone, all_issues)

            if updated:
                # Save the updated milestone (needs to be implemented properly)
                console.print(
                    f"✅ Updated milestone '{milestone_name}':", style="bold green"
                )
                console.print(
                    f"   Progress: {old_progress or 0:.1f}% → {milestone.calculated_progress:.1f}%"
                )
                console.print(f"   Status: {milestone.status}")
                console.print(f"   Method: {method}")
            else:
                console.print(
                    f"ℹ️  Milestone '{milestone_name}' progress unchanged", style="blue"
                )
                console.print(
                    f"   Current progress: {milestone.calculated_progress or 0:.1f}%"
                )
        else:
            # Recalculate all milestones
            updated_count = 0
            for milestone in all_milestones:
                if engine.update_milestone_progress(milestone, all_issues):
                    updated_count += 1

            console.print("✅ Recalculation complete:", style="bold green")
            console.print(
                f"   {updated_count}/{len(all_milestones)} milestones updated"
            )
            console.print(f"   Method: {method}")

    except Exception as e:
        console.print(f"❌ Failed to recalculate progress: {e}", style="bold red")
