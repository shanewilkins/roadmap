"""
Milestone management CLI commands.
"""

from datetime import datetime

import click
from rich.table import Table

from roadmap.cli.utils import get_console

console = get_console()


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
            console.print(
                "Create one with: roadmap milestone create 'Milestone name'",
                style="dim",
            )
            return

        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Name", style="cyan")
        table.add_column("Description", style="white")
        table.add_column("Due Date", style="yellow", width=12)
        table.add_column("Status", style="green", width=10)
        table.add_column("Progress", style="blue", width=12)
        table.add_column("Estimate", style="green", width=10)

        # Get all issues for calculations
        all_issues = core.list_issues()

        for ms in milestones:
            progress = core.get_milestone_progress(ms.name)
            progress_text = f"{progress['completed']}/{progress['total']}"
            estimate_text = ms.get_estimated_time_display(all_issues)

            # Format due date
            due_date_text = ms.due_date.strftime("%Y-%m-%d") if ms.due_date else "-"

            # Add color coding for overdue milestones
            if ms.due_date:
                now = datetime.now().replace(tzinfo=None)  # Ensure timezone-naive
                ms_due_date = (
                    ms.due_date.replace(tzinfo=None)
                    if ms.due_date.tzinfo
                    else ms.due_date
                )

                if ms_due_date < now and ms.status.value == "open":
                    due_date_text = f"[bold red]{due_date_text}[/bold red]"
                elif (ms_due_date - now).days <= 7 and ms.status.value == "open":
                    due_date_text = f"[yellow]{due_date_text}[/yellow]"

            table.add_row(
                ms.name,
                ms.description or "-",
                due_date_text,
                ms.status.value,
                progress_text,
                estimate_text,
            )

        console.print(table)
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
            console.print(
                f"✅ Assigned issue {issue_id} to milestone '{milestone_name}'",
                style="bold green",
            )
        else:
            console.print(
                f"❌ Failed to assign issue {issue_id} to milestone '{milestone_name}' - issue or milestone not found",
                style="bold red",
            )
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
            if not click.confirm(
                f"Are you sure you want to delete milestone '{milestone_name}'?"
            ):
                console.print("❌ Milestone deletion cancelled.", style="yellow")
                return

        success = core.delete_milestone(milestone_name)
        if success:
            console.print(f"✅ Deleted milestone: {milestone_name}", style="bold green")
        else:
            console.print(f"❌ Milestone not found: {milestone_name}", style="bold red")
    except Exception as e:
        console.print(f"❌ Failed to delete milestone: {e}", style="bold red")


@milestone.command("close")
@click.argument("milestone_name")
@click.option("--force", is_flag=True, help="Skip confirmation prompt")
@click.pass_context
def close_milestone(ctx: click.Context, milestone_name: str, force: bool):
    """Convenience command to mark a milestone as closed."""
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return

    try:
        if not force:
            if not click.confirm(
                f"Are you sure you want to close milestone '{milestone_name}'?"
            ):
                console.print("❌ Milestone close cancelled.", style="yellow")
                return

        from roadmap.domain import MilestoneStatus

        success = core.update_milestone(milestone_name, status=MilestoneStatus.CLOSED)
        if success:
            console.print(f"✅ Closed milestone: {milestone_name}", style="bold green")
        else:
            console.print(f"❌ Milestone not found: {milestone_name}", style="bold red")
    except Exception as e:
        console.print(f"❌ Failed to close milestone: {e}", style="bold red")


@milestone.command("update")
@click.argument("milestone_name")
@click.option("--name", help="Update milestone name")
@click.option("--description", "-d", help="Update milestone description")
@click.option("--due-date", help="Update due date (YYYY-MM-DD format)")
@click.option(
    "--status",
    type=click.Choice(["open", "closed"]),
    help="Set milestone status (open|closed)",
)
@click.option("--clear-due-date", is_flag=True, help="Clear the due date")
@click.pass_context
def update_milestone(
    ctx: click.Context,
    milestone_name: str,
    name: str,
    description: str,
    due_date: str,
    status: str,
    clear_due_date: bool,
):
    """Update an existing milestone."""
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return

    try:
        # Check if milestone exists
        milestone = core.get_milestone(milestone_name)
        if not milestone:
            console.print(f"❌ Milestone not found: {milestone_name}", style="bold red")
            return

        # Build update dict
        updates = {}
        if name:
            updates["name"] = name
        if description:
            updates["description"] = description
        if clear_due_date:
            updates["due_date"] = None
        elif due_date:
            if due_date.lower() == "clear":
                updates["due_date"] = None
            else:
                try:
                    parsed_due_date = datetime.strptime(due_date, "%Y-%m-%d")
                    updates["due_date"] = parsed_due_date
                except ValueError:
                    console.print(
                        "❌ Invalid due date format. Use YYYY-MM-DD (e.g., 2024-12-31)",
                        style="bold red",
                    )
                    return

        if status:
            # Map CLI status string to MilestoneStatus enum
            try:
                from roadmap.domain import MilestoneStatus

                # MilestoneStatus expects 'open' or 'closed' values
                updates["status"] = MilestoneStatus(status)
            except Exception:
                # Fallback to raw string if mapping fails
                updates["status"] = status

        if not updates:
            console.print("❌ No updates specified", style="bold red")
            return

        # Update the milestone
        success = core.update_milestone(milestone_name, **updates)

        if not success:
            console.print(
                f"❌ Failed to update milestone: {milestone_name}", style="bold red"
            )
            return

        # Re-fetch the milestone to show updated values
        updated_milestone = core.get_milestone(updates.get("name", milestone_name))

        console.print(
            f"✅ Updated milestone: {updated_milestone.name}", style="bold green"
        )
        console.print(f"   Description: {updated_milestone.description}", style="cyan")
        if updated_milestone.due_date:
            console.print(
                f"   Due Date: {updated_milestone.due_date.strftime('%Y-%m-%d')}",
                style="yellow",
            )
        elif clear_due_date:
            console.print("   Due Date: Cleared", style="dim")

    except Exception as e:
        console.print(f"❌ Failed to update milestone: {e}", style="bold red")


