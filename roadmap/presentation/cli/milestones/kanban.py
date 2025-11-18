"""Milestone kanban board command."""

import click

from roadmap.cli.utils import get_console

console = get_console()


@click.command("kanban")
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
        except Exception:
            col_width = 35

        # Print column headers
        header_line = ""
        separator_line = ""
        for title, _issues, _style in columns:
            header_line += f"{title:<{col_width}}"
            separator_line += "─" * col_width

        console.print(header_line, style="bold")
        console.print(separator_line, style="dim")

        # Print issues in columns
        max_issues = max(len(col[1]) for col in columns) if columns else 0

        for row in range(max_issues):
            row_line = ""
            for _title, issues, _style in columns:
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
