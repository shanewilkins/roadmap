"""
Issue management CLI commands.
"""

import os
import subprocess

import click
from rich.table import Table
from rich.text import Text

from roadmap.cli.utils import get_console
from roadmap.error_handling import (
    ErrorHandler,
    ValidationError,
)
from roadmap.models import IssueType, Priority, Status

console = get_console()


def _safe_create_branch(git, issue, checkout=True, force=False):
    """Call create_branch_for_issue with best-effort compatibility for older signatures.

    Tries the newest signature (checkout, force) first, falls back to older ones.
    """
    try:
        return git.create_branch_for_issue(issue, checkout=checkout, force=force)
    except TypeError:
        # Try without force
        try:
            return git.create_branch_for_issue(issue, checkout=checkout)
        except TypeError:
            # Try fully positional (issue only)
            try:
                return git.create_branch_for_issue(issue)
            except Exception:
                return False


@click.group()
def issue():
    """Manage issues."""
    pass


# Basic issue commands - full implementation would be extracted from main CLI
@issue.command("list")
@click.option("--milestone", "-m", help="Filter by milestone")
@click.option("--backlog", is_flag=True, help="Show only backlog issues (no milestone)")
@click.option(
    "--unassigned",
    is_flag=True,
    help="Show only unassigned issues (alias for --backlog)",
)
@click.option("--open", is_flag=True, help="Show only open issues (not done)")
@click.option("--blocked", is_flag=True, help="Show only blocked issues")
@click.option(
    "--next-milestone", is_flag=True, help="Show issues for the next upcoming milestone"
)
@click.option("--assignee", "-a", help="Filter by assignee")
@click.option("--my-issues", is_flag=True, help="Show only issues assigned to me")
@click.option(
    "--status",
    "-s",
    type=click.Choice(["todo", "in-progress", "blocked", "review", "done"]),
    help="Filter by status",
)
@click.option(
    "--priority",
    "-p",
    type=click.Choice(["critical", "high", "medium", "low"]),
    help="Filter by priority",
)
@click.pass_context
def list_issues(
    ctx: click.Context,
    milestone: str,
    backlog: bool,
    unassigned: bool,
    open: bool,
    blocked: bool,
    next_milestone: bool,
    assignee: str,
    my_issues: bool,
    status: str,
    priority: str,
):
    """List all issues with various filtering options."""
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return

    try:
        # Check for conflicting filters
        assignee_filters = [assignee is not None, my_issues]
        if sum(bool(f) for f in assignee_filters) > 1:
            console.print(
                "❌ Cannot combine --assignee and --my-issues filters", style="bold red"
            )
            return

        exclusive_filters = [backlog, unassigned, next_milestone, milestone is not None]
        if sum(bool(f) for f in exclusive_filters) > 1:
            console.print(
                "❌ Cannot combine --backlog, --unassigned, --next-milestone, and --milestone filters",
                style="bold red",
            )
            return

        # Handle special assignee filters first
        if my_issues:
            issues = core.get_my_issues()
            filter_description = "my"
        elif assignee:
            issues = core.get_assigned_issues(assignee)
            filter_description = f"assigned to {assignee}"
        # Get base set of issues
        elif backlog or unassigned:
            # Show only backlog/unassigned issues
            issues = core.get_backlog_issues()
            filter_description = "backlog"
        elif next_milestone:
            # Show issues for next milestone
            next_ms = core.get_next_milestone()
            if not next_ms:
                console.print(
                    "📋 No upcoming milestones with due dates found.", style="yellow"
                )
                console.print(
                    "Create one with: roadmap milestone create 'Milestone name' --due-date YYYY-MM-DD",
                    style="dim",
                )
                return
            issues = core.get_milestone_issues(next_ms.name)
            filter_description = f"next milestone ({next_ms.name})"
        elif milestone:
            # Show issues for specific milestone
            issues = core.get_milestone_issues(milestone)
            filter_description = f"milestone '{milestone}'"
        else:
            # Show all issues
            issues = core.list_issues()
            filter_description = "all"

        # Apply additional filters
        if open:
            issues = [i for i in issues if i.status != Status.DONE]
            filter_description += " open"

        if blocked:
            issues = [i for i in issues if i.status == Status.BLOCKED]
            filter_description += " blocked"

        if status:
            issues = [i for i in issues if i.status == Status(status)]
            filter_description += f" {status}"

        if priority:
            issues = [i for i in issues if i.priority == Priority(priority)]
            filter_description += f" {priority} priority"

        # Show results
        if not issues:
            console.print(f"📋 No {filter_description} issues found.", style="yellow")
            console.print(
                "Create one with: roadmap issue create 'Issue title'", style="dim"
            )
            return

        # Display header with filter info
        header_text = f"📋 {len(issues)} {filter_description} issue{'s' if len(issues) != 1 else ''}"
        console.print(header_text, style="bold cyan")
        console.print()

        # Rich table display
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("ID", style="cyan", width=8)
        table.add_column("Title", style="white", width=25, no_wrap=False)
        table.add_column("Priority", style="yellow", width=10)
        table.add_column("Status", style="green", width=12)
        table.add_column("Progress", style="blue", width=10)
        table.add_column("Assignee", style="magenta", width=12)
        table.add_column("Estimate", style="green", width=10)
        table.add_column("Milestone", style="blue", width=15)

        for issue in issues:
            priority_style = {
                Priority.CRITICAL: "bold red",
                Priority.HIGH: "red",
                Priority.MEDIUM: "yellow",
                Priority.LOW: "dim",
            }.get(issue.priority, "white")

            status_style = {
                Status.TODO: "white",
                Status.IN_PROGRESS: "yellow",
                Status.BLOCKED: "red",
                Status.REVIEW: "blue",
                Status.DONE: "green",
            }.get(issue.status, "white")

            table.add_row(
                issue.id,
                issue.title,
                Text(issue.priority.value, style=priority_style),
                Text(issue.status.value, style=status_style),
                Text(
                    issue.progress_display,
                    style="blue" if issue.progress_percentage else "dim",
                ),
                Text(
                    issue.assignee or "Unassigned",
                    style="magenta" if issue.assignee else "dim",
                ),
                Text(
                    issue.estimated_time_display,
                    style="green" if issue.estimated_hours else "dim",
                ),
                Text(issue.milestone_name, style="dim" if issue.is_backlog else "blue"),
            )

        console.print(table)

        # Show time aggregation for assignee filters
        if assignee or my_issues:
            assignee_name = assignee if assignee else "you"

            # Calculate totals
            total_hours = sum(issue.estimated_hours or 0 for issue in issues)
            remaining_hours = sum(
                issue.estimated_hours or 0
                for issue in issues
                if issue.status.value != "done"
            )

            if total_hours > 0:
                # Format total time display
                if total_hours < 1:
                    total_display = f"{total_hours * 60:.0f}m"
                elif total_hours <= 24:
                    total_display = f"{total_hours:.1f}h"
                else:
                    total_display = f"{total_hours / 8:.1f}d"

                console.print()
                console.print(
                    f"Total estimated time for {assignee_name}: {total_display}",
                    style="bold blue",
                )

                # Show status breakdown
                status_counts = {}
                for issue in issues:
                    status = issue.status.value
                    if status not in status_counts:
                        status_counts[status] = {"count": 0, "hours": 0}
                    status_counts[status]["count"] += 1
                    status_counts[status]["hours"] += issue.estimated_hours or 0

                console.print("Workload breakdown:", style="bold")
                for status, data in status_counts.items():
                    if data["count"] > 0:
                        if data["hours"] > 0:
                            if data["hours"] < 1:
                                time_display = f"{data['hours'] * 60:.0f}m"
                            elif data["hours"] <= 24:
                                time_display = f"{data['hours']:.1f}h"
                            else:
                                time_display = f"{data['hours'] / 8:.1f}d"
                            console.print(
                                f"  {status}: {data['count']} issues ({time_display})"
                            )
                        else:
                            console.print(f"  {status}: {data['count']} issues")

    except Exception as e:
        error_handler = ErrorHandler()
        error_handler.handle_error(
            ValidationError(
                "Failed to list issues", context={"command": "list"}, cause=e
            ),
            exit_on_critical=False,
        )


