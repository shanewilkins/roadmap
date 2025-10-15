"""
Milestone management CLI commands.
"""

import click
import os
from datetime import datetime
from roadmap.core import RoadmapCore
from roadmap.cli.utils import get_console

console = get_console()

import click
from rich.console import Console
from datetime import datetime

console = Console()

@click.group()
def milestone():
    """Manage milestones."""
    pass

@milestone.command("create")
@click.argument("name")
@click.option("--description", "-d", default="", help="Milestone description")
@click.option("--due-date", help="Due date for milestone (YYYY-MM-DD format)")
@click.pass_context
def create_milestone(ctx: click.Context, name: str, description: str, due_date: str):
    """Create a new milestone."""
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return

    # Parse due date if provided
    parsed_due_date = None
    if due_date:
        try:
            parsed_due_date = datetime.strptime(due_date, "%Y-%m-%d")
        except ValueError:
            console.print(
                "❌ Invalid due date format. Use YYYY-MM-DD (e.g., 2024-12-31)",
                style="bold red",
            )
            return

    try:
        milestone = core.create_milestone(
            name=name, description=description, due_date=parsed_due_date
        )
        console.print(f"✅ Created milestone: {milestone.name}", style="bold green")
        console.print(f"   Description: {milestone.description}", style="cyan")
        if milestone.due_date:
            console.print(
                f"   Due Date: {milestone.due_date.strftime('%Y-%m-%d')}",
                style="yellow",
            )
        console.print(f"   File: .roadmap/milestones/{milestone.filename}", style="dim")
    except Exception as e:
        console.print(f"❌ Failed to create milestone: {e}", style="bold red")


@milestone.command("list")
@click.pass_context
def list_milestones(ctx: click.Context):
    """List all milestones."""
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return

    try:
        milestones = core.list_milestones()
        
        if not milestones:
            console.print("📋 No milestones found.", style="yellow")
            return

        console.print(f"📋 {len(milestones)} milestone{'s' if len(milestones) != 1 else ''}", style="bold cyan")
        for milestone in milestones:
            console.print(f"  {milestone.name}: {milestone.description}")

    except Exception as e:
        console.print(f"❌ Failed to list milestones: {e}", style="bold red")


@milestone.command("assign")
@click.argument("issue_id")
@click.argument("milestone_name")
@click.pass_context
def assign_milestone(ctx: click.Context, issue_id: str, milestone_name: str):
    """Assign an issue to a milestone."""
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return

    try:
        success = core.assign_issue_to_milestone(issue_id, milestone_name)
        if success:
            console.print(f"✅ Assigned issue {issue_id} to milestone '{milestone_name}'", style="bold green")
        else:
            console.print(f"❌ Failed to assign issue {issue_id} to milestone '{milestone_name}' - issue or milestone not found", style="bold red")
    except Exception as e:
        console.print(f"❌ Failed to assign issue: {e}", style="bold red")


@milestone.command("delete")
@click.argument("milestone_name")
@click.option("--force", is_flag=True, help="Skip confirmation prompt")
@click.pass_context
def delete_milestone(ctx: click.Context, milestone_name: str, force: bool):
    """Delete a milestone."""
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return

    try:
        if not force:
            if not click.confirm(f"Are you sure you want to delete milestone '{milestone_name}'?"):
                console.print("❌ Milestone deletion cancelled.", style="yellow")
                return
        
        success = core.delete_milestone(milestone_name)
        if success:
            console.print(f"✅ Deleted milestone: {milestone_name}", style="bold green")
        else:
            console.print(f"❌ Milestone not found: {milestone_name}", style="bold red")
    except Exception as e:
        console.print(f"❌ Failed to delete milestone: {e}", style="bold red")

@milestone.command("update")
@click.argument("milestone_name")
@click.option("--name", help="Update milestone name")
@click.option("--description", "-d", help="Update milestone description")
@click.option("--due-date", help="Update due date (YYYY-MM-DD format)")
@click.option("--clear-due-date", is_flag=True, help="Clear the due date")
@click.pass_context
def update_milestone(ctx: click.Context, milestone_name: str, name: str, description: str, due_date: str, clear_due_date: bool):
    """Update an existing milestone."""
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        raise click.Abort()

    try:
        # Check if milestone exists
        milestone = core.get_milestone(milestone_name)
        if not milestone:
            console.print(f"❌ Milestone not found: {milestone_name}", style="bold red")
            raise click.Abort()

        # Build update dict
        updates = {}
        if name:
            updates["name"] = name
        if description:
            updates["description"] = description
        if clear_due_date:
            updates["due_date"] = None
        elif due_date:
            try:
                parsed_due_date = datetime.strptime(due_date, "%Y-%m-%d")
                updates["due_date"] = parsed_due_date
            except ValueError:
                console.print(
                    "❌ Invalid due date format. Use YYYY-MM-DD (e.g., 2024-12-31)",
                    style="bold red",
                )
                raise click.Abort()

        if not updates:
            console.print("❌ No updates specified", style="bold red")
            raise click.Abort()

        # Update the milestone
        updated_milestone = core.update_milestone(milestone_name, **updates)
        
        console.print(f"✅ Updated milestone: {updated_milestone.name}", style="bold green")
        console.print(f"   Description: {updated_milestone.description}", style="cyan")
        if updated_milestone.due_date:
            console.print(
                f"   Due Date: {updated_milestone.due_date.strftime('%Y-%m-%d')}",
                style="yellow",
            )
        elif clear_due_date:
            console.print("   Due Date: Cleared", style="dim")
            
    except click.Abort:
        raise
    except Exception as e:
        console.print(f"❌ Failed to update milestone: {e}", style="bold red")
        raise click.Abort()