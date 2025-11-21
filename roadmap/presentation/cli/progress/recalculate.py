"""Recalculate milestone and project progress commands."""

import os

import click
from rich.console import Console
from rich.progress import Progress

from roadmap.application.services.progress_service import ProgressCalculationEngine

# Initialize console for rich output with test mode detection
is_testing = "PYTEST_CURRENT_TEST" in os.environ or os.environ.get("NO_COLOR") == "1"
console = Console(force_terminal=not is_testing, no_color=is_testing)


@click.group()
def recalculate_progress():
    """Recalculate milestone and project progress."""
    pass


@recalculate_progress.command("milestone")
@click.argument("milestone_name")
@click.option(
    "--method",
    type=click.Choice(["effort_weighted", "count_based"]),
    default="effort_weighted",
    help="Calculation method",
)
@click.pass_context
def recalculate_milestone(ctx: click.Context, milestone_name: str, method: str):
    """Recalculate progress for a specific milestone."""
    core = ctx.obj["core"]

    try:
        # Load all data
        all_issues = core.list_issues()
        all_milestones = core.list_milestones()

        # Find the milestone
        milestone = None
        for m in all_milestones:
            if m.name == milestone_name:
                milestone = m
                break

        if not milestone:
            console.print(
                f"❌ Milestone '{milestone_name}' not found", style="bold red"
            )
            return

        # Create progress engine and update
        engine = ProgressCalculationEngine(method=method)
        old_progress = milestone.calculated_progress

        updated = engine.update_milestone_progress(milestone, all_issues)

        if updated:
            # Save the updated milestone
            from roadmap.infrastructure.persistence.parser import MilestoneParser

            milestone_file = core.milestones_dir / f"{milestone.name}.md"
            MilestoneParser.save_milestone_file(milestone, milestone_file)

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

    except Exception as e:
        console.print(
            f"❌ Failed to recalculate milestone progress: {e}", style="bold red"
        )


@recalculate_progress.command("project")
@click.argument("project_id")
@click.option(
    "--method",
    type=click.Choice(["effort_weighted", "count_based"]),
    default="effort_weighted",
    help="Calculation method",
)
@click.pass_context
def recalculate_project(ctx: click.Context, project_id: str, method: str):
    """Recalculate progress for a specific project."""
    core = ctx.obj["core"]

    try:
        # Load all data
        all_issues = core.list_issues()
        all_milestones = core.list_milestones()
        all_projects = core.list_projects()  # This method needs to be implemented

        # Find the project
        project = None
        for p in all_projects:
            if p.id.startswith(project_id):
                project = p
                break

        if not project:
            console.print(f"❌ Project '{project_id}' not found", style="bold red")
            return

        # Create progress engine and update
        engine = ProgressCalculationEngine(method=method)
        old_progress = project.calculated_progress

        updated = engine.update_project_progress(project, all_milestones, all_issues)

        if updated:
            # Save the updated project (this method needs to be implemented)
            core.save_project(project)

            console.print(f"✅ Updated project '{project.name}':", style="bold green")
            console.print(
                f"   Progress: {old_progress or 0:.1f}% → {project.calculated_progress:.1f}%"
            )
            console.print(f"   Status: {project.status}")
            console.print(f"   Risk Level: {project.risk_level}")
            if project.projected_end_date:
                console.print(
                    f"   Projected End: {project.projected_end_date.strftime('%Y-%m-%d')}"
                )
            if project.schedule_variance:
                variance_str = f"{abs(project.schedule_variance)} days {'ahead' if project.schedule_variance < 0 else 'behind'}"
                console.print(f"   Schedule Variance: {variance_str}")
        else:
            console.print(
                f"ℹ️  Project '{project.name}' progress unchanged", style="blue"
            )
            console.print(
                f"   Current progress: {project.calculated_progress or 0:.1f}%"
            )

    except Exception as e:
        console.print(
            f"❌ Failed to recalculate project progress: {e}", style="bold red"
        )


@recalculate_progress.command("all")
@click.option(
    "--method",
    type=click.Choice(["effort_weighted", "count_based"]),
    default="effort_weighted",
    help="Calculation method",
)
@click.pass_context
def recalculate_all(ctx: click.Context, method: str):
    """Recalculate progress for all milestones and projects."""
    core = ctx.obj["core"]

    try:
        # Load all data
        all_issues = core.list_issues()
        all_milestones = core.list_milestones()
        all_projects = core.list_projects()

        # Create progress engine
        engine = ProgressCalculationEngine(method=method)

        console.print("🔄 Recalculating all progress...", style="bold blue")

        with Progress() as progress:
            task = progress.add_task(
                "Updating progress...", total=len(all_milestones) + len(all_projects)
            )

            # Update milestones
            updated_milestones = 0
            for milestone in all_milestones:
                if engine.update_milestone_progress(milestone, all_issues):
                    from roadmap.infrastructure.persistence.parser import (
                        MilestoneParser,
                    )

                    milestone_file = core.milestones_dir / f"{milestone.name}.md"
                    MilestoneParser.save_milestone_file(milestone, milestone_file)
                    updated_milestones += 1
                progress.advance(task)

            # Update projects
            updated_projects = 0
            for project in all_projects:
                if engine.update_project_progress(project, all_milestones, all_issues):
                    from roadmap.infrastructure.persistence.parser import ProjectParser

                    project_file = core.projects_dir / f"{project.id}.md"
                    ProjectParser.save_project_file(project, project_file)
                    updated_projects += 1
                progress.advance(task)

        console.print("✅ Recalculation complete:", style="bold green")
        console.print(
            f"   {updated_milestones}/{len(all_milestones)} milestones updated"
        )
        console.print(f"   {updated_projects}/{len(all_projects)} projects updated")
        console.print(f"   Method: {method}")

    except Exception as e:
        console.print(f"❌ Failed to recalculate progress: {e}", style="bold red")