@issue.command("create")
@click.argument("title")
@click.option(
    "--priority",
    "-p",
    type=click.Choice(["critical", "high", "medium", "low"]),
    default="medium",
    help="Issue priority",
)
@click.option(
    "--type",
    "-t",
    "issue_type",
    type=click.Choice(["feature", "bug", "other"]),
    default="other",
    help="Issue type",
)
@click.option("--milestone", "-m", help="Assign to milestone")
@click.option("--assignee", "-a", help="Assign to team member")
@click.option("--labels", "-l", multiple=True, help="Add labels")
@click.option(
    "--estimate", "-e", type=float, help="Estimated time to complete (in hours)"
)
@click.option("--depends-on", multiple=True, help="Issue IDs this depends on")
@click.option("--blocks", multiple=True, help="Issue IDs this blocks")
@click.option("--git-branch", is_flag=True, help="Create a Git branch for this issue")
@click.option(
    "--checkout/--no-checkout",
    default=True,
    help="Checkout the branch after creation (with --git-branch)",
)
@click.option("--branch-name", default=None, help="Override suggested branch name")
@click.option(
    "--force", is_flag=True, help="Force branch creation even if working tree is dirty"
)
@click.pass_context
def create_issue(
    ctx: click.Context,
    title: str,
    priority: str,
    issue_type: str,
    milestone: str,
    assignee: str,
    labels: tuple,
    estimate: float,
    depends_on: tuple,
    blocks: tuple,
    git_branch: bool,
    checkout: bool,
    branch_name: str,
    force: bool,
):
    """Create a new issue."""
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return

    try:
        # Auto-detect assignee from Git if not provided
        if not assignee:
            git_user = core.get_current_user_from_git()
            if git_user:
                assignee = git_user
                console.print(
                    f"🔍 Auto-detected assignee from Git: {assignee}", style="dim"
                )

        # Validate assignee if provided
        canonical_assignee = assignee
        if assignee:
            is_valid, result = core.validate_assignee(assignee)
            if not is_valid:
                console.print(f"❌ Invalid assignee: {result}", style="bold red")
                raise click.Abort()
            elif result and "Warning:" in result:
                console.print(f"⚠️  {result}", style="bold yellow")
                canonical_assignee = assignee  # Keep original if warning
            else:
                canonical_assignee = core.get_canonical_assignee(assignee)
                if canonical_assignee != assignee:
                    console.print(
                        f"🔄 Resolved '{assignee}' to '{canonical_assignee}'",
                        style="dim",
                    )

        issue = core.create_issue(
            title=title,
            priority=Priority(priority),
            issue_type=IssueType(issue_type),
            milestone=milestone,
            assignee=canonical_assignee,
            labels=list(labels),
            estimated_hours=estimate,
            depends_on=list(depends_on),
            blocks=list(blocks),
        )
        console.print(f"✅ Created issue: {issue.title}", style="bold green")
        console.print(f"   ID: {issue.id}", style="cyan")
        console.print(f"   Type: {issue.issue_type.value.title()}", style="blue")
        console.print(f"   Priority: {issue.priority.value}", style="yellow")
        if milestone:
            console.print(f"   Milestone: {milestone}", style="blue")
        if assignee:
            console.print(f"   Assignee: {assignee}", style="magenta")
        if estimate:
            console.print(
                f"   Estimated: {issue.estimated_time_display}", style="green"
            )
        if depends_on:
            console.print(f"   Depends on: {', '.join(depends_on)}", style="orange1")
        if blocks:
            console.print(f"   Blocks: {', '.join(blocks)}", style="red1")

        # Create Git branch if requested
        if git_branch:
            if hasattr(core, "git") and core.git.is_git_repository():
                # Determine resolved branch name early so fallbacks use the same name
                resolved_branch_name = branch_name or core.git.suggest_branch_name(
                    issue
                )
                branch_success = _safe_create_branch(
                    core.git, issue, checkout=checkout, force=force
                )
                if branch_success:
                    console.print(
                        f"🌿 Created Git branch: {resolved_branch_name}", style="green"
                    )
                    if checkout:
                        console.print(
                            f"✅ Checked out branch: {resolved_branch_name}",
                            style="green",
                        )
                else:
                    # Determine likely reason for failure
                    status_output = (
                        core.git._run_git_command(["status", "--porcelain"]) or ""
                    )
                    if status_output.strip():
                        console.print(
                            "⚠️  Working tree has uncommitted changes — branch creation skipped. Use --force to override.",
                            style="yellow",
                        )
                    else:
                        # Try fallback direct git command
                        fallback = core.git._run_git_command(
                            ["checkout", "-b", resolved_branch_name]
                        )
                        if fallback is not None:
                            console.print(
                                f"🌿 Created Git branch: {resolved_branch_name}",
                                style="green",
                            )
                            if checkout:
                                console.print(
                                    f"✅ Checked out branch: {resolved_branch_name}",
                                    style="green",
                                )
                        else:
                            # Final check: maybe branch exists already; verify via rev-parse
                            exists = None
                            try:
                                if hasattr(core, "git"):
                                    exists = core.git._run_git_command(
                                        ["rev-parse", "--verify", resolved_branch_name]
                                    )
                            except Exception:
                                exists = None

                            if exists:
                                console.print(
                                    f"🌿 Created Git branch: {resolved_branch_name}",
                                    style="green",
                                )
                                if checkout:
                                    console.print(
                                        f"✅ Checked out branch: {resolved_branch_name}",
                                        style="green",
                                    )
                            else:
                                # As a last resort try running git directly in the repo root
                                try:
                                    subprocess.run(
                                        [
                                            "git",
                                            "checkout",
                                            "-b",
                                            resolved_branch_name,
                                        ],
                                        cwd=getattr(core, "root_path", None)
                                        or os.getcwd(),
                                        check=True,
                                        capture_output=True,
                                        text=True,
                                    )
                                    console.print(
                                        f"🌿 Created Git branch: {resolved_branch_name}",
                                        style="green",
                                    )
                                    if checkout:
                                        console.print(
                                            f"✅ Checked out branch: {resolved_branch_name}",
                                            style="green",
                                        )
                                except Exception:
                                    console.print(
                                        "⚠️  Failed to create or checkout branch. See git for details.",
                                        style="yellow",
                                    )
            else:
                console.print(
                    "⚠️  Not in a Git repository, skipping branch creation",
                    style="yellow",
                )

        console.print(f"   File: .roadmap/issues/{issue.filename}", style="dim")
    except click.Abort:
        # Re-raise click.Abort to maintain proper exit code
        raise
    except Exception as e:
        error_handler = ErrorHandler()
        error_handler.handle_error(
            ValidationError(
                "Failed to create issue",
                context={"command": "create", "title": title},
                cause=e,
            ),
            exit_on_critical=False,
        )