@milestone.command("recalculate")
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
        from roadmap.application.services.progress_service import (
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


@milestone.command("kanban")
@click.argument("milestone_name")
@click.option("--compact", is_flag=True, help="Compact view with less spacing")
@click.option("--no-color", is_flag=True, help="Disable color coding")
@click.pass_context
def milestone_kanban(
    ctx: click.Context, milestone_name: str, compact: bool, no_color: bool
):
    """Display milestone issues in a kanban board layout."""
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return

    try:
        # Get milestone
        milestone = core.get_milestone(milestone_name)
        if not milestone:
            console.print(
                f"❌ Milestone '{milestone_name}' not found", style="bold red"
            )
            return

        # Get all issues for this milestone
        all_issues = core.list_issues()
        milestone_issues = [
            issue for issue in all_issues if issue.milestone == milestone_name
        ]

        if not milestone_issues:
            console.print(
                f"📋 No issues found for milestone '{milestone_name}'", style="yellow"
            )
            console.print(
                "Create issues with: roadmap issue create 'Issue title' --milestone <milestone>",
                style="dim",
            )
            return

        # Organize issues into kanban columns
        from datetime import datetime

        now = datetime.now()

        overdue = []
        blocked = []
        in_progress = []
        not_started = []
        done = []

        for issue in milestone_issues:
            if issue.status.value == "done":
                done.append(issue)
            elif issue.status.value == "blocked":
                blocked.append(issue)
            elif issue.status.value == "in-progress":
                in_progress.append(issue)
            elif (
                issue.due_date and issue.due_date < now and issue.status.value != "done"
            ):
                overdue.append(issue)
            else:
                not_started.append(issue)

        # Display the kanban board
        console.print(f"\n🎯 Kanban Board: {milestone.name}", style="bold blue")
        console.print(
            f"📅 Due: {milestone.due_date.strftime('%Y-%m-%d') if milestone.due_date else 'No due date'}"
        )
        console.print(
            f"📊 Progress: {len(done)}/{len(milestone_issues)} issues completed\n"
        )

        # Create columns
        columns = [
            ("🚨 Overdue", overdue, "bold red" if not no_color else "white"),
            ("🚫 Blocked", blocked, "bold yellow" if not no_color else "white"),
            ("🔄 In Progress", in_progress, "bold blue" if not no_color else "white"),
            ("⏸️  Not Started", not_started, "dim white" if not no_color else "white"),
            ("✅ Done", done, "bold green" if not no_color else "white"),
        ]

        # Calculate column width based on terminal size
        try:
            import shutil

            terminal_width = shutil.get_terminal_size().columns
            col_width = max(
                30, (terminal_width - 5) // len(columns)
            )  # More space per column
        except:
            col_width = 35

        # Print column headers
        header_line = ""
        separator_line = ""
        for title, issues, _style in columns:
            header_line += f"{title:<{col_width}}"
            separator_line += "─" * col_width

        console.print(header_line, style="bold")
        console.print(separator_line, style="dim")

        # Print issues in columns
        max_issues = max(len(col[1]) for col in columns) if columns else 0

        for row in range(max_issues):
            row_line = ""
            for title, issues, _style in columns:
                if row < len(issues):
                    issue = issues[row]
                    # Format issue card
                    title_space = col_width - 12  # Space for ID and padding
                    display_title = issue.title
                    if len(display_title) > title_space:
                        display_title = display_title[: title_space - 3] + "..."
                    card_text = f"#{issue.id[:8]} {display_title}"
                    row_line += f"{card_text:<{col_width}}"
                else:
                    row_line += " " * col_width

            console.print(row_line)

            if not compact:
                # Add spacing between cards
                if row < max_issues - 1:
                    console.print("")

        # Print summary
        console.print("\n📈 Summary:")
        console.print(
            f"   Overdue: {len(overdue)} | Blocked: {len(blocked)} | In Progress: {len(in_progress)}"
        )
        console.print(f"   Not Started: {len(not_started)} | Done: {len(done)}")

    except Exception as e:
        console.print(f"❌ Failed to display kanban board: {e}", style="bold red")
