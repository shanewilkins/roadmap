"""Milestone kanban board command."""

import click

from roadmap.adapters.cli.cli_command_helpers import require_initialized
from roadmap.common.console import get_console
from roadmap.common.formatters import KanbanLayout, KanbanOrganizer

console = get_console()


@click.command("kanban")
@click.argument("milestone_name")
@click.option("--compact", is_flag=True, help="Compact view with less spacing")
@click.option("--no-color", is_flag=True, help="Disable color coding")
@click.pass_context
@require_initialized
def milestone_kanban(
    ctx: click.Context, milestone_name: str, compact: bool, no_color: bool
):
    """Display milestone issues in a kanban board layout."""
    core = ctx.obj["core"]

    try:
        # Get milestone
        milestone = core.milestones.get(milestone_name)
        if not milestone:
            console.print(
                f"❌ Milestone '{milestone_name}' not found", style="bold red"
            )
            return

        # Get all issues for this milestone
        all_issues = core.issues.list()
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

        # Organize into categories
        categories = KanbanOrganizer.categorize_issues(milestone_issues)
        columns = KanbanOrganizer.create_column_definitions(categories, no_color)

        # Display kanban board
        _display_header(milestone, milestone_issues)
        _display_board(
            columns,
            compact,
            col_width=KanbanLayout.calculate_column_width(len(columns)),
        )
        _display_summary(categories)

    except Exception as e:
        console.print(f"❌ Failed to display kanban board: {e}", style="bold red")


def _display_header(milestone, milestone_issues):
    """Display board header with milestone info."""
    console.print(f"\n🎯 Kanban Board: {milestone.name}", style="bold blue")
    console.print(
        f"📅 Due: {milestone.due_date.strftime('%Y-%m-%d') if milestone.due_date else 'No due date'}"
    )
    done_count = sum(1 for i in milestone_issues if i.status.value == "closed")
    console.print(
        f"📊 Progress: {done_count}/{len(milestone_issues)} issues completed\n"
    )


def _display_board(columns, compact: bool, col_width: int):
    """Display the kanban board columns."""
    # Print column headers
    header_line = ""
    separator_line = ""
    for title, _issues, _style in columns:
        header_line += f"{title:<{col_width}}"
        separator_line += "─" * col_width

    console.print(header_line, style="bold")
    console.print(separator_line, style="dim")

    # Print rows
    max_issues = max(len(issues) for _, issues, _ in columns) if columns else 0
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


def _display_summary(categories: dict):
    """Display summary statistics."""
    console.print("\n📈 Summary:")
    console.print(
        f"   Overdue: {len(categories['overdue'])} | Blocked: {len(categories['blocked'])} | In Progress: {len(categories['in_progress'])}"
    )
    console.print(
        f"   Not Started: {len(categories['not_started'])} | Done: {len(categories['closed'])}"
    )