@issue.command("update")
@click.argument("issue_id")
@click.option("--title", help="Update issue title")
@click.option(
    "--priority",
    "-p",
    type=click.Choice(["critical", "high", "medium", "low"]),
    help="Update priority",
)
@click.option(
    "--status",
    "-s",
    type=click.Choice(["todo", "in-progress", "blocked", "review", "done"]),
    help="Update status",
)
@click.option("--assignee", "-a", help="Update assignee")
@click.option("--milestone", "-m", help="Update milestone")
@click.option("--description", "-d", help="Update description")
@click.option("--estimate", "-e", type=float, help="Update estimated time (in hours)")
@click.option("--reason", "-r", help="Reason for the update")
@click.pass_context
def update_issue(
    ctx: click.Context,
    issue_id: str,
    title: str,
    priority: str,
    status: str,
    assignee: str,
    milestone: str,
    description: str,
    estimate: float,
    reason: str,
):
    """Update an existing issue."""
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return

    try:
        # Check if issue exists
        issue = core.get_issue(issue_id)
        if not issue:
            console.print(f"❌ Issue not found: {issue_id}", style="bold red")
            return

        # Build update dict
        updates = {}
        if title:
            updates["title"] = title
        if priority:
            updates["priority"] = Priority(priority)
        if status:
            updates["status"] = status
        if assignee is not None:
            # Convert empty string to None for proper unassignment
            if assignee == "":
                updates["assignee"] = None
            else:
                # Validate assignee before updating
                is_valid, result = core.validate_assignee(assignee)
                if not is_valid:
                    console.print(f"❌ Invalid assignee: {result}", style="bold red")
                    raise click.Abort()
                elif result and "Warning:" in result:
                    console.print(f"⚠️  {result}", style="bold yellow")
                    updates["assignee"] = assignee
                else:
                    canonical_assignee = core.get_canonical_assignee(assignee)
                    if canonical_assignee != assignee:
                        console.print(
                            f"🔄 Resolved '{assignee}' to '{canonical_assignee}'",
                            style="dim",
                        )
                    updates["assignee"] = canonical_assignee
        if milestone:
            updates["milestone"] = milestone
        if description:
            updates["description"] = description
        if estimate is not None:
            updates["estimated_hours"] = estimate

        if not updates:
            console.print("❌ No updates specified", style="bold red")
            raise click.Abort()

        # Update the issue
        updated_issue = core.update_issue(issue_id, **updates)

        console.print(f"✅ Updated issue: {updated_issue.title}", style="bold green")
        console.print(f"   ID: {updated_issue.id}", style="cyan")

        # Show what was updated
        for field, value in updates.items():
            if field == "estimated_hours":
                display_value = updated_issue.estimated_time_display
                console.print(f"   estimate: {display_value}", style="cyan")
            elif field in [
                "title",
                "priority",
                "status",
                "assignee",
                "milestone",
                "description",
            ]:
                console.print(f"   {field}: {value}", style="cyan")

        if reason:
            console.print(f"   reason: {reason}", style="dim")

    except click.Abort:
        raise
    except Exception as e:
        error_handler = ErrorHandler()
        error_handler.handle_error(
            ValidationError(
                "Failed to update issue",
                context={"command": "update", "issue_id": issue_id},
                cause=e,
            ),
            exit_on_critical=False,
        )


@issue.command("done")
@click.argument("issue_id")
@click.option("--reason", "-r", help="Reason for marking as done")
@click.pass_context
def done_issue(
    ctx: click.Context,
    issue_id: str,
    reason: str,
):
    """Mark an issue as done."""
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return

    try:
        # Check if issue exists
        issue = core.get_issue(issue_id)
        if not issue:
            console.print(f"❌ Issue not found: {issue_id}", style="bold red")
            return

        # Update status to done
        updated_issue = core.update_issue(issue_id, status="done")

        console.print(f"✅ Finished: {updated_issue.title}", style="bold green")
        console.print(f"   ID: {updated_issue.id}", style="cyan")

        if reason:
            console.print(f"   Reason: {reason}", style="dim")

    except click.Abort:
        raise
    except Exception as e:
        console.print(f"❌ Failed to mark issue as done: {e}", style="bold red")


@issue.command("finish")
@click.argument("issue_id")
@click.option("--reason", "-r", help="Reason for finishing the issue")
@click.option("--date", help="Completion date (YYYY-MM-DD HH:MM, defaults to now)")
@click.option(
    "--record-time",
    "-t",
    is_flag=True,
    help="Record actual completion time and duration (like old 'complete' command)",
)
@click.pass_context
def finish_issue(
    ctx: click.Context, issue_id: str, reason: str, date: str, record_time: bool
):
    """Finish an issue (record completion time, reason).

    Behaves like the original monolithic `issue finish` command.
    """
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return

    try:
        # Parse completion date
        from datetime import datetime

        if record_time:
            if date:
                try:
                    end_date = datetime.strptime(date, "%Y-%m-%d %H:%M")
                except ValueError:
                    try:
                        end_date = datetime.strptime(date, "%Y-%m-%d")
                    except ValueError:
                        console.print(
                            "❌ Invalid date format. Use YYYY-MM-DD or YYYY-MM-DD HH:MM",
                            style="bold red",
                        )
                        return
            else:
                end_date = datetime.now()

        # Prepare update data
        update_data = {
            "status": "done",
            "progress_percentage": 100.0,
        }

        if record_time:
            update_data["actual_end_date"] = end_date

        if reason:
            # Append reason to existing content
            issue = core.get_issue(issue_id)
            if not issue:
                console.print(f"❌ Issue not found: {issue_id}", style="bold red")
                return
            content = issue.content or ""
            completion_note = f"\n\n**Finished:** {reason}"
            update_data["content"] = content + completion_note

        # Update the issue
        success = core.update_issue(issue_id, **update_data)

        if success:
            # Re-fetch issue to display updated values
            updated = core.get_issue(issue_id)
            console.print(f"✅ Finished: {updated.title}", style="bold green")

            if reason:
                console.print(f"   Reason: {reason}", style="cyan")

            if record_time:
                end_display = update_data.get("actual_end_date", datetime.now())
                console.print(
                    f"   Completed: {end_display.strftime('%Y-%m-%d %H:%M')}",
                    style="cyan",
                )

                # Show duration if we have start date
                if updated.actual_start_date:
                    duration = end_display - updated.actual_start_date
                    hours = duration.total_seconds() / 3600
                    console.print(f"   Duration: {hours:.1f} hours", style="cyan")

                    # Compare with estimate
                    if updated.estimated_hours:
                        diff = hours - updated.estimated_hours
                        if abs(diff) > 0.5:
                            if diff > 0:
                                console.print(
                                    f"   Over estimate by: {diff:.1f} hours",
                                    style="yellow",
                                )
                            else:
                                console.print(
                                    f"   Under estimate by: {abs(diff):.1f} hours",
                                    style="green",
                                )
                        else:
                            console.print("   ✅ Right on estimate!", style="green")

            console.print("   Status: Done", style="green")
        else:
            console.print(f"❌ Failed to finish issue: {issue_id}", style="bold red")

    except Exception as e:
        console.print(f"❌ Error finishing issue: {e}", style="bold red")


@issue.command("unblock")
@click.argument("issue_id")
@click.option("--reason", "-r", help="Reason for unblocking")
@click.pass_context
def unblock_issue(ctx: click.Context, issue_id: str, reason: str):
    """Unblock an issue by setting it to in-progress status."""
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return

    try:
        issue = core.get_issue(issue_id)
        if not issue:
            console.print(f"❌ Issue not found: {issue_id}", style="bold red")
            return

        if (
            issue.status
            and getattr(issue.status, "value", str(issue.status)) != "blocked"
        ):
            console.print(
                f"⚠️  Issue is not blocked (current status: {issue.status.value if hasattr(issue.status, 'value') else issue.status})",
                style="yellow",
            )
            return

        success = core.update_issue(
            issue_id,
            status="in-progress",
            content=(issue.content or "")
            + (f"\n\n**Unblocked:** {reason}" if reason else ""),
        )

        if success:
            updated = core.get_issue(issue_id)
            console.print(f"✅ Unblocked issue: {updated.title}", style="bold green")
            console.print(f"   ID: {issue_id}", style="cyan")
            console.print("   Status: 🔄 In Progress", style="yellow")
            if reason:
                console.print(f"   Reason: {reason}", style="cyan")
        else:
            console.print(f"❌ Failed to unblock issue: {issue_id}", style="bold red")

    except Exception as e:
        console.print(f"❌ Failed to unblock issue: {e}", style="bold red")


@issue.command("block")
@click.argument("issue_id")
@click.option("--reason", "-r", help="Reason for blocking")
@click.pass_context
def block_issue(
    ctx: click.Context,
    issue_id: str,
    reason: str,
):
    """Mark an issue as blocked."""
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return

    try:
        # Check if issue exists
        issue = core.get_issue(issue_id)
        if not issue:
            console.print(f"❌ Issue not found: {issue_id}", style="bold red")
            return

        # Update status to blocked
        updated_issue = core.update_issue(issue_id, status="blocked")

        console.print(f"🚫 Blocked issue: {updated_issue.title}", style="bold red")
        console.print(f"   ID: {updated_issue.id}", style="cyan")
        console.print("   Status: 🚫 Blocked", style="red")

        if reason:
            console.print(f"   Reason: {reason}", style="dim")

    except click.Abort:
        raise
    except Exception as e:
        console.print(f"❌ Failed to block issue: {e}", style="bold red")


@issue.command("delete")
@click.argument("issue_id")
@click.option("--yes", is_flag=True, help="Skip confirmation prompt")
@click.pass_context
def delete_issue(
    ctx: click.Context,
    issue_id: str,
    yes: bool,
):
    """Delete an issue."""
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return

    try:
        # Check if issue exists
        issue = core.get_issue(issue_id)
        if not issue:
            console.print(f"❌ Issue not found: {issue_id}", style="bold red")
            return

        # Confirm deletion if not using --yes flag
        if not yes:
            if not click.confirm(
                f"Are you sure you want to delete issue '{issue.title}'?"
            ):
                console.print("❌ Issue deletion cancelled.", style="yellow")
                return

        # Delete the issue
        core.delete_issue(issue_id)

        console.print(
            f"✅ Permanently deleted issue: {issue.title}", style="bold green"
        )
        console.print(f"   ID: {issue_id}", style="cyan")

    except click.Abort:
        raise
    except Exception as e:
        console.print(f"❌ Failed to delete issue: {e}", style="bold red")


@issue.command("start")
@click.argument("issue_id")
@click.option("--date", help="Start date (YYYY-MM-DD HH:MM, defaults to now)")
@click.option(
    "--git-branch/--no-git-branch",
    default=False,
    help="Create a Git branch for this issue when starting",
)
@click.option(
    "--checkout/--no-checkout",
    default=True,
    help="Checkout the created branch (when --git-branch is used)",
)
@click.option("--branch-name", default=None, help="Override suggested branch name")
@click.option(
    "--force", is_flag=True, help="Force branch creation even if working tree is dirty"
)
@click.pass_context
def start_issue(
    ctx: click.Context,
    issue_id: str,
    date: str,
    git_branch: bool,
    checkout: bool,
    branch_name: str,
    force: bool,
):
    """Start work on an issue by recording the actual start date."""
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return

    try:
        from datetime import datetime

        from roadmap.models import Status

        # Parse start date
        if date:
            try:
                start_date = datetime.strptime(date, "%Y-%m-%d %H:%M")
            except ValueError:
                try:
                    start_date = datetime.strptime(date, "%Y-%m-%d")
                except ValueError:
                    console.print(
                        "❌ Invalid date format. Use YYYY-MM-DD or YYYY-MM-DD HH:MM",
                        style="bold red",
                    )
                    return
        else:
            start_date = datetime.now()

        # Get the issue
        issue = core.get_issue(issue_id)
        if not issue:
            console.print(f"❌ Issue not found: {issue_id}", style="bold red")
            return

        # Update issue with start date and status
        success = core.update_issue(
            issue_id,
            actual_start_date=start_date,
            status=Status.IN_PROGRESS,
            progress_percentage=0.0,
        )

        if success:
            console.print(f"🚀 Started work on: {issue.title}", style="bold green")
            console.print(
                f"   Started: {start_date.strftime('%Y-%m-%d %H:%M')}", style="cyan"
            )
            console.print("   Status: In Progress", style="yellow")
            # Determine git-branch behavior: CLI flag overrides, otherwise check config
            try:
                from roadmap.models import RoadmapConfig

                cfg = (
                    RoadmapConfig.load_from_file(core.config_file)
                    if core.config_file.exists()
                    else RoadmapConfig()
                )
                config_auto_branch = bool(cfg.defaults.get("auto_branch", False))
            except Exception:
                config_auto_branch = False

            if not git_branch and config_auto_branch:
                git_branch = True

            # Optionally create a git branch for the issue
            try:
                if git_branch:
                    if hasattr(core, "git") and core.git.is_git_repository():
                        resolved_branch_name = (
                            branch_name or core.git.suggest_branch_name(issue)
                        )
                        branch_success = _safe_create_branch(
                            core.git, issue, checkout=checkout, force=force
                        )
                        if branch_success:
                            console.print(
                                f"🌿 Created Git branch: {resolved_branch_name}",
                                style="green",
                            )
                            if checkout:
                                console.print(
                                    f"✅ Checked out branch: {resolved_branch_name}",
                                    style="green",
                                )
                        else:
                            status_output = (
                                core.git._run_git_command(["status", "--porcelain"])
                                or ""
                            )
                            if status_output.strip():
                                console.print(
                                    "⚠️  Working tree has uncommitted changes — branch creation skipped. Use --force to override.",
                                    style="yellow",
                                )
                            else:
                                console.print(
                                    "⚠️  Failed to create or checkout branch. See git for details.",
                                    style="yellow",
                                )
                    else:
                        console.print(
                            "⚠️  Not in a Git repository, skipping branch creation",
                            style="yellow",
                        )
            except Exception as e:
                console.print(
                    f"⚠️  Git branch creation skipped due to error: {e}", style="yellow"
                )
        else:
            console.print(f"❌ Failed to start issue: {issue_id}", style="bold red")

    except Exception as e:
        console.print(f"❌ Failed to start issue: {e}", style="bold red")


@issue.command("progress")
@click.argument("issue_id")
@click.argument("percentage", type=float)
@click.pass_context
def update_progress(ctx: click.Context, issue_id: str, percentage: float):
    """Update the progress percentage for an issue (0-100)."""
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return

    if not 0 <= percentage <= 100:
        console.print(
            "❌ Progress percentage must be between 0 and 100", style="bold red"
        )
        return

    try:
        # Get the issue
        issue = core.get_issue(issue_id)
        if not issue:
            console.print(f"❌ Issue not found: {issue_id}", style="bold red")
            return

        # Update progress
        success = core.update_issue(issue_id, progress_percentage=percentage)

        if success:
            console.print(f"📊 Updated progress: {issue.title}", style="bold green")
            console.print(f"   Progress: {percentage:.0f}%", style="cyan")

            # Auto-update status based on progress
            if percentage == 0:
                status_msg = "Todo"
            elif percentage == 100:
                status_msg = "Consider marking as done"
                console.print(
                    f"   💡 {status_msg}: roadmap issue complete {issue_id}",
                    style="dim",
                )
            else:
                status_msg = "In Progress"
                if issue.status == Status.TODO:
                    core.update_issue(issue_id, status=Status.IN_PROGRESS)
                    console.print(
                        "   Status: Auto-updated to In Progress", style="yellow"
                    )
        else:
            console.print(f"❌ Failed to update progress: {issue_id}", style="bold red")

    except Exception as e:
        console.print(f"❌ Failed to update progress: {e}", style="bold red")


@issue.group("deps")
def deps():
    """Manage issue dependencies."""
    pass


@deps.command("add")
@click.argument("issue_id")
@click.argument("dependency_id")
@click.pass_context
def add_dependency(ctx: click.Context, issue_id: str, dependency_id: str):
    """Add a dependency to an issue."""
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return

    try:
        # Get the issue
        issue = core.get_issue(issue_id)
        if not issue:
            console.print(f"❌ Issue not found: {issue_id}", style="bold red")
            return

        # Check if dependency issue exists
        dependency_issue = core.get_issue(dependency_id)
        if not dependency_issue:
            console.print(
                f"❌ Dependency issue not found: {dependency_id}", style="bold red"
            )
            return

        # Add dependency
        current_deps = issue.depends_on or []
        if dependency_id not in current_deps:
            current_deps.append(dependency_id)
            core.update_issue(issue_id, depends_on=current_deps)
            console.print(
                f"✅ Added dependency: {dependency_issue.title}", style="bold green"
            )
            console.print(
                f"   {issue.title} now depends on {dependency_issue.title}", style="dim"
            )
        else:
            console.print("⚠️ Dependency already exists", style="yellow")

    except Exception as e:
        console.print(f"❌ Failed to add dependency: {e}", style="bold red")
