"""Main CLI module for the roadmap tool."""

import statistics
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import click
import pandas as pd
from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, TextColumn
from rich.table import Table
from rich.text import Text

from roadmap import __version__
from roadmap.core import RoadmapCore
from roadmap.data_utils import DataAnalyzer, DataFrameAdapter, QueryBuilder
from roadmap.enhanced_analytics import EnhancedAnalyzer
from roadmap.github_client import GitHubClient
from roadmap.models import Comment, IssueType, Priority, Status
from roadmap.performance_sync import HighPerformanceSyncManager
from roadmap.security import (
    configure_security_logging,
    create_secure_file,
    log_security_event,
    sanitize_filename,
    validate_export_size,
    validate_path,
)
from roadmap.sync import SyncManager
from roadmap.visualization import ChartGenerator, DashboardGenerator, VisualizationError

console = Console()


@click.group()
@click.version_option(version=__version__)
@click.pass_context
def main(ctx: click.Context) -> None:
    """Roadmap CLI - A command line tool for creating and managing roadmaps."""
    ctx.ensure_object(dict)

    # Configure security logging
    configure_security_logging()

    # Try to find an existing roadmap directory
    existing_core = RoadmapCore.find_existing_roadmap()
    if existing_core:
        ctx.obj["core"] = existing_core
    else:
        # Default to .roadmap if no existing roadmap found
        ctx.obj["core"] = RoadmapCore()


@main.command()
@click.option(
    "--name",
    "-n",
    default=".roadmap",
    help="Name of the roadmap directory (default: .roadmap)",
)
@click.pass_context
def init(ctx: click.Context, name: str) -> None:
    """Initialize a new roadmap in the current directory.

    Examples:
        roadmap init                    # Creates .roadmap directory
        roadmap init --name my-project  # Creates my-project directory
        roadmap init -n project-docs    # Creates project-docs directory
    """
    # Create a new core instance with the custom directory name
    custom_core = RoadmapCore(roadmap_dir_name=name)

    if custom_core.is_initialized():
        console.print(
            f"❌ Roadmap already initialized in {name}/ directory", style="bold red"
        )
        return

    console.print(f"🗺️  Initializing new roadmap in {name}/...", style="bold green")

    try:
        custom_core.initialize()

        # Update the context to use the custom core
        ctx.obj["core"] = custom_core

        console.print("✅ Roadmap initialized successfully!", style="bold green")
        console.print("\nCreated the following structure:", style="cyan")
        console.print(f"  {name}/")
        console.print("  ├── issues/")
        console.print("  ├── milestones/")
        console.print("  ├── templates/")
        console.print("  ├── artifacts/")
        console.print("  └── config.yaml")
        console.print(
            f"\n📝 Updated .gitignore to exclude {name}/artifacts/ from version control",
            style="dim",
        )
        console.print("\nTry: roadmap issue create 'My first issue'", style="yellow")
    except Exception as e:
        console.print(f"❌ Failed to initialize roadmap: {e}", style="bold red")


@main.command()
@click.option(
    "--assignee", "-a", help="Show dashboard for specific assignee (defaults to you)"
)
@click.option(
    "--days",
    "-d",
    type=int,
    default=7,
    help="Number of days to look ahead (default: 7)",
)
@click.pass_context
def dashboard(ctx: click.Context, assignee: str, days: int):
    """Show your personalized daily dashboard with tasks, blockers, and priorities."""
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return

    try:
        # Determine which assignee to show
        if not assignee:
            # Try to get current user from git config or environment
            assignee = _get_current_user()
            if not assignee:
                console.print(
                    "❌ Could not determine current user. Use --assignee NAME",
                    style="bold red",
                )
                console.print(
                    "Set git user with: git config user.name 'Your Name'", style="dim"
                )
                return

        _display_daily_dashboard(core, assignee, days)

    except Exception as e:
        console.print(f"❌ Failed to show dashboard: {e}", style="bold red")


def _get_current_user() -> Optional[str]:
    """Get current user from git config or environment."""
    from .git_integration import GitIntegration

    # Try Git integration first
    git = GitIntegration()
    user = git.get_current_user()
    if user:
        return user

    # Fallback to environment variable
    import os

    return os.environ.get("USER") or os.environ.get("USERNAME")

    # Fall back to environment variables
    import os

    return os.environ.get("USER") or os.environ.get("USERNAME")


def _display_daily_dashboard(core, assignee: str, days: int):
    """Display the personalized daily dashboard."""
    import datetime

    console.print(f"📊 Daily Dashboard - {assignee}", style="bold blue")
    console.print(f"📅 {datetime.date.today().strftime('%A, %B %d, %Y')}", style="dim")
    console.print()

    # Get all issues
    all_issues = core.list_issues()

    # Filter for this assignee
    my_issues = [i for i in all_issues if i.assignee == assignee]

    if not my_issues:
        console.print(f"🎉 No issues assigned to {assignee}", style="green")
        console.print("Check with your team lead for new assignments", style="dim")
        return

    # Categorize issues
    active_issues = [i for i in my_issues if i.status != Status.DONE]
    today_issues = []
    upcoming_issues = []
    blocked_issues = []
    overdue_issues = []

    # Calculate what needs attention
    today = datetime.date.today()
    future_cutoff = today + datetime.timedelta(days=days)

    for issue in active_issues:
        if issue.status == Status.BLOCKED:
            blocked_issues.append(issue)
        elif issue.is_overdue:
            overdue_issues.append(issue)
        elif issue.status == Status.IN_PROGRESS or issue.priority in [
            Priority.CRITICAL,
            Priority.HIGH,
        ]:
            today_issues.append(issue)
        else:
            upcoming_issues.append(issue)

    # 1. URGENT ATTENTION NEEDED
    urgent_count = len(overdue_issues) + len(blocked_issues)
    if urgent_count > 0:
        console.print("🚨 Urgent Attention Needed", style="bold red")

        if overdue_issues:
            console.print(
                f"   ⏰ {len(overdue_issues)} overdue item{'s' if len(overdue_issues) != 1 else ''}",
                style="red",
            )
            for issue in overdue_issues[:3]:  # Show first 3
                console.print(f"      • {issue.id}: {issue.title}", style="red")

        if blocked_issues:
            console.print(
                f"   🚫 {len(blocked_issues)} blocked item{'s' if len(blocked_issues) != 1 else ''}",
                style="yellow",
            )
            for issue in blocked_issues[:3]:  # Show first 3
                console.print(f"      • {issue.id}: {issue.title}", style="yellow")

        console.print()

    # 2. TODAY'S PRIORITIES
    if today_issues:
        console.print("🎯 Today's Priorities", style="bold green")

        # Sort by priority and progress
        today_issues.sort(key=lambda x: (x.priority.value, x.progress_percentage or 0))

        for issue in today_issues:
            priority_emoji = {
                Priority.CRITICAL: "🔥",
                Priority.HIGH: "⚡",
                Priority.MEDIUM: "📋",
                Priority.LOW: "💤",
            }.get(issue.priority, "📋")

            status_info = ""
            if issue.progress_percentage:
                status_info = f" ({issue.progress_percentage:.0f}%)"
            elif issue.status == Status.IN_PROGRESS:
                status_info = " (in progress)"

            console.print(
                f"   {priority_emoji} {issue.id}: {issue.title}{status_info}",
                style="cyan",
            )

        console.print()

    # 3. UPCOMING WORK
    if upcoming_issues:
        console.print(f"📅 Upcoming ({days} days)", style="bold blue")

        upcoming_issues.sort(key=lambda x: x.priority.value)

        for issue in upcoming_issues[:5]:  # Show first 5
            priority_emoji = {
                Priority.CRITICAL: "🔥",
                Priority.HIGH: "⚡",
                Priority.MEDIUM: "📋",
                Priority.LOW: "💤",
            }.get(issue.priority, "📋")

            console.print(
                f"   {priority_emoji} {issue.id}: {issue.title}", style="white"
            )

        if len(upcoming_issues) > 5:
            console.print(f"   ... and {len(upcoming_issues) - 5} more", style="dim")

        console.print()

    # 4. TEAM IMPACT
    console.print("👥 Team Impact", style="bold magenta")

    # Issues I can unblock for others
    can_unblock = []
    for issue in all_issues:
        if (
            issue.status == Status.BLOCKED
            and issue.depends_on
            and any(
                core.get_issue(dep_id) and core.get_issue(dep_id).assignee == assignee
                for dep_id in issue.depends_on
            )
        ):
            can_unblock.append(issue)

    if can_unblock:
        console.print(
            f"   🔓 You can unblock {len(can_unblock)} item{'s' if len(can_unblock) != 1 else ''} for others:",
            style="yellow",
        )
        for issue in can_unblock[:3]:
            console.print(
                f"      • {issue.id}: {issue.title} (for {issue.assignee or 'unassigned'})",
                style="yellow",
            )

    # Issues blocking me
    blocking_me = []
    for issue in my_issues:
        if issue.depends_on:
            for dep_id in issue.depends_on:
                dep_issue = core.get_issue(dep_id)
                if dep_issue and dep_issue.status != Status.DONE:
                    blocking_me.append((issue, dep_issue))

    if blocking_me:
        console.print(
            f"   ⏳ {len(blocking_me)} item{'s' if len(blocking_me) != 1 else ''} waiting on dependencies:",
            style="blue",
        )
        for my_issue, blocking_issue in blocking_me[:3]:
            blocker_assignee = blocking_issue.assignee or "unassigned"
            console.print(
                f"      • {my_issue.id} waits for {blocking_issue.id} ({blocker_assignee})",
                style="blue",
            )

    if not can_unblock and not blocking_me:
        console.print("   ✅ No dependency issues affecting team", style="green")

    console.print()

    # 5. QUICK STATS
    total_active = len(active_issues)
    total_done_today = len(
        [
            i
            for i in my_issues
            if i.status == Status.DONE
            and i.actual_end_date
            and i.actual_end_date.date() == today
        ]
    )

    console.print("📈 Quick Stats", style="bold white")
    console.print(
        f"   Active: {total_active} | Completed today: {total_done_today}", style="cyan"
    )

    # Calculate total estimated time remaining
    remaining_hours = sum(issue.estimated_hours or 0 for issue in active_issues)
    if remaining_hours > 0:
        if remaining_hours >= 8:
            days_remaining = remaining_hours / 8
            console.print(
                f"   Estimated remaining: {remaining_hours:.1f}h ({days_remaining:.1f}d)",
                style="cyan",
            )
        else:
            console.print(
                f"   Estimated remaining: {remaining_hours:.1f}h", style="cyan"
            )

    console.print()

    # 6. SUGGESTED ACTIONS
    console.print("💡 Suggested Actions", style="bold yellow")

    if overdue_issues:
        console.print("   1. Address overdue items first", style="yellow")
    elif blocked_issues:
        console.print(
            "   1. Review blocked items and escalate if needed", style="yellow"
        )
    elif today_issues:
        highest_priority = min(today_issues, key=lambda x: x.priority.value)
        console.print(
            f"   1. Focus on: {highest_priority.id} ({highest_priority.title})",
            style="green",
        )
    elif upcoming_issues:
        next_issue = min(upcoming_issues, key=lambda x: x.priority.value)
        console.print(
            f"   1. Consider starting: {next_issue.id} ({next_issue.title})",
            style="green",
        )

    if can_unblock:
        console.print("   2. Complete work to unblock teammates", style="yellow")

    console.print("   3. Update progress on active items", style="dim")


@main.command()
@click.option(
    "--assignee",
    "-a",
    help="Show notifications for specific assignee (defaults to you)",
)
@click.option(
    "--since",
    "-s",
    help="Show notifications since date (YYYY-MM-DD, defaults to today)",
)
@click.option("--mark-read", is_flag=True, help="Mark all notifications as read")
@click.pass_context
def notifications(ctx: click.Context, assignee: str, since: str, mark_read: bool):
    """Show team notifications about issues affecting you."""
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return

    try:
        # Determine which assignee to show
        if not assignee:
            assignee = _get_current_user()
            if not assignee:
                console.print(
                    "❌ Could not determine current user. Use --assignee NAME",
                    style="bold red",
                )
                return

        # Parse since date
        import datetime

        if since:
            try:
                since_date = datetime.datetime.strptime(since, "%Y-%m-%d").date()
            except ValueError:
                console.print(
                    "❌ Invalid date format. Use YYYY-MM-DD", style="bold red"
                )
                return
        else:
            since_date = datetime.date.today()

        notifications = _get_notifications_for_user(core, assignee, since_date)
        _display_notifications(notifications, mark_read)

    except Exception as e:
        console.print(f"❌ Failed to show notifications: {e}", style="bold red")


@main.command()
@click.argument("message")
@click.option(
    "--assignee", "-a", help="Send update to specific assignee (defaults to team)"
)
@click.option("--issue", "-i", help="Associate update with specific issue ID")
@click.pass_context
def broadcast(ctx: click.Context, message: str, assignee: str, issue: str):
    """Broadcast a status update to the team."""
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return

    try:
        sender = _get_current_user()
        if not sender:
            console.print("❌ Could not determine current user", style="bold red")
            return

        # Store the broadcast message
        _store_team_update(core, sender, message, assignee, issue)

        if assignee:
            console.print(
                f"📢 Update sent to {assignee}: {message}", style="bold green"
            )
        else:
            console.print(f"📢 Team update: {message}", style="bold green")

    except Exception as e:
        console.print(f"❌ Failed to send update: {e}", style="bold red")


@main.command()
@click.option("--days", "-d", type=int, default=7, help="Show activity for last N days")
@click.option("--assignee", "-a", help="Filter by assignee")
@click.pass_context
def activity(ctx: click.Context, days: int, assignee: str):
    """Show recent team activity and updates."""
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return

    try:
        import datetime

        since_date = datetime.date.today() - datetime.timedelta(days=days)

        activity_feed = _get_team_activity(core, since_date, assignee)
        _display_activity_feed(activity_feed, days)

    except Exception as e:
        console.print(f"❌ Failed to show activity: {e}", style="bold red")


def _get_notifications_for_user(core, assignee: str, since_date) -> list:
    """Get notifications relevant to a specific user."""
    notifications = []
    all_issues = core.list_issues()

    # Issues assigned to user
    my_issues = [i for i in all_issues if i.assignee == assignee]

    # Check for dependency notifications
    for issue in my_issues:
        if issue.depends_on:
            for dep_id in issue.depends_on:
                dep_issue = core.get_issue(dep_id)
                if dep_issue:
                    # Check if dependency was recently completed
                    if (
                        dep_issue.status == Status.DONE
                        and dep_issue.actual_end_date
                        and dep_issue.actual_end_date.date() >= since_date
                    ):
                        notifications.append(
                            {
                                "type": "dependency_completed",
                                "message": f"🔓 Dependency completed: {dep_issue.title}",
                                "details": f"You can now start work on {issue.title}",
                                "issue_id": issue.id,
                                "related_issue_id": dep_issue.id,
                                "priority": "high",
                                "date": dep_issue.actual_end_date,
                            }
                        )

                    # Check if dependency is overdue
                    elif dep_issue.is_overdue and dep_issue.assignee != assignee:
                        notifications.append(
                            {
                                "type": "dependency_overdue",
                                "message": f"⚠️  Dependency overdue: {dep_issue.title}",
                                "details": f"This may delay your work on {issue.title}",
                                "issue_id": issue.id,
                                "related_issue_id": dep_issue.id,
                                "priority": "medium",
                                "date": datetime.datetime.now(),
                            }
                        )

    # Check for issues I'm blocking
    for issue in all_issues:
        if issue.depends_on and any(
            core.get_issue(dep_id) and core.get_issue(dep_id).assignee == assignee
            for dep_id in issue.depends_on
        ):

            # Check if someone is waiting on me
            blocking_issues = [
                core.get_issue(dep_id)
                for dep_id in issue.depends_on
                if core.get_issue(dep_id)
                and core.get_issue(dep_id).assignee == assignee
            ]

            for blocking_issue in blocking_issues:
                if blocking_issue.status != Status.DONE:
                    notifications.append(
                        {
                            "type": "blocking_someone",
                            "message": f"🚫 {issue.assignee or 'Someone'} waiting on: {blocking_issue.title}",
                            "details": f"Complete this to unblock {issue.title}",
                            "issue_id": blocking_issue.id,
                            "related_issue_id": issue.id,
                            "priority": (
                                "high"
                                if issue.priority == Priority.CRITICAL
                                else "medium"
                            ),
                            "date": datetime.datetime.now(),
                        }
                    )

    # Check for new assignments
    for issue in my_issues:
        if (
            issue.created
            and issue.created.date() >= since_date
            and issue.status == Status.TODO
        ):
            notifications.append(
                {
                    "type": "new_assignment",
                    "message": f"📋 New assignment: {issue.title}",
                    "details": f"Priority: {issue.priority.value}",
                    "issue_id": issue.id,
                    "priority": "medium",
                    "date": issue.created,
                }
            )

    # Sort by priority and date
    priority_order = {"high": 0, "medium": 1, "low": 2}
    notifications.sort(
        key=lambda x: (priority_order.get(x["priority"], 2), x["date"]), reverse=True
    )

    return notifications


def _display_notifications(notifications: list, mark_read: bool):
    """Display notifications to the user."""
    if not notifications:
        console.print("📭 No new notifications", style="green")
        return

    console.print(f"🔔 Notifications ({len(notifications)})", style="bold blue")
    console.print()

    for i, notification in enumerate(notifications, 1):
        priority_style = {"high": "bold red", "medium": "yellow", "low": "dim"}.get(
            notification["priority"], "white"
        )

        console.print(f"{i}. {notification['message']}", style=priority_style)
        console.print(f"   {notification['details']}", style="dim")

        if notification.get("issue_id"):
            console.print(f"   📌 Issue: {notification['issue_id']}", style="cyan")

        console.print()

    if mark_read:
        console.print("✅ All notifications marked as read", style="green")


def _store_team_update(
    core, sender: str, message: str, target_assignee: str = None, issue_id: str = None
):
    """Store a team update for later retrieval."""
    import datetime
    import json
    from pathlib import Path

    # Store updates in .roadmap/updates.json
    updates_file = core.roadmap_dir / "updates.json"

    # Load existing updates
    updates = []
    if updates_file.exists():
        try:
            # Validate the path first
            validate_path(str(updates_file))
            with open(updates_file, "r") as f:
                updates = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            updates = []

    # Add new update
    update = {
        "timestamp": datetime.datetime.now().isoformat(),
        "sender": sender,
        "message": message,
        "target_assignee": target_assignee,
        "issue_id": issue_id,
        "type": "broadcast",
    }

    updates.append(update)

    # Keep only last 100 updates
    updates = updates[-100:]

    # Save updates
    with create_secure_file(updates_file, "w") as f:
        json.dump(updates, f, indent=2)


def _get_team_activity(core, since_date, assignee_filter: str = None) -> list:
    """Get team activity since a certain date."""
    import datetime
    import json

    activity = []

    # Get stored updates
    updates_file = core.roadmap_dir / "updates.json"
    if updates_file.exists():
        try:
            # Validate the path first
            validate_path(str(updates_file))
            with open(updates_file, "r") as f:
                updates = json.load(f)

            for update in updates:
                update_date = datetime.datetime.fromisoformat(
                    update["timestamp"]
                ).date()
                if update_date >= since_date:
                    if not assignee_filter or update["sender"] == assignee_filter:
                        activity.append(
                            {
                                "type": "team_update",
                                "timestamp": datetime.datetime.fromisoformat(
                                    update["timestamp"]
                                ),
                                "author": update["sender"],
                                "message": update["message"],
                                "issue_id": update.get("issue_id"),
                            }
                        )
        except (json.JSONDecodeError, FileNotFoundError):
            pass

    # Get issue activity
    issues = core.list_issues()
    for issue in issues:
        # Issue completion
        if (
            issue.actual_end_date
            and issue.actual_end_date.date() >= since_date
            and issue.assignee
        ):
            if not assignee_filter or issue.assignee == assignee_filter:
                activity.append(
                    {
                        "type": "issue_completed",
                        "timestamp": issue.actual_end_date,
                        "author": issue.assignee,
                        "message": f"Completed: {issue.title}",
                        "issue_id": issue.id,
                    }
                )

        # Issue started
        if (
            issue.actual_start_date
            and issue.actual_start_date.date() >= since_date
            and issue.assignee
        ):
            if not assignee_filter or issue.assignee == assignee_filter:
                activity.append(
                    {
                        "type": "issue_started",
                        "timestamp": issue.actual_start_date,
                        "author": issue.assignee,
                        "message": f"Started: {issue.title}",
                        "issue_id": issue.id,
                    }
                )

        # Issue created
        if issue.created and issue.created.date() >= since_date:
            activity.append(
                {
                    "type": "issue_created",
                    "timestamp": issue.created,
                    "author": "system",
                    "message": f"Created: {issue.title}",
                    "issue_id": issue.id,
                }
            )

    # Sort by timestamp
    activity.sort(key=lambda x: x["timestamp"], reverse=True)

    return activity


def _display_activity_feed(activity: list, days: int):
    """Display the team activity feed."""
    if not activity:
        console.print(f"📭 No team activity in the last {days} days", style="dim")
        return

    console.print(f"📈 Team Activity (last {days} days)", style="bold blue")
    console.print()

    # Group by date
    import datetime
    from collections import defaultdict

    by_date = defaultdict(list)
    for item in activity:
        date_key = item["timestamp"].date()
        by_date[date_key].append(item)

    # Display by date
    for date in sorted(by_date.keys(), reverse=True):
        items = by_date[date]

        # Date header
        if date == datetime.date.today():
            date_str = "Today"
        elif date == datetime.date.today() - datetime.timedelta(days=1):
            date_str = "Yesterday"
        else:
            date_str = date.strftime("%B %d")

        console.print(f"📅 {date_str}", style="bold white")

        # Items for this date
        for item in items:
            time_str = item["timestamp"].strftime("%H:%M")

            icon = {
                "issue_completed": "✅",
                "issue_started": "🚀",
                "issue_created": "📋",
                "team_update": "📢",
            }.get(item["type"], "📝")

            console.print(
                f"   {time_str} {icon} {item['author']}: {item['message']}",
                style="cyan",
            )

            if item.get("issue_id"):
                console.print(f"        📌 {item['issue_id']}", style="dim")

        console.print()


@main.command()
@click.argument("issue_id")
@click.argument("new_assignee")
@click.option("--notes", "-n", help="Handoff notes for the new assignee")
@click.option(
    "--preserve-progress", is_flag=True, help="Preserve current progress percentage"
)
@click.pass_context
def handoff(
    ctx: click.Context,
    issue_id: str,
    new_assignee: str,
    notes: str,
    preserve_progress: bool,
):
    """Hand off an issue to another team member."""
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return

    try:
        issue = core.get_issue(issue_id)
        if not issue:
            console.print(f"❌ Issue {issue_id} not found", style="bold red")
            return

        # Store handoff information
        old_assignee = issue.assignee

        # Prepare update parameters
        update_params = {
            "assignee": new_assignee,
            "previous_assignee": old_assignee,
            "handoff_date": datetime.now(),
        }

        if notes:
            update_params["handoff_notes"] = notes

        # Reset progress if not preserving
        if not preserve_progress:
            update_params["progress_percentage"] = None
            update_params["actual_start_date"] = None

        core.update_issue(issue_id, **update_params)

        # Display success message
        console.print(
            f"🔄 Issue handed off from {old_assignee or 'unassigned'} to {new_assignee}",
            style="bold green",
        )
        console.print(f"   📋 {issue.title}", style="cyan")

        if notes:
            console.print(f"   📝 Notes: {notes}", style="dim")

        if preserve_progress and issue.progress_percentage:
            console.print(
                f"   📊 Progress preserved: {issue.progress_percentage:.0f}%",
                style="yellow",
            )

        # Store team update about the handoff
        _store_team_update(
            core,
            old_assignee or "system",
            f"Handed off '{issue.title}' to {new_assignee}"
            + (f": {notes}" if notes else ""),
            new_assignee,
            issue_id,
        )

    except Exception as e:
        console.print(f"❌ Failed to hand off issue: {e}", style="bold red")


@main.command()
@click.argument("issue_id")
@click.pass_context
def handoff_context(ctx: click.Context, issue_id: str):
    """Show handoff context and history for an issue."""
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return

    try:
        issue = core.get_issue(issue_id)
        if not issue:
            console.print(f"❌ Issue {issue_id} not found", style="bold red")
            return

        console.print(f"🔄 Handoff Context: {issue.title}", style="bold blue")
        console.print(f"   📌 ID: {issue.id}", style="cyan")
        console.print()

        # Current assignment
        console.print("📋 Current Assignment:", style="bold white")
        console.print(
            f"   👤 Assignee: {issue.assignee or 'Unassigned'}", style="green"
        )
        console.print(f"   📊 Progress: {issue.progress_display}", style="yellow")
        console.print(f"   🎯 Status: {issue.status.value}", style="cyan")
        console.print()

        # Handoff history
        if issue.has_been_handed_off:
            console.print("🔄 Handoff History:", style="bold white")
            console.print(
                f"   📅 Date: {issue.handoff_date.strftime('%Y-%m-%d %H:%M')}",
                style="dim",
            )
            console.print(f"   👤 From: {issue.previous_assignee}", style="red")
            console.print(f"   👤 To: {issue.assignee}", style="green")

            if issue.handoff_notes:
                console.print(f"   📝 Notes:", style="bold white")
                # Word wrap the notes for better display
                import textwrap

                wrapped_notes = textwrap.fill(
                    issue.handoff_notes,
                    width=60,
                    initial_indent="      ",
                    subsequent_indent="      ",
                )
                console.print(wrapped_notes, style="dim")
            console.print()
        else:
            console.print("📋 No previous handoffs", style="dim")
            console.print()

        # Work tracking
        console.print("⏱️  Work Tracking:", style="bold white")
        if issue.actual_start_date:
            console.print(
                f"   🚀 Started: {issue.actual_start_date.strftime('%Y-%m-%d %H:%M')}",
                style="green",
            )
        else:
            console.print("   🚀 Not started", style="dim")

        if issue.actual_end_date:
            console.print(
                f"   ✅ Completed: {issue.actual_end_date.strftime('%Y-%m-%d %H:%M')}",
                style="green",
            )
        else:
            console.print("   ✅ Not completed", style="dim")

        if issue.estimated_hours:
            console.print(
                f"   ⏳ Estimated: {issue.estimated_time_display}", style="yellow"
            )

        if issue.actual_duration_hours:
            console.print(
                f"   ⏱️  Actual: {issue.actual_duration_hours:.1f}h", style="cyan"
            )
        console.print()

        # Dependencies context
        if issue.depends_on or issue.blocks:
            console.print("🔗 Dependencies:", style="bold white")

            if issue.depends_on:
                console.print("   📥 Depends on:", style="yellow")
                for dep_id in issue.depends_on:
                    dep_issue = core.get_issue(dep_id)
                    if dep_issue:
                        status_style = (
                            "green" if dep_issue.status == Status.DONE else "red"
                        )
                        console.print(
                            f"      • {dep_issue.title} ({dep_issue.status.value})",
                            style=status_style,
                        )
                    else:
                        console.print(f"      • {dep_id} (not found)", style="dim")

            if issue.blocks:
                console.print("   📤 Blocks:", style="yellow")
                for blocked_id in issue.blocks:
                    blocked_issue = core.get_issue(blocked_id)
                    if blocked_issue:
                        console.print(
                            f"      • {blocked_issue.title} (assigned to {blocked_issue.assignee})",
                            style="cyan",
                        )
                    else:
                        console.print(f"      • {blocked_id} (not found)", style="dim")
            console.print()

        # Suggestions for the current assignee
        if issue.assignee:
            console.print("💡 Suggestions:", style="bold blue")

            if not issue.is_started and issue.depends_on:
                unfinished_deps = [
                    core.get_issue(dep_id)
                    for dep_id in issue.depends_on
                    if core.get_issue(dep_id)
                    and core.get_issue(dep_id).status != Status.DONE
                ]
                if unfinished_deps:
                    console.print(
                        "   ⚠️  Wait for dependencies to complete first", style="yellow"
                    )
                    for dep in unfinished_deps:
                        console.print(
                            f"      • {dep.title} (assigned to {dep.assignee})",
                            style="dim",
                        )
                else:
                    console.print(
                        "   🚀 All dependencies ready - you can start!", style="green"
                    )

            elif issue.is_started and not issue.is_completed:
                console.print("   📈 Continue working on this issue", style="cyan")

            elif issue.is_completed:
                console.print("   ✅ This issue is complete", style="green")

            else:
                console.print(
                    "   🚀 Ready to start when you're available", style="cyan"
                )

    except Exception as e:
        console.print(f"❌ Failed to show handoff context: {e}", style="bold red")


@main.command()
@click.option("--assignee", "-a", help="Filter by assignee")
@click.option("--show-completed", is_flag=True, help="Include completed handoffs")
@click.pass_context
def handoff_list(ctx: click.Context, assignee: str, show_completed: bool):
    """List all recent handoffs in the project."""
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return

    try:
        issues = core.list_issues()
        handed_off_issues = [i for i in issues if i.has_been_handed_off]

        # Filter by assignee if specified
        if assignee:
            handed_off_issues = [
                i
                for i in handed_off_issues
                if i.assignee == assignee or i.previous_assignee == assignee
            ]

        # Filter out completed unless requested
        if not show_completed:
            handed_off_issues = [
                i for i in handed_off_issues if i.status != Status.DONE
            ]

        if not handed_off_issues:
            console.print("📭 No handoffs found", style="dim")
            return

        # Sort by handoff date
        handed_off_issues.sort(key=lambda x: x.handoff_date, reverse=True)

        console.print(
            f"🔄 Recent Handoffs ({len(handed_off_issues)})", style="bold blue"
        )
        console.print()

        for issue in handed_off_issues:
            # Status indicator
            status_icon = {
                Status.TODO: "📋",
                Status.IN_PROGRESS: "🚀",
                Status.BLOCKED: "🚫",
                Status.REVIEW: "👀",
                Status.DONE: "✅",
            }.get(issue.status, "📝")

            # Handoff direction
            console.print(f"{status_icon} {issue.title}", style="bold white")
            console.print(
                f"   🔄 {issue.previous_assignee} → {issue.assignee}", style="cyan"
            )
            console.print(
                f"   📅 {issue.handoff_date.strftime('%Y-%m-%d %H:%M')}", style="dim"
            )
            console.print(
                f"   📌 {issue.id} | {issue.status.value} | {issue.progress_display}",
                style="yellow",
            )

            if issue.handoff_notes:
                # Truncate long notes
                notes_preview = (
                    (issue.handoff_notes[:60] + "...")
                    if len(issue.handoff_notes) > 60
                    else issue.handoff_notes
                )
                console.print(f"   📝 {notes_preview}", style="dim")

            console.print()

    except Exception as e:
        console.print(f"❌ Failed to list handoffs: {e}", style="bold red")


@main.command()
@click.option("--assignee", "-a", help="Analyze workload for specific assignee")
@click.option(
    "--include-estimates", is_flag=True, help="Include time estimates in analysis"
)
@click.option("--suggest-rebalance", is_flag=True, help="Suggest workload rebalancing")
@click.pass_context
def workload_analysis(
    ctx: click.Context, assignee: str, include_estimates: bool, suggest_rebalance: bool
):
    """Analyze team workload and capacity."""
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return

    try:
        issues = core.list_issues()

        if assignee:
            # Single assignee analysis
            _analyze_individual_workload(issues, assignee, include_estimates)
        else:
            # Team-wide analysis
            _analyze_team_workload(issues, include_estimates, suggest_rebalance)

    except Exception as e:
        console.print(f"❌ Failed to analyze workload: {e}", style="bold red")


@main.command()
@click.argument("issue_id")
@click.option(
    "--consider-skills", is_flag=True, help="Consider team member skills (experimental)"
)
@click.option("--consider-availability", is_flag=True, help="Consider current workload")
@click.option("--suggest-only", is_flag=True, help="Only suggest, don't assign")
@click.pass_context
def smart_assign(
    ctx: click.Context,
    issue_id: str,
    consider_skills: bool,
    consider_availability: bool,
    suggest_only: bool,
):
    """Intelligently assign an issue to the best team member."""
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return

    try:
        issue = core.get_issue(issue_id)
        if not issue:
            console.print(f"❌ Issue {issue_id} not found", style="bold red")
            return

        issues = core.list_issues()
        suggestion = _get_smart_assignment_suggestion(
            issue, issues, consider_skills, consider_availability
        )

        if not suggestion:
            console.print("❌ Could not determine optimal assignment", style="bold red")
            return

        _display_assignment_suggestion(issue, suggestion, suggest_only)

        if not suggest_only and suggestion["assignee"]:
            # Confirm assignment
            if click.confirm(f"Assign '{issue.title}' to {suggestion['assignee']}?"):
                issue.assignee = suggestion["assignee"]
                core.update_issue(issue)
                console.print(
                    f"✅ Assigned to {suggestion['assignee']}", style="bold green"
                )

    except Exception as e:
        console.print(f"❌ Failed to suggest assignment: {e}", style="bold red")


@main.command()
@click.option("--days", "-d", type=int, default=14, help="Forecast period in days")
@click.option("--assignee", "-a", help="Forecast for specific assignee")
@click.pass_context
def capacity_forecast(ctx: click.Context, days: int, assignee: str):
    """Forecast team capacity and bottlenecks."""
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return

    try:
        issues = core.list_issues()
        _generate_capacity_forecast(issues, days, assignee)

    except Exception as e:
        console.print(f"❌ Failed to generate forecast: {e}", style="bold red")


def _analyze_individual_workload(issues: list, assignee: str, include_estimates: bool):
    """Analyze workload for a specific team member."""
    user_issues = [i for i in issues if i.assignee == assignee]

    if not user_issues:
        console.print(f"📭 No issues assigned to {assignee}", style="dim")
        return

    console.print(f"👤 Workload Analysis: {assignee}", style="bold blue")
    console.print()

    # Status breakdown
    from collections import defaultdict

    status_breakdown = defaultdict(list)
    total_estimated_hours = 0

    for issue in user_issues:
        status_breakdown[issue.status].append(issue)
        if issue.estimated_hours:
            total_estimated_hours += issue.estimated_hours

    # Current status
    console.print("📊 Current Status:", style="bold white")
    for status, status_issues in status_breakdown.items():
        count = len(status_issues)

        if include_estimates:
            status_hours = sum(i.estimated_hours or 0 for i in status_issues)
            console.print(
                f"   {status.value}: {count} issues ({status_hours:.1f}h)", style="cyan"
            )
        else:
            console.print(f"   {status.value}: {count} issues", style="cyan")

    console.print()

    if include_estimates and total_estimated_hours > 0:
        console.print(
            f"⏱️  Total estimated work: {total_estimated_hours:.1f}h ({total_estimated_hours/8:.1f} days)",
            style="yellow",
        )
        console.print()

    # Priority analysis
    high_priority = [
        i for i in user_issues if i.priority in [Priority.CRITICAL, Priority.HIGH]
    ]
    blocked_issues = [i for i in user_issues if i.status == Status.BLOCKED]
    overdue_issues = [i for i in user_issues if i.is_overdue]

    if high_priority:
        console.print(f"🔥 High priority items: {len(high_priority)}", style="bold red")
        for issue in high_priority[:3]:  # Show top 3
            console.print(f"   • {issue.title} ({issue.priority.value})", style="red")
        if len(high_priority) > 3:
            console.print(f"   ... and {len(high_priority) - 3} more", style="dim")
        console.print()

    if blocked_issues:
        console.print(f"🚫 Blocked items: {len(blocked_issues)}", style="bold red")
        for issue in blocked_issues:
            console.print(f"   • {issue.title}", style="red")
        console.print()

    if overdue_issues:
        console.print(f"⚠️  Overdue items: {len(overdue_issues)}", style="bold yellow")
        for issue in overdue_issues:
            console.print(f"   • {issue.title}", style="yellow")
        console.print()

    # Workload assessment
    workload_score = _calculate_workload_score(user_issues)
    workload_status = _get_workload_status(workload_score)

    console.print(
        f"📈 Workload Status: {workload_status['label']}",
        style=workload_status["style"],
    )
    console.print(f"   {workload_status['description']}", style="dim")


def _analyze_team_workload(
    issues: list, include_estimates: bool, suggest_rebalance: bool
):
    """Analyze workload across the entire team."""
    from collections import defaultdict

    # Group by assignee
    assignee_issues = defaultdict(list)
    unassigned_issues = []

    for issue in issues:
        if issue.assignee:
            assignee_issues[issue.assignee].append(issue)
        else:
            unassigned_issues.append(issue)

    console.print("👥 Team Workload Analysis", style="bold blue")
    console.print()

    if not assignee_issues:
        console.print("📭 No assigned issues found", style="dim")
        return

    # Workload table
    table = Table(title="Team Workload Distribution")
    table.add_column("Assignee", style="cyan")
    table.add_column("Total Issues", justify="center")
    table.add_column("In Progress", justify="center", style="yellow")
    table.add_column("Blocked", justify="center", style="red")
    table.add_column("High Priority", justify="center", style="bold red")

    if include_estimates:
        table.add_column("Est. Hours", justify="center", style="green")
        table.add_column("Workload", justify="center")

    workload_data = []

    for assignee, user_issues in assignee_issues.items():
        total_count = len(user_issues)
        in_progress_count = len(
            [i for i in user_issues if i.status == Status.IN_PROGRESS]
        )
        blocked_count = len([i for i in user_issues if i.status == Status.BLOCKED])
        high_priority_count = len(
            [i for i in user_issues if i.priority in [Priority.CRITICAL, Priority.HIGH]]
        )

        estimated_hours = sum(i.estimated_hours or 0 for i in user_issues)
        workload_score = _calculate_workload_score(user_issues)
        workload_status = _get_workload_status(workload_score)

        workload_data.append(
            {
                "assignee": assignee,
                "total": total_count,
                "in_progress": in_progress_count,
                "blocked": blocked_count,
                "high_priority": high_priority_count,
                "estimated_hours": estimated_hours,
                "workload_score": workload_score,
                "workload_status": workload_status,
            }
        )

        row = [
            assignee,
            str(total_count),
            str(in_progress_count),
            str(blocked_count),
            str(high_priority_count),
        ]

        if include_estimates:
            row.extend([f"{estimated_hours:.1f}h", workload_status["label"]])

        table.add_row(*row)

    console.print(table)
    console.print()

    # Unassigned issues
    if unassigned_issues:
        unassigned_hours = sum(i.estimated_hours or 0 for i in unassigned_issues)
        console.print(f"📋 Unassigned Issues: {len(unassigned_issues)}", style="yellow")
        if include_estimates and unassigned_hours > 0:
            console.print(
                f"   Total estimated work: {unassigned_hours:.1f}h", style="dim"
            )
        console.print()

    # Team insights
    _display_team_insights(workload_data, suggest_rebalance)


def _calculate_workload_score(issues: list) -> float:
    """Calculate a workload score based on issue count, priority, and estimates."""
    if not issues:
        return 0.0

    score = 0.0

    for issue in issues:
        # Base score per issue
        issue_score = 1.0

        # Priority multiplier
        priority_multiplier = {
            Priority.CRITICAL: 3.0,
            Priority.HIGH: 2.0,
            Priority.MEDIUM: 1.0,
            Priority.LOW: 0.5,
        }.get(issue.priority, 1.0)

        # Status multiplier (blocked items count more)
        status_multiplier = {
            Status.BLOCKED: 1.5,
            Status.IN_PROGRESS: 1.2,
            Status.REVIEW: 1.1,
            Status.TODO: 1.0,
            Status.DONE: 0.1,  # Completed work counts very little
        }.get(issue.status, 1.0)

        # Time estimate factor
        if issue.estimated_hours:
            time_factor = min(issue.estimated_hours / 8, 3.0)  # Cap at 3 days worth
        else:
            time_factor = 1.0

        issue_score *= priority_multiplier * status_multiplier * time_factor
        score += issue_score

    return score


def _get_workload_status(score: float) -> dict:
    """Get workload status description based on score."""
    if score <= 2.0:
        return {
            "label": "Light",
            "style": "green",
            "description": "Capacity available for new work",
        }
    elif score <= 5.0:
        return {
            "label": "Moderate",
            "style": "yellow",
            "description": "Balanced workload, some capacity available",
        }
    elif score <= 10.0:
        return {
            "label": "Heavy",
            "style": "red",
            "description": "High workload, limited capacity",
        }
    else:
        return {
            "label": "Overloaded",
            "style": "bold red",
            "description": "Unsustainable workload, needs rebalancing",
        }


def _display_team_insights(workload_data: list, suggest_rebalance: bool):
    """Display insights about team workload distribution."""
    if not workload_data:
        return

    console.print("💡 Team Insights:", style="bold blue")

    # Find workload extremes
    workload_data.sort(key=lambda x: x["workload_score"])
    lightest = workload_data[0]
    heaviest = workload_data[-1]

    # Workload distribution
    overloaded = [w for w in workload_data if w["workload_score"] > 10.0]
    light_load = [w for w in workload_data if w["workload_score"] <= 2.0]

    if overloaded:
        console.print(
            f"⚠️  {len(overloaded)} team member(s) overloaded:", style="bold red"
        )
        for member in overloaded:
            console.print(
                f"   • {member['assignee']} (score: {member['workload_score']:.1f})",
                style="red",
            )

    if light_load:
        console.print(
            f"✅ {len(light_load)} team member(s) have capacity:", style="green"
        )
        for member in light_load:
            console.print(
                f"   • {member['assignee']} (score: {member['workload_score']:.1f})",
                style="green",
            )

    # Suggest rebalancing
    if suggest_rebalance and overloaded and light_load:
        console.print()
        console.print("🔄 Rebalancing Suggestions:", style="bold yellow")
        console.print(
            f"   Consider moving work from {overloaded[0]['assignee']} to {light_load[0]['assignee']}",
            style="cyan",
        )

    console.print()


def _get_smart_assignment_suggestion(
    issue, all_issues: list, consider_skills: bool, consider_availability: bool
) -> dict:
    """Generate smart assignment suggestion for an issue."""
    from collections import defaultdict

    # Get all potential assignees
    assignees = set()
    for i in all_issues:
        if i.assignee:
            assignees.add(i.assignee)

    if not assignees:
        return None

    suggestion_scores = {}

    for assignee in assignees:
        score = 0.0

        # Base availability score
        if consider_availability:
            user_issues = [i for i in all_issues if i.assignee == assignee]
            workload_score = _calculate_workload_score(user_issues)

            # Lower workload = higher availability score
            availability_score = max(0, 10 - workload_score)
            score += availability_score
        else:
            score += 5.0  # Neutral score if not considering availability

        # Skill matching (experimental)
        if consider_skills:
            skill_score = _calculate_skill_match(issue, assignee, all_issues)
            score += skill_score

        # Dependency considerations
        if issue.depends_on:
            dependency_score = _calculate_dependency_score(issue, assignee, all_issues)
            score += dependency_score

        suggestion_scores[assignee] = score

    # Find best assignment
    best_assignee = max(suggestion_scores, key=suggestion_scores.get)
    best_score = suggestion_scores[best_assignee]

    return {
        "assignee": best_assignee,
        "score": best_score,
        "confidence": (
            "high" if best_score > 8 else "medium" if best_score > 5 else "low"
        ),
        "reasoning": _generate_assignment_reasoning(
            best_assignee, best_score, consider_skills, consider_availability
        ),
    }


def _calculate_skill_match(issue, assignee: str, all_issues: list) -> float:
    """Calculate skill match score based on previous work (experimental)."""
    # This is a simplified heuristic - in practice, you'd want more sophisticated skill tracking
    user_issues = [i for i in all_issues if i.assignee == assignee]

    # Check if assignee has worked on similar issue types
    similar_types = [i for i in user_issues if i.issue_type == issue.issue_type]
    type_experience = len(similar_types) * 0.5

    # Check if assignee has worked on similar priority items
    similar_priority = [i for i in user_issues if i.priority == issue.priority]
    priority_experience = len(similar_priority) * 0.2

    return min(type_experience + priority_experience, 3.0)  # Cap at 3.0


def _calculate_dependency_score(issue, assignee: str, all_issues: list) -> float:
    """Calculate score bonus for dependency relationships."""
    score = 0.0

    # Bonus if assignee is working on dependencies
    if issue.depends_on:
        for dep_id in issue.depends_on:
            dep_issue = next((i for i in all_issues if i.id == dep_id), None)
            if dep_issue and dep_issue.assignee == assignee:
                score += 1.0  # Bonus for working on related items

    return score


def _generate_assignment_reasoning(
    assignee: str, score: float, consider_skills: bool, consider_availability: bool
) -> str:
    """Generate human-readable reasoning for assignment suggestion."""
    reasons = []

    if consider_availability:
        if score > 8:
            reasons.append("has good availability")
        elif score > 5:
            reasons.append("has moderate availability")
        else:
            reasons.append("workload is manageable")

    if consider_skills:
        reasons.append("has relevant experience")

    if score > 8:
        reasons.append("shows strong overall fit")

    if not reasons:
        reasons.append("is available for assignment")

    return f"{assignee} {' and '.join(reasons)}"


def _display_assignment_suggestion(issue, suggestion: dict, suggest_only: bool):
    """Display the assignment suggestion to the user."""
    console.print(f"🎯 Smart Assignment Suggestion", style="bold blue")
    console.print(f"   📋 Issue: {issue.title}", style="cyan")
    console.print()

    confidence_style = {"high": "bold green", "medium": "yellow", "low": "red"}.get(
        suggestion["confidence"], "white"
    )

    console.print(
        f"👤 Suggested Assignee: {suggestion['assignee']}", style="bold white"
    )
    console.print(f"📊 Confidence: {suggestion['confidence']}", style=confidence_style)
    console.print(f"💡 Reasoning: {suggestion['reasoning']}", style="dim")
    console.print()


def _generate_capacity_forecast(issues: list, days: int, assignee: str = None):
    """Generate capacity forecast for the team or individual."""
    import datetime
    from collections import defaultdict

    console.print(f"📈 Capacity Forecast ({days} days)", style="bold blue")
    console.print()

    # Filter issues if assignee specified
    if assignee:
        issues = [i for i in issues if i.assignee == assignee]
        if not issues:
            console.print(f"📭 No issues assigned to {assignee}", style="dim")
            return
        console.print(f"👤 Forecast for: {assignee}", style="bold white")
    else:
        console.print("👥 Team Forecast", style="bold white")

    console.print()

    # Analyze current workload
    active_issues = [
        i
        for i in issues
        if i.status in [Status.TODO, Status.IN_PROGRESS, Status.BLOCKED]
    ]

    if not active_issues:
        console.print("✅ No active work items", style="green")
        return

    # Estimate completion dates based on current progress
    today = datetime.date.today()
    forecast_end = today + datetime.timedelta(days=days)

    # Group by estimated completion week
    weekly_forecast = defaultdict(list)
    unestimated_work = []

    for issue in active_issues:
        if issue.estimated_hours:
            # Rough estimate: assuming 6 productive hours per day
            remaining_work = issue.estimated_hours
            if issue.progress_percentage:
                remaining_work *= (100 - issue.progress_percentage) / 100

            estimated_days = remaining_work / 6
            estimated_completion = today + datetime.timedelta(days=estimated_days)

            if estimated_completion <= forecast_end:
                week_key = estimated_completion.strftime("%Y-W%U")
                weekly_forecast[week_key].append(
                    {
                        "issue": issue,
                        "estimated_completion": estimated_completion,
                        "remaining_hours": remaining_work,
                    }
                )
            else:
                weekly_forecast["beyond_forecast"].append(
                    {
                        "issue": issue,
                        "estimated_completion": estimated_completion,
                        "remaining_hours": remaining_work,
                    }
                )
        else:
            unestimated_work.append(issue)

    # Display forecast by week
    current_week = today.strftime("%Y-W%U")
    weeks = sorted([w for w in weekly_forecast.keys() if w != "beyond_forecast"])

    for week in weeks:
        week_items = weekly_forecast[week]
        total_hours = sum(item["remaining_hours"] for item in week_items)

        # Convert week back to readable format
        week_start = datetime.datetime.strptime(week + "-1", "%Y-W%U-%w").date()
        week_display = week_start.strftime("%b %d")

        style = "bold yellow" if week == current_week else "cyan"
        console.print(
            f"📅 Week of {week_display}: {len(week_items)} items ({total_hours:.1f}h)",
            style=style,
        )

        for item in week_items[:3]:  # Show top 3
            issue = item["issue"]
            completion_date = item["estimated_completion"].strftime("%m/%d")
            console.print(f"   • {issue.title} (est. {completion_date})", style="dim")

        if len(week_items) > 3:
            console.print(f"   ... and {len(week_items) - 3} more", style="dim")

        console.print()

    # Items beyond forecast period
    if "beyond_forecast" in weekly_forecast:
        beyond_items = weekly_forecast["beyond_forecast"]
        console.print(
            f"⏳ Beyond {days} days: {len(beyond_items)} items", style="yellow"
        )
        console.print()

    # Unestimated work warning
    if unestimated_work:
        console.print(
            f"⚠️  {len(unestimated_work)} items lack time estimates", style="bold red"
        )
        for issue in unestimated_work[:3]:
            console.print(f"   • {issue.title}", style="red")
        if len(unestimated_work) > 3:
            console.print(f"   ... and {len(unestimated_work) - 3} more", style="dim")
        console.print(
            "   Consider adding estimates for better forecasting", style="dim"
        )


@main.group()
def issue():
    """Manage issues."""
    pass


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

        issue = core.create_issue(
            title=title,
            priority=Priority(priority),
            issue_type=IssueType(issue_type),
            milestone=milestone,
            assignee=assignee,
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
        if git_branch and core.git.is_git_repository():
            branch_success = core.git.create_branch_for_issue(issue, checkout=checkout)
            if branch_success:
                branch_name = core.git.suggest_branch_name(issue)
                console.print(f"🌿 Created Git branch: {branch_name}", style="green")
                if checkout:
                    console.print(
                        f"✅ Checked out branch: {branch_name}", style="green"
                    )
            else:
                console.print("⚠️  Failed to create Git branch", style="yellow")
        elif git_branch:
            console.print(
                "⚠️  Not in a Git repository, skipping branch creation", style="yellow"
            )

        console.print(f"   File: .roadmap/issues/{issue.filename}", style="dim")
    except Exception as e:
        console.print(f"❌ Failed to create issue: {e}", style="bold red")


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

        # Show aggregated time summary when filtering by assignee
        if assignee or my_issues:
            # Calculate total estimated time
            total_hours = sum(issue.estimated_hours or 0 for issue in issues)
            remaining_hours = sum(
                issue.estimated_hours or 0
                for issue in issues
                if issue.status != Status.DONE
            )

            console.print()

            if total_hours > 0:
                # Format time displays
                if total_hours < 1:
                    total_display = f"{total_hours * 60:.0f}m"
                elif total_hours <= 24:
                    total_display = f"{total_hours:.1f}h"
                else:
                    total_display = f"{total_hours / 8:.1f}d"

                if remaining_hours < 1:
                    remaining_display = f"{remaining_hours * 60:.0f}m"
                elif remaining_hours <= 24:
                    remaining_display = f"{remaining_hours:.1f}h"
                else:
                    remaining_display = f"{remaining_hours / 8:.1f}d"

                assignee_name = assignee if assignee else "you"
                console.print(
                    f"⏱️  Total estimated time for {assignee_name}: {total_display}",
                    style="bold blue",
                )
                if remaining_hours != total_hours:
                    console.print(
                        f"⏳ Remaining work (excluding done): {remaining_display}",
                        style="blue",
                    )

                # Show status breakdown
                status_counts = {}
                for issue in issues:
                    status = issue.status.value
                    if status not in status_counts:
                        status_counts[status] = {"count": 0, "hours": 0}
                    status_counts[status]["count"] += 1
                    status_counts[status]["hours"] += issue.estimated_hours or 0

                console.print("📊 Workload breakdown:", style="bold")
                for status, data in status_counts.items():
                    if data["hours"] > 0:
                        if data["hours"] < 1:
                            time_display = f"{data['hours'] * 60:.0f}m"
                        elif data["hours"] <= 24:
                            time_display = f"{data['hours']:.1f}h"
                        else:
                            time_display = f"{data['hours'] / 8:.1f}d"
                        console.print(
                            f"   {status}: {data['count']} issues ({time_display})"
                        )
                    else:
                        console.print(f"   {status}: {data['count']} issues")
            else:
                assignee_name = assignee if assignee else "you"
                console.print(
                    f"ℹ️  No time estimates available for {assignee_name}'s issues",
                    style="dim",
                )
    except Exception as e:
        console.print(f"❌ Failed to list issues: {e}", style="bold red")


@issue.command("update")
@click.argument("issue_id")
@click.option(
    "--status",
    "-s",
    type=click.Choice(["todo", "in-progress", "blocked", "review", "done"]),
    help="Update status",
)
@click.option(
    "--priority",
    "-p",
    type=click.Choice(["critical", "high", "medium", "low"]),
    help="Update priority",
)
@click.option("--milestone", "-m", help="Update milestone")
@click.option("--assignee", "-a", help="Update assignee")
@click.option("--estimate", "-e", type=float, help="Update estimated time (in hours)")
@click.pass_context
def update_issue(
    ctx: click.Context,
    issue_id: str,
    status: str,
    priority: str,
    milestone: str,
    assignee: str,
    estimate: float,
):
    """Update an existing issue."""
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return

    try:
        updates = {}
        if status:
            updates["status"] = Status(status)
        if priority:
            updates["priority"] = Priority(priority)
        if milestone is not None:
            updates["milestone"] = milestone
        if assignee is not None:
            # Convert empty string to None for proper unassignment
            updates["assignee"] = assignee if assignee else None
        if estimate is not None:
            updates["estimated_hours"] = estimate

        if not updates:
            console.print(
                "❌ No updates specified. Use --status, --priority, --milestone, --assignee, or --estimate",
                style="bold red",
            )
            return

        issue = core.update_issue(issue_id, **updates)
        if not issue:
            console.print(f"❌ Issue not found: {issue_id}", style="bold red")
            return

        console.print(f"✅ Updated issue: {issue.title}", style="bold green")
        for field, value in updates.items():
            if field == "estimated_hours":
                display_value = issue.estimated_time_display
                console.print(f"   estimate: {display_value}", style="cyan")
            else:
                console.print(f"   {field}: {value}", style="cyan")
    except Exception as e:
        console.print(f"❌ Failed to update issue: {e}", style="bold red")


@issue.command("delete")
@click.argument("issue_id")
@click.confirmation_option(
    prompt="⚠️  PERMANENT DELETION: This will completely remove the issue. Consider using 'roadmap issue update --status done' instead. Are you sure?"
)
@click.pass_context
def delete_issue(ctx: click.Context, issue_id: str):
    """Delete an issue permanently.

    ⚠️  WARNING: This permanently deletes the issue. Consider marking it as 'done' instead:
    roadmap issue update ISSUE_ID --status done

    Deletion should only be used for:
    - Duplicate issues
    - Issues created by mistake
    - Issues that are no longer relevant
    """
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return

    # Show issue details before deletion
    try:
        issue = core.get_issue(issue_id)
        if issue:
            console.print(f"\n🔍 Issue to be deleted:", style="yellow")
            console.print(f"   ID: {issue.id}", style="cyan")
            console.print(f"   Title: {issue.title}", style="cyan")
            console.print(f"   Status: {issue.status.value}", style="cyan")
            console.print(f"   Priority: {issue.priority.value}", style="cyan")
            if issue.milestone:
                console.print(f"   Milestone: {issue.milestone}", style="cyan")
            console.print(
                f"\n💡 Consider: roadmap issue update {issue_id} --status done\n",
                style="green",
            )
    except:
        pass  # Continue with deletion even if we can't show details

    try:
        if core.delete_issue(issue_id):
            console.print(
                f"✅ Permanently deleted issue: {issue_id}", style="bold green"
            )
        else:
            console.print(f"❌ Issue not found: {issue_id}", style="bold red")
    except Exception as e:
        console.print(f"❌ Failed to delete issue: {e}", style="bold red")


@issue.command("close")
@click.argument("issue_id")
@click.option("--reason", help="Reason for closing the issue")
@click.pass_context
def close_issue(ctx: click.Context, issue_id: str, reason: str):
    """Close an issue by marking it as done.

    This is the recommended way to complete an issue instead of deleting it.
    Closed issues are preserved in the roadmap for historical tracking.
    """
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return

    try:
        # Get current issue details
        issue = core.get_issue(issue_id)
        if not issue:
            console.print(f"❌ Issue not found: {issue_id}", style="bold red")
            return

        # Update issue to done status
        success = core.update_issue(
            issue_id,
            status=Status.DONE,
            content=issue.content + (f"\n\n**Closed:** {reason}" if reason else ""),
        )

        if success:
            console.print(f"✅ Closed issue: {issue.title}", style="bold green")
            console.print(f"   ID: {issue_id}", style="cyan")
            console.print(f"   Status: ✅ Done", style="green")
            if reason:
                console.print(f"   Reason: {reason}", style="cyan")
            console.print(
                "\n💡 Issue preserved in roadmap for historical tracking", style="dim"
            )
        else:
            console.print(f"❌ Failed to close issue: {issue_id}", style="bold red")

    except Exception as e:
        console.print(f"❌ Failed to close issue: {e}", style="bold red")


@issue.command("block")
@click.argument("issue_id")
@click.option("--reason", help="Reason why the issue is blocked")
@click.pass_context
def block_issue(ctx: click.Context, issue_id: str, reason: str):
    """Mark an issue as blocked.

    This sets the issue status to 'blocked' and optionally records the reason.
    Blocked issues are waiting on dependencies or external factors.
    """
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return

    try:
        # Get current issue details
        issue = core.get_issue(issue_id)
        if not issue:
            console.print(f"❌ Issue not found: {issue_id}", style="bold red")
            return

        # Update issue to blocked status
        success = core.update_issue(
            issue_id,
            status=Status.BLOCKED,
            content=issue.content + (f"\n\n**Blocked:** {reason}" if reason else ""),
        )

        if success:
            console.print(f"🚫 Blocked issue: {issue.title}", style="bold yellow")
            console.print(f"   ID: {issue_id}", style="cyan")
            console.print(f"   Status: 🚫 Blocked", style="yellow")
            if reason:
                console.print(f"   Reason: {reason}", style="cyan")
            console.print(
                "\n💡 Use 'roadmap issue update --status in-progress' to unblock",
                style="dim",
            )
        else:
            console.print(f"❌ Failed to block issue: {issue_id}", style="bold red")

    except Exception as e:
        console.print(f"❌ Failed to block issue: {e}", style="bold red")


@issue.command("deps")
@click.argument("issue_id", required=False)
@click.option(
    "--show-all", is_flag=True, help="Show all dependency relationships in the project"
)
@click.pass_context
def show_dependencies(ctx: click.Context, issue_id: str, show_all: bool):
    """Show dependency relationships for an issue or the entire project.

    If ISSUE_ID is provided, shows dependencies for that specific issue.
    Use --show-all to display all dependency relationships in the project.
    """
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return

    try:
        if show_all:
            _display_all_dependencies(core)
        elif issue_id:
            _display_issue_dependencies(core, issue_id)
        else:
            console.print("❌ Specify an issue ID or use --show-all", style="bold red")
            console.print("Examples:", style="dim")
            console.print("  roadmap issue deps abc123", style="dim")
            console.print("  roadmap issue deps --show-all", style="dim")

    except Exception as e:
        console.print(f"❌ Failed to show dependencies: {e}", style="bold red")


def _display_issue_dependencies(core, issue_id: str):
    """Display dependencies for a specific issue."""
    issue = core.get_issue(issue_id)
    if not issue:
        console.print(f"❌ Issue not found: {issue_id}", style="bold red")
        return

    console.print(f"🔗 Dependencies for: {issue.title}", style="bold blue")
    console.print(f"   ID: {issue.id}", style="cyan")
    console.print()

    # Show what this issue depends on
    if issue.depends_on:
        console.print("🔒 Depends on:", style="bold yellow")
        for dep_id in issue.depends_on:
            dep_issue = core.get_issue(dep_id)
            if dep_issue:
                status_emoji = {
                    "todo": "📋",
                    "in-progress": "🔄",
                    "blocked": "🚫",
                    "review": "👀",
                    "done": "✅",
                }.get(dep_issue.status.value, "❓")
                console.print(
                    f"   {status_emoji} {dep_id}: {dep_issue.title}", style="cyan"
                )
            else:
                console.print(f"   ❌ {dep_id}: Issue not found", style="red")
    else:
        console.print("🔒 Depends on: None", style="dim")

    console.print()

    # Show what depends on this issue
    all_issues = core.list_issues()
    blocking_issues = [i for i in all_issues if issue_id in (i.depends_on or [])]

    if blocking_issues:
        console.print("🚫 Blocks:", style="bold red")
        for blocked_issue in blocking_issues:
            status_emoji = {
                "todo": "📋",
                "in-progress": "🔄",
                "blocked": "🚫",
                "review": "👀",
                "done": "✅",
            }.get(blocked_issue.status.value, "❓")
            console.print(
                f"   {status_emoji} {blocked_issue.id}: {blocked_issue.title}",
                style="cyan",
            )
    else:
        console.print("🚫 Blocks: None", style="dim")

    console.print()

    # Show what this issue blocks
    if issue.blocks:
        console.print("⛔ This issue blocks:", style="bold red")
        for blocked_id in issue.blocks:
            blocked_issue = core.get_issue(blocked_id)
            if blocked_issue:
                status_emoji = {
                    "todo": "📋",
                    "in-progress": "🔄",
                    "blocked": "🚫",
                    "review": "👀",
                    "done": "✅",
                }.get(blocked_issue.status.value, "❓")
                console.print(
                    f"   {status_emoji} {blocked_id}: {blocked_issue.title}",
                    style="cyan",
                )
            else:
                console.print(f"   ❌ {blocked_id}: Issue not found", style="red")
    else:
        console.print("⛔ This issue blocks: None", style="dim")


def _display_all_dependencies(core):
    """Display all dependency relationships in the project."""
    issues = core.list_issues()

    # Find all issues with dependencies
    issues_with_deps = [i for i in issues if i.depends_on or i.blocks]

    if not issues_with_deps:
        console.print(
            "🔗 No dependency relationships found in this project", style="dim"
        )
        console.print(
            "Create dependencies with: roadmap issue create 'Title' --depends-on ID",
            style="yellow",
        )
        return

    console.print("🔗 Project Dependency Relationships", style="bold blue")
    console.print()

    # Group by dependency chains
    dependency_chains = _build_dependency_chains(issues)

    if dependency_chains:
        console.print("📊 Dependency Chains:", style="bold")
        for i, chain in enumerate(dependency_chains, 1):
            console.print(f"\nChain {i}:", style="yellow")
            for j, issue_id in enumerate(chain):
                issue = core.get_issue(issue_id)
                if issue:
                    status_emoji = {
                        "todo": "📋",
                        "in-progress": "🔄",
                        "blocked": "🚫",
                        "review": "👀",
                        "done": "✅",
                    }.get(issue.status.value, "❓")

                    prefix = "   " + ("└─ " if j == len(chain) - 1 else "├─ ")
                    if j > 0:
                        prefix = (
                            "   "
                            + ("   " * (j - 1))
                            + ("└─ " if j == len(chain) - 1 else "├─ ")
                        )

                    console.print(
                        f"{prefix}{status_emoji} {issue_id}: {issue.title}",
                        style="cyan",
                    )

    # Show individual dependencies
    console.print(f"\n📋 Individual Dependencies:", style="bold")
    for issue in issues_with_deps:
        status_emoji = {
            "todo": "📋",
            "in-progress": "🔄",
            "blocked": "🚫",
            "review": "👀",
            "done": "✅",
        }.get(issue.status.value, "❓")

        console.print(f"\n{status_emoji} {issue.id}: {issue.title}", style="white")

        if issue.depends_on:
            console.print("   🔒 Depends on:", style="yellow")
            for dep_id in issue.depends_on:
                dep_issue = core.get_issue(dep_id)
                if dep_issue:
                    dep_status_emoji = {
                        "todo": "📋",
                        "in-progress": "🔄",
                        "blocked": "🚫",
                        "review": "👀",
                        "done": "✅",
                    }.get(dep_issue.status.value, "❓")
                    console.print(
                        f"      {dep_status_emoji} {dep_id}: {dep_issue.title}",
                        style="cyan",
                    )
                else:
                    console.print(f"      ❌ {dep_id}: Issue not found", style="red")

        if issue.blocks:
            console.print("   ⛔ Blocks:", style="red")
            for blocked_id in issue.blocks:
                blocked_issue = core.get_issue(blocked_id)
                if blocked_issue:
                    blocked_status_emoji = {
                        "todo": "📋",
                        "in-progress": "🔄",
                        "blocked": "🚫",
                        "review": "👀",
                        "done": "✅",
                    }.get(blocked_issue.status.value, "❓")
                    console.print(
                        f"      {blocked_status_emoji} {blocked_id}: {blocked_issue.title}",
                        style="cyan",
                    )
                else:
                    console.print(
                        f"      ❌ {blocked_id}: Issue not found", style="red"
                    )


def _build_dependency_chains(issues):
    """Build dependency chains from issues."""
    # Create a map of issue ID to issue for quick lookup
    issue_map = {issue.id: issue for issue in issues}

    # Find root issues (no dependencies)
    roots = []
    for issue in issues:
        if not issue.depends_on:
            roots.append(issue.id)

    # Build chains from each root
    chains = []
    visited = set()

    def build_chain(issue_id, current_chain):
        if issue_id in visited or issue_id in current_chain:
            return  # Avoid cycles

        current_chain.append(issue_id)
        issue = issue_map.get(issue_id)

        if issue and issue.blocks:
            # Find issues that depend on this one
            dependents = [i for i in issues if issue_id in (i.depends_on or [])]
            if dependents:
                for dependent in dependents:
                    build_chain(dependent.id, current_chain.copy())
            else:
                # This is a leaf in the dependency chain
                if len(current_chain) > 1:
                    chains.append(current_chain.copy())
        else:
            # This is a leaf in the dependency chain
            if len(current_chain) > 1:
                chains.append(current_chain.copy())

    for root_id in roots:
        if root_id not in visited:
            build_chain(root_id, [])

    return chains


@issue.command("start")
@click.argument("issue_id")
@click.option("--date", help="Start date (YYYY-MM-DD HH:MM, defaults to now)")
@click.pass_context
def start_issue(ctx: click.Context, issue_id: str, date: str):
    """Start work on an issue by recording the actual start date."""
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return

    try:
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
            console.print(f"   Status: In Progress", style="yellow")
        else:
            console.print(f"❌ Failed to start issue: {issue_id}", style="bold red")

    except Exception as e:
        console.print(f"❌ Failed to start issue: {e}", style="bold red")


@issue.command("complete")
@click.argument("issue_id")
@click.option("--date", help="Completion date (YYYY-MM-DD HH:MM, defaults to now)")
@click.pass_context
def complete_issue(ctx: click.Context, issue_id: str, date: str):
    """Complete work on an issue by recording the actual end date."""
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return

    try:
        # Parse completion date
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

        # Get the issue
        issue = core.get_issue(issue_id)
        if not issue:
            console.print(f"❌ Issue not found: {issue_id}", style="bold red")
            return

        # Update issue with end date and status
        success = core.update_issue(
            issue_id,
            actual_end_date=end_date,
            status=Status.DONE,
            progress_percentage=100.0,
        )

        if success:
            console.print(f"✅ Completed work on: {issue.title}", style="bold green")
            console.print(
                f"   Completed: {end_date.strftime('%Y-%m-%d %H:%M')}", style="cyan"
            )
            console.print(f"   Status: Done", style="green")

            # Show duration if we have start date
            if issue.actual_start_date:
                duration = end_date - issue.actual_start_date
                hours = duration.total_seconds() / 3600
                console.print(f"   Duration: {hours:.1f}h", style="blue")

                # Compare to estimate
                if issue.estimated_hours:
                    if hours > issue.estimated_hours:
                        over = hours - issue.estimated_hours
                        console.print(
                            f"   ⚠️  Over estimate by {over:.1f}h", style="yellow"
                        )
                    else:
                        under = issue.estimated_hours - hours
                        console.print(
                            f"   🎯 Under estimate by {under:.1f}h", style="green"
                        )
        else:
            console.print(f"❌ Failed to complete issue: {issue_id}", style="bold red")

    except Exception as e:
        console.print(f"❌ Failed to complete issue: {e}", style="bold red")


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
                        f"   Status: Auto-updated to In Progress", style="yellow"
                    )
        else:
            console.print(f"❌ Failed to update progress: {issue_id}", style="bold red")

    except Exception as e:
        console.print(f"❌ Failed to update progress: {e}", style="bold red")


@issue.command("unblock")
@click.argument("issue_id")
@click.option("--reason", help="Reason for unblocking")
@click.pass_context
def unblock_issue(ctx: click.Context, issue_id: str, reason: str):
    """Unblock an issue by setting it to in-progress status.

    This moves a blocked issue back to in-progress status.
    """
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return

    try:
        # Get current issue details
        issue = core.get_issue(issue_id)
        if not issue:
            console.print(f"❌ Issue not found: {issue_id}", style="bold red")
            return

        if issue.status != Status.BLOCKED:
            console.print(
                f"⚠️  Issue is not blocked (current status: {issue.status.value})",
                style="yellow",
            )
            return

        # Update issue to in-progress status
        success = core.update_issue(
            issue_id,
            status=Status.IN_PROGRESS,
            content=issue.content + (f"\n\n**Unblocked:** {reason}" if reason else ""),
        )

        if success:
            console.print(f"✅ Unblocked issue: {issue.title}", style="bold green")
            console.print(f"   ID: {issue_id}", style="cyan")
            console.print(f"   Status: 🔄 In Progress", style="yellow")
            if reason:
                console.print(f"   Reason: {reason}", style="cyan")
        else:
            console.print(f"❌ Failed to unblock issue: {issue_id}", style="bold red")

    except Exception as e:
        console.print(f"❌ Failed to unblock issue: {e}", style="bold red")


@issue.command("move")
@click.argument("issue_id")
@click.argument("milestone_name", required=False)
@click.pass_context
def move_issue(ctx: click.Context, issue_id: str, milestone_name: str):
    """Move an issue to a milestone or to backlog."""
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return

    try:
        # If no milestone specified, move to backlog
        if not milestone_name or milestone_name.lower() == "backlog":
            success = core.move_issue_to_milestone(issue_id, None)
            if success:
                console.print(
                    f"✅ Moved issue {issue_id} to backlog", style="bold green"
                )
            else:
                console.print(f"❌ Issue not found: {issue_id}", style="bold red")
        else:
            success = core.move_issue_to_milestone(issue_id, milestone_name)
            if success:
                console.print(
                    f"✅ Moved issue {issue_id} to milestone '{milestone_name}'",
                    style="bold green",
                )
            else:
                console.print(
                    f"❌ Failed to move. Check that issue {issue_id} and milestone '{milestone_name}' exist.",
                    style="bold red",
                )
    except Exception as e:
        console.print(f"❌ Failed to move issue: {e}", style="bold red")


@main.group()
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
            from datetime import datetime

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
                from datetime import datetime

                if ms.due_date < datetime.now() and ms.status.value == "open":
                    due_date_text = f"[bold red]{due_date_text}[/bold red]"
                elif (
                    ms.due_date - datetime.now()
                ).days <= 7 and ms.status.value == "open":
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
        if core.assign_issue_to_milestone(issue_id, milestone_name):
            console.print(
                f"✅ Assigned issue {issue_id} to milestone '{milestone_name}'",
                style="bold green",
            )
        else:
            console.print(
                f"❌ Failed to assign. Check that issue {issue_id} and milestone '{milestone_name}' exist.",
                style="bold red",
            )
    except Exception as e:
        console.print(f"❌ Failed to assign issue: {e}", style="bold red")


@main.command()
@click.pass_context
def status(ctx: click.Context) -> None:
    """Show the current status of the roadmap."""
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return

    try:
        console.print("📊 Roadmap Status", style="bold blue")

        # Get all issues and milestones
        issues = core.list_issues()
        milestones = core.list_milestones()

        if not issues and not milestones:
            console.print("\n📝 No issues or milestones found.", style="yellow")
            console.print("Get started with:")
            console.print("  roadmap issue create 'My first issue'")
            console.print("  roadmap milestone create 'My first milestone'")
            return

        # Show milestone progress
        if milestones:
            console.print("\n🎯 Milestones:", style="bold cyan")
            for ms in milestones:
                progress = core.get_milestone_progress(ms.name)
                console.print(f"\n  {ms.name}")

                if progress["total"] > 0:
                    with Progress(
                        TextColumn("[progress.description]{task.description}"),
                        BarColumn(),
                        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                        console=console,
                        transient=True,
                    ) as progress_bar:
                        task = progress_bar.add_task(
                            f"    Progress ({progress['completed']}/{progress['total']})",
                            total=progress["total"],
                            completed=progress["completed"],
                        )
                else:
                    console.print("    No issues assigned", style="dim")

        # Show issues by status
        console.print("\n📋 Issues by Status:", style="bold cyan")
        status_counts = {}
        for issue in issues:
            status_counts[issue.status] = status_counts.get(issue.status, 0) + 1

        if status_counts:
            status_table = Table(show_header=False, box=None)
            status_table.add_column("Status", style="white", width=15)
            status_table.add_column("Count", style="cyan", width=10)

            for status in Status:
                count = status_counts.get(status, 0)
                status_style = {
                    Status.TODO: "white",
                    Status.IN_PROGRESS: "yellow",
                    Status.BLOCKED: "red",
                    Status.REVIEW: "blue",
                    Status.DONE: "green",
                }.get(status, "white")

                status_table.add_row(
                    Text(f"  {status.value}", style=status_style), str(count)
                )

            console.print(status_table)
        else:
            console.print("  No issues found", style="dim")

    except Exception as e:
        console.print(f"❌ Failed to show status: {e}", style="bold red")


@milestone.command("delete")
@click.argument("milestone_name")
@click.confirmation_option(
    prompt="⚠️  PERMANENT DELETION: This will permanently delete the milestone and unassign all issues from it. Are you sure?"
)
@click.pass_context
def delete_milestone(ctx: click.Context, milestone_name: str):
    """Delete a milestone permanently and unassign all issues from it.

    ⚠️  WARNING: This permanently deletes the milestone and unassigns all issues.

    MILESTONE_NAME is the name of the milestone to delete.

    This action will:
    - Permanently delete the milestone
    - Unassign all issues from this milestone
    - Move all assigned issues back to the backlog
    """
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return

    # Show milestone details and affected issues before deletion
    try:
        milestone = core.get_milestone(milestone_name)
        if milestone:
            console.print(f"\n🔍 Milestone to be deleted:", style="yellow")
            console.print(f"   Name: {milestone.name}", style="cyan")
            console.print(f"   Status: {milestone.status.value}", style="cyan")
            if milestone.description:
                console.print(
                    f"   Description: {milestone.description[:100]}...", style="cyan"
                )

            # Show affected issues
            issues = core.list_issues(milestone=milestone_name)
            if issues:
                console.print(
                    f"\n📋 {len(issues)} issue(s) will be unassigned and moved to backlog:",
                    style="yellow",
                )
                for issue in issues[:5]:  # Show first 5 issues
                    console.print(f"   • {issue.id}: {issue.title}", style="dim")
                if len(issues) > 5:
                    console.print(
                        f"   ... and {len(issues) - 5} more issues", style="dim"
                    )
            console.print()
    except:
        pass  # Continue with deletion even if we can't show details

    try:
        if core.delete_milestone(milestone_name):
            console.print(
                f"✅ Permanently deleted milestone: {milestone_name}",
                style="bold green",
            )
            console.print(
                "📝 All assigned issues have been moved to backlog", style="green"
            )
        else:
            console.print(f"❌ Milestone not found: {milestone_name}", style="bold red")
    except Exception as e:
        console.print(f"❌ Failed to delete milestone: {e}", style="bold red")


@milestone.command("update")
@click.argument("milestone_name")
@click.option("--description", "-d", help="Update milestone description")
@click.option(
    "--due-date", help="Update due date (YYYY-MM-DD format, or 'clear' to remove)"
)
@click.option(
    "--status", type=click.Choice(["open", "closed"]), help="Update milestone status"
)
@click.pass_context
def update_milestone(
    ctx: click.Context,
    milestone_name: str,
    description: str,
    due_date: str,
    status: str,
):
    """Update milestone properties."""
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return

    try:
        milestone = core.get_milestone(milestone_name)
        if not milestone:
            console.print(f"❌ Milestone not found: {milestone_name}", style="bold red")
            return

        updates = {}

        # Handle description update
        if description is not None:
            updates["description"] = description

        # Handle due date update
        clear_due_date = False
        parsed_due_date = None

        if due_date is not None:
            if due_date.lower() == "clear":
                clear_due_date = True
            else:
                try:
                    from datetime import datetime

                    parsed_due_date = datetime.strptime(due_date, "%Y-%m-%d")
                except ValueError:
                    console.print(
                        "❌ Invalid due date format. Use YYYY-MM-DD (e.g., 2024-12-31) or 'clear'",
                        style="bold red",
                    )
                    return

        # Handle status update
        if status is not None:
            from roadmap.models import MilestoneStatus

            updates["status"] = MilestoneStatus(status)

        if not (description is not None or due_date is not None or status is not None):
            console.print(
                "❌ No updates specified. Use --description, --due-date, or --status options.",
                style="bold red",
            )
            return

        # Apply updates
        update_kwargs = {}
        if description is not None:
            update_kwargs["description"] = description
        if due_date is not None:
            update_kwargs["due_date"] = parsed_due_date
            update_kwargs["clear_due_date"] = clear_due_date
        if status is not None:
            update_kwargs["status"] = status

        if core.update_milestone(milestone_name, **update_kwargs):
            console.print(f"✅ Updated milestone: {milestone_name}", style="bold green")

            # Show what was updated
            updated_milestone = core.get_milestone(milestone_name)
            if description is not None:
                console.print(
                    f"   Description: {updated_milestone.description}", style="cyan"
                )
            if due_date is not None:
                if updated_milestone.due_date:
                    console.print(
                        f"   Due Date: {updated_milestone.due_date.strftime('%Y-%m-%d')}",
                        style="yellow",
                    )
                else:
                    console.print("   Due Date: [cleared]", style="dim")
            if status is not None:
                console.print(
                    f"   Status: {updated_milestone.status.value}", style="green"
                )
        else:
            console.print(
                f"❌ Failed to update milestone: {milestone_name}", style="bold red"
            )

    except Exception as e:
        console.print(f"❌ Failed to update milestone: {e}", style="bold red")


@main.group()
def sync():
    """Synchronize with GitHub repository."""
    pass


@sync.command("setup")
@click.option("--token", help="GitHub token for authentication")
@click.option("--repo", help="GitHub repository (owner/repo)")
@click.option(
    "--insecure",
    is_flag=True,
    help="Store token in config file (NOT RECOMMENDED - use environment variable instead)",
)
@click.pass_context
def sync_setup(ctx: click.Context, token: str, repo: str, insecure: bool):
    """Set up GitHub integration and repository labels."""
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return

    try:
        config = core.load_config()
        repo_info = {}

        # Update config with provided values
        if repo:
            if "/" in repo:
                owner, repo_name = repo.split("/", 1)
                config.github["owner"] = owner
                config.github["repo"] = repo_name
                repo_info = {"owner": owner, "repo": repo_name}
            else:
                console.print(
                    "❌ Repository must be in format 'owner/repo'", style="bold red"
                )
                return

        # Handle token storage
        config_updated = False
        if token:
            if insecure:
                # Store in config file (discouraged method)
                console.print(
                    "⚠️ WARNING: Storing token in config file is NOT RECOMMENDED!",
                    style="bold yellow",
                )
                console.print(
                    "💡 Consider using environment variable instead: export GITHUB_TOKEN='your_token'",
                    style="yellow",
                )
                config.github["token"] = token
                config_updated = True
            else:
                # Store token securely using credential manager (default behavior)
                temp_sync = SyncManager(core, config)
                success, message = temp_sync.store_token_secure(token, repo_info)

                if success:
                    console.print(f"✅ {message}", style="bold green")
                    # Don't store in config file when using secure storage
                else:
                    console.print(f"❌ {message}", style="bold red")
                    console.print(
                        "💡 Alternative: Set environment variable: export GITHUB_TOKEN='your_token'",
                        style="yellow",
                    )
                    return

        # Save updated config (only for repo info, not tokens)
        if repo or config_updated:
            config.save_to_file(core.config_file)
            if not config_updated:  # Only repo was updated
                console.print("✅ Repository configuration saved", style="bold green")

        sync_manager = SyncManager(core, config)

        # Test connection
        success, message = sync_manager.test_connection()
        if not success:
            console.print(f"❌ {message}", style="bold red")
            console.print("\nTo configure GitHub integration:", style="yellow")
            console.print(
                "1. Set environment variable: export GITHUB_TOKEN='your_token'"
            )
            console.print("2. Use secure storage: roadmap sync setup --token <token>")
            console.print("3. Update repository: roadmap sync setup --repo owner/repo")
            console.print(
                "4. Ensure token has 'repo' scope for private repos or 'public_repo' for public repos"
            )
            return

        console.print(f"✅ {message}", style="bold green")

        # Set up repository
        success, message = sync_manager.setup_repository()
        if success:
            console.print(f"✅ {message}", style="bold green")
        else:
            console.print(f"❌ {message}", style="bold red")

    except Exception as e:
        console.print(f"❌ Failed to set up GitHub integration: {e}", style="bold red")


@sync.command("test")
@click.pass_context
def sync_test(ctx: click.Context):
    """Test GitHub connection and authentication."""
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return

    try:
        config = core.load_config()
        sync_manager = SyncManager(core, config)

        success, message = sync_manager.test_connection()
        if success:
            console.print(f"✅ {message}", style="bold green")
        else:
            console.print(f"❌ {message}", style="bold red")

    except Exception as e:
        console.print(f"❌ Failed to test connection: {e}", style="bold red")


@sync.command("status")
@click.pass_context
def sync_status(ctx: click.Context):
    """Show GitHub integration status and credential information."""
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return

    try:
        config = core.load_config()
        sync_manager = SyncManager(core, config)

        console.print("GitHub Integration Status", style="bold blue")
        console.print("─" * 30)

        # Show connection status
        success, message = sync_manager.test_connection()
        if success:
            console.print(f"✅ Connection: {message}", style="green")
        else:
            console.print(f"❌ Connection: {message}", style="red")

        # Show token information
        token_info = sync_manager.get_token_info()
        console.print(f"\nToken Sources:", style="bold")

        if token_info["credential_manager_available"]:
            status = "✅" if token_info["credential_manager"] else "❌"
            console.print(
                f"  {status} Credential Manager: {'Available' if token_info['credential_manager'] else 'No token stored'}"
            )
        else:
            console.print("  ❌ Credential Manager: Not available on this system")

        status = "✅" if token_info["environment"] else "❌"
        console.print(
            f"  {status} Environment Variable (GITHUB_TOKEN): {'Set' if token_info['environment'] else 'Not set'}"
        )

        status = "✅" if token_info["config_file"] else "❌"
        console.print(
            f"  {status} Config File: {'Stored' if token_info['config_file'] else 'Not stored'}"
        )

        if token_info["active_source"]:
            console.print(
                f"\nActive Source: {token_info['active_source'].replace('_', ' ').title()}",
                style="bold green",
            )
            console.print(f"Token: {token_info['masked_token']}")
        else:
            console.print("\nNo token configured", style="bold red")

        # Show repository configuration
        github_config = config.github
        if github_config.get("owner") and github_config.get("repo"):
            console.print(
                f"\nRepository: {github_config['owner']}/{github_config['repo']}",
                style="bold",
            )
        else:
            console.print("\nRepository: Not configured", style="bold red")

    except Exception as e:
        console.print(f"❌ Failed to get sync status: {e}", style="bold red")


@sync.command("delete-token")
@click.pass_context
def sync_delete_token(ctx: click.Context):
    """Delete stored GitHub token from credential manager."""
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return

    try:
        config = core.load_config()
        sync_manager = SyncManager(core, config)

        success, message = sync_manager.delete_token_secure()
        if success:
            console.print(f"✅ {message}", style="bold green")
        else:
            console.print(f"❌ {message}", style="bold red")

    except Exception as e:
        console.print(f"❌ Failed to delete token: {e}", style="bold red")


@sync.command("push")
@click.option("--issues", is_flag=True, help="Push issues only")
@click.option("--milestones", is_flag=True, help="Push milestones only")
@click.pass_context
def sync_push(ctx: click.Context, issues: bool, milestones: bool):
    """Push local changes to GitHub."""
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return

    try:
        config = core.load_config()
        sync_manager = SyncManager(core, config)

        if not sync_manager.is_configured():
            console.print(
                "❌ GitHub integration not configured. Run 'roadmap sync setup' first.",
                style="bold red",
            )
            return

        console.print("🔄 Pushing to GitHub...", style="bold blue")

        # Determine what to sync
        sync_issues = issues or not milestones  # Default to issues if nothing specified
        sync_milestones = (
            milestones or not issues
        )  # Default to milestones if nothing specified

        total_success = 0
        total_errors = 0
        all_error_messages = []

        if sync_milestones:
            console.print("📋 Syncing milestones...", style="cyan")
            success_count, error_count, error_messages = (
                sync_manager.sync_all_milestones("push")
            )
            total_success += success_count
            total_errors += error_count
            all_error_messages.extend(error_messages)

            if success_count > 0:
                console.print(f"   ✅ {success_count} milestones synced", style="green")
            if error_count > 0:
                console.print(f"   ❌ {error_count} milestone errors", style="red")

        if sync_issues:
            console.print("🎯 Syncing issues...", style="cyan")
            success_count, error_count, error_messages = sync_manager.sync_all_issues(
                "push"
            )
            total_success += success_count
            total_errors += error_count
            all_error_messages.extend(error_messages)

            if success_count > 0:
                console.print(f"   ✅ {success_count} issues synced", style="green")
            if error_count > 0:
                console.print(f"   ❌ {error_count} issue errors", style="red")

        # Summary
        if total_success > 0:
            console.print(
                f"\n✅ Successfully synced {total_success} items to GitHub",
                style="bold green",
            )

        if total_errors > 0:
            console.print(f"\n❌ {total_errors} errors occurred:", style="bold red")
            for error in all_error_messages:
                console.print(f"   • {error}", style="red")

    except Exception as e:
        console.print(f"❌ Failed to push to GitHub: {e}", style="bold red")


@sync.command("pull")
@click.option("--issues", is_flag=True, help="Pull issues only")
@click.option("--milestones", is_flag=True, help="Pull milestones only")
@click.option(
    "--high-performance",
    is_flag=True,
    help="Use high-performance sync for large operations",
)
@click.option(
    "--batch-size",
    default=50,
    help="Batch size for high-performance sync (default: 50)",
)
@click.option(
    "--workers",
    default=8,
    help="Number of worker threads for high-performance sync (default: 8)",
)
@click.pass_context
def sync_pull(
    ctx: click.Context,
    issues: bool,
    milestones: bool,
    high_performance: bool,
    batch_size: int,
    workers: int,
):
    """Pull changes from GitHub."""
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return

    try:
        config = core.load_config()
        sync_manager = SyncManager(core, config)

        if not sync_manager.is_configured():
            console.print(
                "❌ GitHub integration not configured. Run 'roadmap sync setup' first.",
                style="bold red",
            )
            return

        # Determine what to sync
        sync_issues = issues or not milestones  # Default to issues if nothing specified
        sync_milestones = (
            milestones or not issues
        )  # Default to milestones if nothing specified

        if high_performance:
            console.print("🚀 Using high-performance sync mode...", style="bold blue")
            _sync_pull_high_performance(
                sync_manager, sync_issues, sync_milestones, batch_size, workers
            )
        else:
            console.print("🔄 Pulling from GitHub...", style="bold blue")
            _sync_pull_standard(sync_manager, sync_issues, sync_milestones)

    except Exception as e:
        console.print(f"❌ Failed to pull from GitHub: {e}", style="bold red")


def _sync_pull_high_performance(
    sync_manager: SyncManager,
    sync_issues: bool,
    sync_milestones: bool,
    batch_size: int,
    workers: int,
):
    """High-performance sync pull implementation."""

    def progress_callback(message: str):
        console.print(f"   {message}", style="cyan")

    hp_sync = HighPerformanceSyncManager(
        sync_manager=sync_manager,
        max_workers=workers,
        batch_size=batch_size,
        progress_callback=progress_callback,
    )

    total_start_time = time.time()

    if sync_milestones:
        console.print("📋 High-performance milestone sync...", style="bold cyan")
        milestone_stats = hp_sync.sync_milestones_optimized("pull")

        console.print(
            f"   ✅ {milestone_stats.milestones_created} created, "
            f"{milestone_stats.milestones_updated} updated",
            style="green",
        )

        if milestone_stats.milestones_failed > 0:
            console.print(
                f"   ❌ {milestone_stats.milestones_failed} failed", style="red"
            )

    if sync_issues:
        console.print("🎯 High-performance issue sync...", style="bold cyan")
        issue_stats = hp_sync.sync_issues_optimized("pull")

        console.print(
            f"   ✅ {issue_stats.issues_created} created, "
            f"{issue_stats.issues_updated} updated",
            style="green",
        )

        if issue_stats.issues_failed > 0:
            console.print(f"   ❌ {issue_stats.issues_failed} failed", style="red")

    # Performance report
    total_time = time.time() - total_start_time
    report = hp_sync.get_performance_report()

    console.print("\n📊 Performance Report:", style="bold yellow")
    console.print(f"   ⏱️  Total time: {total_time:.2f} seconds", style="yellow")
    console.print(
        f"   🚀 Throughput: {report['throughput_items_per_second']:.1f} items/second",
        style="yellow",
    )
    console.print(f"   📞 API calls: {report['api_calls']}", style="yellow")
    console.print(f"   💾 Disk writes: {report['disk_writes']}", style="yellow")
    console.print(f"   ✅ Success rate: {report['success_rate']:.1f}%", style="yellow")

    if hp_sync.stats.errors:
        console.print(
            f"\n❌ {len(hp_sync.stats.errors)} errors occurred:", style="bold red"
        )
        for error in hp_sync.stats.errors[:10]:  # Show first 10 errors
            console.print(f"   • {error}", style="red")
        if len(hp_sync.stats.errors) > 10:
            console.print(
                f"   ... and {len(hp_sync.stats.errors) - 10} more errors", style="red"
            )


def _sync_pull_standard(
    sync_manager: SyncManager, sync_issues: bool, sync_milestones: bool
):
    """Standard sync pull implementation."""
    total_success = 0
    total_errors = 0
    all_error_messages = []

    if sync_milestones:
        console.print("📋 Syncing milestones...", style="cyan")
        success_count, error_count, error_messages = sync_manager.sync_all_milestones(
            "pull"
        )
        total_success += success_count
        total_errors += error_count
        all_error_messages.extend(error_messages)

        if success_count > 0:
            console.print(f"   ✅ {success_count} milestones synced", style="green")
        if error_count > 0:
            console.print(f"   ❌ {error_count} milestone errors", style="red")

    if sync_issues:
        console.print("🎯 Syncing issues...", style="cyan")
        success_count, error_count, error_messages = sync_manager.sync_all_issues(
            "pull"
        )
        total_success += success_count
        total_errors += error_count
        all_error_messages.extend(error_messages)

        if success_count > 0:
            console.print(f"   ✅ {success_count} issues synced", style="green")
        if error_count > 0:
            console.print(f"   ❌ {error_count} issue errors", style="red")

    # Summary
    if total_success > 0:
        console.print(
            f"\n✅ Successfully synced {total_success} items from GitHub",
            style="bold green",
        )

    if total_errors > 0:
        console.print(f"\n❌ {total_errors} errors occurred:", style="bold red")
        for error in all_error_messages:
            console.print(f"   • {error}", style="red")


@sync.command("bidirectional")
@click.option("--issues", is_flag=True, help="Sync issues only")
@click.option("--milestones", is_flag=True, help="Sync milestones only")
@click.option(
    "--strategy",
    type=click.Choice(["local_wins", "remote_wins", "newer_wins"]),
    default="newer_wins",
    help="Conflict resolution strategy (default: newer_wins)",
)
@click.option(
    "--dry-run", is_flag=True, help="Show what would be synced without making changes"
)
@click.pass_context
def sync_bidirectional(
    ctx: click.Context, issues: bool, milestones: bool, strategy: str, dry_run: bool
):
    """Perform intelligent bidirectional synchronization between local and GitHub.

    This command compares local and remote data, detects conflicts, and resolves them
    according to the specified strategy:

    - local_wins: Always prefer local version
    - remote_wins: Always prefer remote version
    - newer_wins: Use timestamp comparison (default)
    """
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return

    try:
        config = core.load_config()

        # Convert strategy string to enum
        from roadmap.sync import SyncConflictStrategy

        strategy_map = {
            "local_wins": SyncConflictStrategy.LOCAL_WINS,
            "remote_wins": SyncConflictStrategy.REMOTE_WINS,
            "newer_wins": SyncConflictStrategy.NEWER_WINS,
        }
        conflict_strategy = strategy_map[strategy]

        sync_manager = SyncManager(core, config, conflict_strategy)

        if not sync_manager.is_configured():
            console.print(
                "❌ GitHub integration not configured. Run 'roadmap sync setup' first.",
                style="bold red",
            )
            return

        # Determine what to sync
        sync_issues = issues or not milestones  # Default to issues if nothing specified
        sync_milestones = (
            milestones or not issues
        )  # Default to milestones if nothing specified

        if dry_run:
            console.print("🔍 DRY RUN - No changes will be made", style="bold yellow")
            console.print(f"📋 Strategy: {strategy}", style="cyan")
            console.print(
                f"🎯 Syncing: {'Issues' if sync_issues else ''}{'Issues & Milestones' if sync_issues and sync_milestones else 'Milestones' if sync_milestones else ''}",
                style="cyan",
            )
            console.print(
                "\n⚠️  Dry run mode not yet implemented. Run without --dry-run to perform actual sync.",
                style="yellow",
            )
            return

        console.print("🔄 Starting bidirectional synchronization...", style="bold blue")
        console.print(f"📋 Strategy: {strategy}", style="cyan")

        success_count, error_count, error_messages, conflicts = (
            sync_manager.bidirectional_sync(
                sync_issues=sync_issues, sync_milestones=sync_milestones
            )
        )

        # Report conflicts
        if conflicts:
            console.print(
                f"\n⚠️  {len(conflicts)} conflicts detected and resolved:",
                style="bold yellow",
            )
            for conflict in conflicts:
                resolution = sync_manager.sync_strategy.resolve_conflict(conflict)
                newer = conflict.get_newer_item()
                console.print(
                    f"   • {conflict.item_type.title()} {conflict.item_id}: {resolution} (local: {conflict.local_updated.strftime('%Y-%m-%d %H:%M')}, remote: {conflict.remote_updated.strftime('%Y-%m-%d %H:%M')}, newer: {newer})",
                    style="yellow",
                )

        # Summary
        if success_count > 0:
            console.print(
                f"\n✅ Successfully synchronized {success_count} items",
                style="bold green",
            )

        if error_count > 0:
            console.print(f"\n❌ {error_count} errors occurred:", style="bold red")
            for error in error_messages:
                console.print(f"   • {error}", style="red")

        if success_count == 0 and error_count == 0:
            console.print("\n🎯 Everything is already in sync!", style="bold green")

    except Exception as e:
        console.print(f"❌ Failed to perform bidirectional sync: {e}", style="bold red")


@main.group()
def comment():
    """Manage issue comments."""
    pass


@comment.command("list")
@click.argument("issue_identifier")
@click.pass_context
def list_comments(ctx: click.Context, issue_identifier: str):
    """List all comments for an issue.

    ISSUE_IDENTIFIER can be either a local issue ID or GitHub issue number.
    """
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return

    try:
        # Try to get GitHub config
        config = core.load_config()
        github_config = config.github

        if not github_config.get("owner") or not github_config.get("repo"):
            console.print(
                "❌ GitHub repository not configured. Run 'roadmap sync setup' first.",
                style="bold red",
            )
            return

        # Initialize GitHub client
        client = GitHubClient(owner=github_config["owner"], repo=github_config["repo"])

        # Determine if it's a local issue ID or GitHub issue number
        github_issue_number = None

        if issue_identifier.isdigit():
            # It's likely a GitHub issue number
            github_issue_number = int(issue_identifier)
        else:
            # It's a local issue ID, need to find the corresponding GitHub issue
            issues = core.get_all_issues()
            local_issue = next(
                (issue for issue in issues if issue.id == issue_identifier), None
            )

            if not local_issue:
                console.print(
                    f"❌ Issue '{issue_identifier}' not found", style="bold red"
                )
                return

            if not local_issue.github_issue:
                console.print(
                    f"❌ Issue '{issue_identifier}' is not synced with GitHub",
                    style="bold red",
                )
                return

            github_issue_number = local_issue.github_issue

        # Fetch comments
        console.print(
            f"📝 Fetching comments for issue #{github_issue_number}...", style="cyan"
        )
        comments = client.get_issue_comments(github_issue_number)

        if not comments:
            console.print("📝 No comments found for this issue.", style="yellow")
            return

        # Display comments
        for i, comment in enumerate(comments, 1):
            panel_title = f"Comment {i} by {comment.author}"
            panel_subtitle = (
                f"Created: {comment.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}"
            )
            if comment.created_at != comment.updated_at:
                panel_subtitle += f" • Updated: {comment.updated_at.strftime('%Y-%m-%d %H:%M:%S UTC')}"

            panel = Panel(
                comment.body,
                title=panel_title,
                subtitle=panel_subtitle,
                border_style="cyan",
                expand=False,
            )
            console.print(panel)

            if i < len(comments):
                console.print()  # Add spacing between comments

        console.print(f"\n✅ Displayed {len(comments)} comment(s)", style="bold green")

    except Exception as e:
        console.print(f"❌ Error fetching comments: {str(e)}", style="bold red")


@comment.command("create")
@click.argument("issue_identifier")
@click.argument("comment_text")
@click.pass_context
def create_comment(ctx: click.Context, issue_identifier: str, comment_text: str):
    """Create a new comment on an issue.

    ISSUE_IDENTIFIER can be either a local issue ID or GitHub issue number.
    COMMENT_TEXT is the comment content (supports markdown).
    """
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return

    try:
        # Try to get GitHub config
        config = core.load_config()
        github_config = config.github

        if not github_config.get("owner") or not github_config.get("repo"):
            console.print(
                "❌ GitHub repository not configured. Run 'roadmap sync setup' first.",
                style="bold red",
            )
            return

        # Initialize GitHub client
        client = GitHubClient(owner=github_config["owner"], repo=github_config["repo"])

        # Determine if it's a local issue ID or GitHub issue number
        github_issue_number = None
        issue_title = f"issue #{issue_identifier}"

        if issue_identifier.isdigit():
            # It's likely a GitHub issue number
            github_issue_number = int(issue_identifier)
        else:
            # It's a local issue ID, need to find the corresponding GitHub issue
            issues = core.get_all_issues()
            local_issue = next(
                (issue for issue in issues if issue.id == issue_identifier), None
            )

            if not local_issue:
                console.print(
                    f"❌ Issue '{issue_identifier}' not found", style="bold red"
                )
                return

            if not local_issue.github_issue:
                console.print(
                    f"❌ Issue '{issue_identifier}' is not synced with GitHub",
                    style="bold red",
                )
                return

            github_issue_number = local_issue.github_issue
            issue_title = f"'{local_issue.title}'"

        # Create comment
        console.print(f"💬 Creating comment on {issue_title}...", style="cyan")
        comment = client.create_issue_comment(github_issue_number, comment_text)

        console.print(f"✅ Comment created successfully!", style="bold green")
        console.print(f"   Author: {comment.author}", style="cyan")
        console.print(
            f"   Created: {comment.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}",
            style="cyan",
        )
        console.print(f"   URL: {comment.github_url}", style="cyan")

        # Display the comment content
        panel = Panel(
            comment.body,
            title=f"New Comment by {comment.author}",
            border_style="green",
            expand=False,
        )
        console.print(panel)

    except Exception as e:
        console.print(f"❌ Error creating comment: {str(e)}", style="bold red")


@comment.command("edit")
@click.argument("comment_id", type=int)
@click.argument("new_text")
@click.pass_context
def edit_comment(ctx: click.Context, comment_id: int, new_text: str):
    """Edit an existing comment.

    COMMENT_ID is the GitHub comment ID (displayed when listing comments).
    NEW_TEXT is the updated comment content (supports markdown).
    """
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return

    try:
        # Try to get GitHub config
        config = core.load_config()
        github_config = config.github

        if not github_config.get("owner") or not github_config.get("repo"):
            console.print(
                "❌ GitHub repository not configured. Run 'roadmap sync setup' first.",
                style="bold red",
            )
            return

        # Initialize GitHub client
        client = GitHubClient(owner=github_config["owner"], repo=github_config["repo"])

        # Update comment
        console.print(f"✏️  Updating comment #{comment_id}...", style="cyan")
        comment = client.update_issue_comment(comment_id, new_text)

        console.print(f"✅ Comment updated successfully!", style="bold green")
        console.print(f"   Author: {comment.author}", style="cyan")
        console.print(
            f"   Updated: {comment.updated_at.strftime('%Y-%m-%d %H:%M:%S UTC')}",
            style="cyan",
        )
        console.print(f"   URL: {comment.github_url}", style="cyan")

        # Display the updated comment content
        panel = Panel(
            comment.body,
            title=f"Updated Comment by {comment.author}",
            border_style="yellow",
            expand=False,
        )
        console.print(panel)

    except Exception as e:
        console.print(f"❌ Error updating comment: {str(e)}", style="bold red")


@comment.command("delete")
@click.argument("comment_id", type=int)
@click.option("--force", is_flag=True, help="Skip confirmation prompt")
@click.confirmation_option(
    prompt="⚠️  PERMANENT DELETION: This will permanently delete the comment from GitHub. Are you sure?"
)
@click.pass_context
def delete_comment(ctx: click.Context, comment_id: int, force: bool):
    """Delete a comment permanently.

    ⚠️  WARNING: This permanently deletes the comment from GitHub.

    COMMENT_ID is the GitHub comment ID (displayed when listing comments).
    Use --force to skip the additional confirmation prompt.
    """
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return

    try:
        # Try to get GitHub config
        config = core.load_config()
        github_config = config.github

        if not github_config.get("owner") or not github_config.get("repo"):
            console.print(
                "❌ GitHub repository not configured. Run 'roadmap sync setup' first.",
                style="bold red",
            )
            return

        # Initialize GitHub client
        client = GitHubClient(owner=github_config["owner"], repo=github_config["repo"])

        # Delete comment
        console.print(f"🗑️  Deleting comment #{comment_id} from GitHub...", style="cyan")
        client.delete_issue_comment(comment_id)

        console.print(
            f"✅ Comment #{comment_id} permanently deleted from GitHub!",
            style="bold green",
        )

    except Exception as e:
        console.print(f"❌ Error deleting comment: {str(e)}", style="bold red")


@main.group()
def export():
    """Export project data and reports to various formats."""
    pass


@export.command("issues")
@click.option(
    "--format",
    "-f",
    type=click.Choice(["csv", "json", "markdown"]),
    default="csv",
    help="Export format",
)
@click.option(
    "--output", "-o", help="Output file path (defaults to roadmap-issues.FORMAT)"
)
@click.option(
    "--status",
    "-s",
    multiple=True,
    type=click.Choice(["todo", "in-progress", "blocked", "review", "done"]),
    help="Filter by status",
)
@click.option("--assignee", "-a", help="Filter by assignee")
@click.option("--milestone", "-m", help="Filter by milestone")
@click.option(
    "--type",
    "-t",
    multiple=True,
    type=click.Choice(["feature", "bug", "other"]),
    help="Filter by issue type",
)
@click.pass_context
def export_issues(
    ctx: click.Context,
    format: str,
    output: str,
    status: tuple,
    assignee: str,
    milestone: str,
    type: tuple,
):
    """Export issues to CSV, JSON, or Markdown format."""
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return

    try:
        # Get and filter issues
        issues = core.list_issues()

        # Apply filters
        if status:
            status_filters = [Status(s) for s in status]
            issues = [i for i in issues if i.status in status_filters]
        if assignee:
            issues = [i for i in issues if i.assignee == assignee]
        if milestone:
            issues = [i for i in issues if i.milestone == milestone]
        if type:
            type_filters = [IssueType(t) for t in type]
            issues = [i for i in issues if i.issue_type in type_filters]

        if not issues:
            console.print("📋 No issues found matching filters", style="yellow")
            return

        # Generate output filename if not provided
        if not output:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            output = f"roadmap-issues-{timestamp}.{format}"

        # Export based on format
        if format == "csv":
            _export_issues_csv(issues, output)
        elif format == "json":
            _export_issues_json(issues, output)
        elif format == "markdown":
            _export_issues_markdown(issues, output)

        console.print(
            f"✅ Exported {len(issues)} issue{'s' if len(issues) != 1 else ''} to {output}",
            style="bold green",
        )

    except Exception as e:
        console.print(f"❌ Failed to export issues: {e}", style="bold red")


@export.command("timeline")
@click.option(
    "--format",
    "-f",
    type=click.Choice(["html", "json"]),
    default="html",
    help="Export format",
)
@click.option("--output", "-o", help="Output file path")
@click.option("--assignee", "-a", help="Filter by assignee")
@click.option("--milestone", "-m", help="Filter by milestone")
@click.option("--days", "-d", type=int, default=30, help="Number of days to include")
@click.pass_context
def export_timeline(
    ctx: click.Context,
    format: str,
    output: str,
    assignee: str,
    milestone: str,
    days: int,
):
    """Export project timeline to HTML or JSON format."""
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return

    try:
        issues = core.list_issues()

        # Filter issues
        if assignee:
            issues = [i for i in issues if i.assignee == assignee]
        if milestone:
            issues = [i for i in issues if i.milestone == milestone]

        # Only show issues that aren't done
        issues = [i for i in issues if i.status != Status.DONE]

        if not issues:
            console.print("📅 No issues found for timeline export", style="yellow")
            return

        # Generate output filename if not provided
        if not output:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            output = f"roadmap-timeline-{timestamp}.{format}"

        # Calculate schedule
        schedule = _calculate_issue_schedule(issues)

        if format == "html":
            _export_timeline_html(issues, schedule, output, days)
        elif format == "json":
            _export_timeline_json(issues, schedule, output)

        console.print(f"✅ Exported timeline to {output}", style="bold green")

    except Exception as e:
        console.print(f"❌ Failed to export timeline: {e}", style="bold red")


@export.command("report")
@click.option(
    "--format",
    "-f",
    type=click.Choice(["html", "markdown", "json"]),
    default="html",
    help="Export format",
)
@click.option("--output", "-o", help="Output file path")
@click.option(
    "--type",
    "-t",
    multiple=True,
    type=click.Choice(["feature", "bug", "other"]),
    help="Filter by issue type",
)
@click.option("--milestone", "-m", help="Filter by milestone")
@click.pass_context
def export_report(
    ctx: click.Context, format: str, output: str, type: tuple, milestone: str
):
    """Export comprehensive project report."""
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return

    try:
        issues = core.list_issues()

        # Apply filters
        if type:
            type_filters = [IssueType(t) for t in type]
            issues = [i for i in issues if i.issue_type in type_filters]
        if milestone:
            issues = [i for i in issues if i.milestone == milestone]

        if not issues:
            console.print("📊 No issues found for report", style="yellow")
            return

        # Generate output filename if not provided
        if not output:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            output = f"roadmap-report-{timestamp}.{format}"

        # Export based on format
        if format == "html":
            _export_report_html(issues, output, milestone)
        elif format == "markdown":
            _export_report_markdown(issues, output, milestone)
        elif format == "json":
            _export_report_json(issues, output, milestone)

        console.print(f"✅ Exported report to {output}", style="bold green")

    except Exception as e:
        console.print(f"❌ Failed to export report: {e}", style="bold red")


def _export_issues_csv(issues, output_path):
    """Export issues to CSV format."""
    import csv

    with create_secure_file(output_path, "w", newline="", encoding="utf-8") as csvfile:
        fieldnames = [
            "id",
            "title",
            "type",
            "status",
            "priority",
            "assignee",
            "milestone",
            "estimated_hours",
            "depends_on",
            "blocks",
            "labels",
        ]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        writer.writeheader()
        for issue in issues:
            writer.writerow(
                {
                    "id": issue.id,
                    "title": issue.title,
                    "type": issue.issue_type.value,
                    "status": issue.status.value,
                    "priority": issue.priority.value,
                    "assignee": issue.assignee or "",
                    "milestone": issue.milestone or "",
                    "estimated_hours": issue.estimated_hours or "",
                    "depends_on": ",".join(issue.depends_on or []),
                    "blocks": ",".join(issue.blocks or []),
                    "labels": ",".join(issue.labels or []),
                }
            )


def _export_issues_json(issues, output_path):
    """Export issues to JSON format."""
    import json

    issues_data = []
    for issue in issues:
        issues_data.append(
            {
                "id": issue.id,
                "title": issue.title,
                "content": issue.content,
                "type": issue.issue_type.value,
                "status": issue.status.value,
                "priority": issue.priority.value,
                "assignee": issue.assignee,
                "milestone": issue.milestone,
                "estimated_hours": issue.estimated_hours,
                "depends_on": issue.depends_on or [],
                "blocks": issue.blocks or [],
                "labels": issue.labels or [],
                "created_at": (
                    issue.created_at.isoformat() if issue.created_at else None
                ),
                "updated_at": (
                    issue.updated_at.isoformat() if issue.updated_at else None
                ),
            }
        )

    with create_secure_file(output_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "export_timestamp": datetime.datetime.now().isoformat(),
                "total_issues": len(issues),
                "issues": issues_data,
            },
            f,
            indent=2,
            ensure_ascii=False,
        )


def _export_issues_markdown(issues, output_path):
    """Export issues to Markdown format."""
    with create_secure_file(output_path, "w", encoding="utf-8") as f:
        f.write("# Roadmap Issues Export\n\n")
        f.write(f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Total Issues: {len(issues)}\n\n")

        # Group by status
        status_groups = {}
        for issue in issues:
            status = issue.status.value
            if status not in status_groups:
                status_groups[status] = []
            status_groups[status].append(issue)

        for status, status_issues in status_groups.items():
            f.write(f"## {status.title()} ({len(status_issues)})\n\n")

            for issue in status_issues:
                f.write(f"### {issue.title}\n\n")
                f.write(f"- **ID:** {issue.id}\n")
                f.write(f"- **Type:** {issue.issue_type.value}\n")
                f.write(f"- **Priority:** {issue.priority.value}\n")

                if issue.assignee:
                    f.write(f"- **Assignee:** {issue.assignee}\n")
                if issue.milestone:
                    f.write(f"- **Milestone:** {issue.milestone}\n")
                if issue.estimated_hours:
                    f.write(f"- **Estimated:** {issue.estimated_hours}h\n")
                if issue.depends_on:
                    f.write(f"- **Depends on:** {', '.join(issue.depends_on)}\n")
                if issue.blocks:
                    f.write(f"- **Blocks:** {', '.join(issue.blocks)}\n")
                if issue.labels:
                    f.write(f"- **Labels:** {', '.join(issue.labels)}\n")

                if issue.content:
                    f.write(f"\n{issue.content}\n")

                f.write("\n---\n\n")


def _export_timeline_html(issues, schedule, output_path, days):
    """Export timeline to HTML format."""
    import datetime

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Roadmap Timeline</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ margin-bottom: 30px; }}
        .timeline {{ width: 100%; border-collapse: collapse; }}
        .timeline th, .timeline td {{ padding: 8px; border: 1px solid #ddd; text-align: left; }}
        .timeline th {{ background-color: #f2f2f2; }}
        .gantt-bar {{ height: 20px; position: relative; }}
        .task-bar {{ height: 100%; border-radius: 3px; }}
        .feature {{ background-color: #4CAF50; }}
        .bug {{ background-color: #f44336; }}
        .other {{ background-color: #2196F3; }}
        .task-text {{ position: absolute; left: 5px; top: 2px; font-size: 12px; color: white; }}
        .legend {{ margin-top: 20px; }}
        .legend-item {{ display: inline-block; margin-right: 20px; }}
        .legend-color {{ width: 20px; height: 20px; display: inline-block; margin-right: 5px; vertical-align: middle; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>📊 Roadmap Timeline</h1>
        <p>Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p>Total Issues: {len(issues)}</p>
    </div>
    
    <table class="timeline">
        <thead>
            <tr>
                <th>Issue</th>
                <th>Type</th>
                <th>Assignee</th>
                <th>Duration</th>
                <th>Timeline ({days} days)</th>
            </tr>
        </thead>
        <tbody>
"""

    today = datetime.date.today()

    # Sort by start date
    if schedule:
        sorted_schedule = sorted(schedule.items(), key=lambda x: x[1]["start_date"])

        for issue_id, sched in sorted_schedule:
            issue = next((i for i in issues if i.id == issue_id), None)
            if not issue:
                continue

            start_date = sched["start_date"]
            end_date = sched["end_date"]
            duration = sched["duration_days"]

            # Calculate bar position and width
            start_offset = (start_date - today).days
            bar_width = duration

            # Adjust for timeline bounds
            if start_offset < 0:
                bar_width += start_offset
                start_offset = 0
            if start_offset + bar_width > days:
                bar_width = days - start_offset

            bar_left = (start_offset / days) * 100
            bar_width_percent = (bar_width / days) * 100

            type_class = issue.issue_type.value

            html_content += f"""
            <tr>
                <td>{issue.title[:30]}{'...' if len(issue.title) > 30 else ''}</td>
                <td>{issue.issue_type.value}</td>
                <td>{issue.assignee or 'Unassigned'}</td>
                <td>{duration}d</td>
                <td>
                    <div class="gantt-bar">
                        <div class="task-bar {type_class}" style="left: {bar_left}%; width: {bar_width_percent}%;">
                            <span class="task-text">{issue.id[:8]}</span>
                        </div>
                    </div>
                </td>
            </tr>
            """

    html_content += f"""
        </tbody>
    </table>
    
    <div class="legend">
        <h3>Legend</h3>
        <div class="legend-item">
            <span class="legend-color feature"></span>Feature
        </div>
        <div class="legend-item">
            <span class="legend-color bug"></span>Bug
        </div>
        <div class="legend-item">
            <span class="legend-color other"></span>Other
        </div>
    </div>
</body>
</html>
"""

    with create_secure_file(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)


def _export_timeline_json(issues, schedule, output_path):
    """Export timeline to JSON format."""
    import json

    timeline_data = {
        "export_timestamp": datetime.datetime.now().isoformat(),
        "issues": [],
        "schedule": {},
    }

    for issue in issues:
        timeline_data["issues"].append(
            {
                "id": issue.id,
                "title": issue.title,
                "type": issue.issue_type.value,
                "status": issue.status.value,
                "priority": issue.priority.value,
                "assignee": issue.assignee,
                "estimated_hours": issue.estimated_hours,
                "depends_on": issue.depends_on or [],
                "blocks": issue.blocks or [],
            }
        )

    for issue_id, sched in schedule.items():
        timeline_data["schedule"][issue_id] = {
            "start_date": sched["start_date"].isoformat(),
            "end_date": sched["end_date"].isoformat(),
            "duration_days": sched["duration_days"],
        }

    with create_secure_file(output_path, "w", encoding="utf-8") as f:
        json.dump(timeline_data, f, indent=2, ensure_ascii=False)


def _export_report_html(issues, output_path, milestone_filter=None):
    """Export comprehensive report to HTML format."""
    # Generate analytics
    total = len(issues)

    # Status breakdown
    status_counts = {}
    for issue in issues:
        status = issue.status.value
        status_counts[status] = status_counts.get(status, 0) + 1

    # Type breakdown
    type_counts = {}
    for issue in issues:
        issue_type = issue.issue_type.value
        type_counts[issue_type] = type_counts.get(issue_type, 0) + 1

    # Assignee breakdown
    assignee_counts = {}
    unassigned = 0
    for issue in issues:
        if issue.assignee:
            assignee_counts[issue.assignee] = assignee_counts.get(issue.assignee, 0) + 1
        else:
            unassigned += 1

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Roadmap Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; line-height: 1.6; }}
        .header {{ margin-bottom: 30px; }}
        .section {{ margin-bottom: 30px; }}
        .chart {{ margin: 20px 0; }}
        .bar {{ height: 25px; background-color: #4CAF50; margin: 5px 0; position: relative; }}
        .bar-label {{ position: absolute; left: 10px; color: white; font-weight: bold; }}
        .issues-table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
        .issues-table th, .issues-table td {{ padding: 8px; border: 1px solid #ddd; text-align: left; }}
        .issues-table th {{ background-color: #f2f2f2; }}
        .status-todo {{ color: #666; }}
        .status-in-progress {{ color: #ff9800; }}
        .status-blocked {{ color: #f44336; }}
        .status-review {{ color: #2196F3; }}
        .status-done {{ color: #4CAF50; }}
        .priority-critical {{ color: #f44336; font-weight: bold; }}
        .priority-high {{ color: #ff5722; }}
        .priority-medium {{ color: #ff9800; }}
        .priority-low {{ color: #666; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>📊 Roadmap Report</h1>
        {"<h2>" + milestone_filter + "</h2>" if milestone_filter else ""}
        <p>Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p>Total Issues: {total}</p>
    </div>
    
    <div class="section">
        <h2>📋 Status Breakdown</h2>
        <div class="chart">
"""

    for status in ["todo", "in-progress", "blocked", "review", "done"]:
        count = status_counts.get(status, 0)
        if count > 0:
            percentage = (count / total) * 100
            html_content += f"""
            <div class="bar" style="width: {percentage}%;">
                <span class="bar-label">{status}: {count} ({percentage:.1f}%)</span>
            </div>
            """

    html_content += """
        </div>
    </div>
    
    <div class="section">
        <h2>🏷️ Type Breakdown</h2>
        <div class="chart">
"""

    for issue_type in ["feature", "bug", "other"]:
        count = type_counts.get(issue_type, 0)
        if count > 0:
            percentage = (count / total) * 100
            html_content += f"""
            <div class="bar" style="width: {percentage}%;">
                <span class="bar-label">{issue_type}: {count} ({percentage:.1f}%)</span>
            </div>
            """

    html_content += """
        </div>
    </div>
    
    <div class="section">
        <h2>📋 All Issues</h2>
        <table class="issues-table">
            <thead>
                <tr>
                    <th>ID</th>
                    <th>Title</th>
                    <th>Type</th>
                    <th>Status</th>
                    <th>Priority</th>
                    <th>Assignee</th>
                    <th>Estimate</th>
                </tr>
            </thead>
            <tbody>
"""

    for issue in sorted(issues, key=lambda x: (x.priority.value, x.status.value)):
        html_content += f"""
                <tr>
                    <td>{issue.id}</td>
                    <td>{issue.title}</td>
                    <td>{issue.issue_type.value}</td>
                    <td class="status-{issue.status.value}">{issue.status.value}</td>
                    <td class="priority-{issue.priority.value}">{issue.priority.value}</td>
                    <td>{issue.assignee or 'Unassigned'}</td>
                    <td>{issue.estimated_time_display if issue.estimated_hours else ''}</td>
                </tr>
        """

    html_content += """
            </tbody>
        </table>
    </div>
</body>
</html>
"""

    with create_secure_file(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)


def _export_report_markdown(issues, output_path, milestone_filter=None):
    """Export comprehensive report to Markdown format."""
    with create_secure_file(output_path, "w", encoding="utf-8") as f:
        f.write("# 📊 Roadmap Report\n\n")

        if milestone_filter:
            f.write(f"## {milestone_filter}\n\n")

        f.write(f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Total Issues: {len(issues)}\n\n")

        # Status breakdown
        status_counts = {}
        for issue in issues:
            status = issue.status.value
            status_counts[status] = status_counts.get(status, 0) + 1

        f.write("## 📋 Status Breakdown\n\n")
        for status, count in status_counts.items():
            percentage = (count / len(issues)) * 100
            f.write(f"- **{status}**: {count} ({percentage:.1f}%)\n")

        # Type breakdown
        type_counts = {}
        for issue in issues:
            issue_type = issue.issue_type.value
            type_counts[issue_type] = type_counts.get(issue_type, 0) + 1

        f.write("\n## 🏷️ Type Breakdown\n\n")
        for issue_type, count in type_counts.items():
            percentage = (count / len(issues)) * 100
            f.write(f"- **{issue_type}**: {count} ({percentage:.1f}%)\n")

        # Issues table
        f.write("\n## 📋 All Issues\n\n")
        f.write("| ID | Title | Type | Status | Priority | Assignee | Estimate |\n")
        f.write("|---|---|---|---|---|---|---|\n")

        for issue in sorted(issues, key=lambda x: (x.priority.value, x.status.value)):
            estimate = issue.estimated_time_display if issue.estimated_hours else ""
            assignee = issue.assignee or "Unassigned"
            f.write(
                f"| {issue.id} | {issue.title} | {issue.issue_type.value} | {issue.status.value} | {issue.priority.value} | {assignee} | {estimate} |\n"
            )


def _export_report_json(issues, output_path, milestone_filter=None):
    """Export comprehensive report to JSON format."""
    import json

    # Calculate analytics
    total = len(issues)

    status_counts = {}
    type_counts = {}
    priority_counts = {}
    assignee_counts = {}

    for issue in issues:
        # Status
        status = issue.status.value
        status_counts[status] = status_counts.get(status, 0) + 1

        # Type
        issue_type = issue.issue_type.value
        type_counts[issue_type] = type_counts.get(issue_type, 0) + 1

        # Priority
        priority = issue.priority.value
        priority_counts[priority] = priority_counts.get(priority, 0) + 1

        # Assignee
        if issue.assignee:
            assignee_counts[issue.assignee] = assignee_counts.get(issue.assignee, 0) + 1

    report_data = {
        "export_timestamp": datetime.datetime.now().isoformat(),
        "milestone_filter": milestone_filter,
        "summary": {
            "total_issues": total,
            "status_breakdown": status_counts,
            "type_breakdown": type_counts,
            "priority_breakdown": priority_counts,
            "assignee_breakdown": assignee_counts,
        },
        "issues": [],
    }

    for issue in issues:
        report_data["issues"].append(
            {
                "id": issue.id,
                "title": issue.title,
                "content": issue.content,
                "type": issue.issue_type.value,
                "status": issue.status.value,
                "priority": issue.priority.value,
                "assignee": issue.assignee,
                "milestone": issue.milestone,
                "estimated_hours": issue.estimated_hours,
                "depends_on": issue.depends_on or [],
                "blocks": issue.blocks or [],
                "labels": issue.labels or [],
            }
        )

    with create_secure_file(output_path, "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2, ensure_ascii=False)


# Team collaboration commands
@main.group()
def team():
    """Team collaboration commands."""
    pass


@team.command("members")
@click.pass_context
def list_team_members(ctx: click.Context):
    """List all team members from the GitHub repository."""
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return

    try:
        team_members = core.get_team_members()
        current_user = core.get_current_user()

        if not team_members:
            console.print("👥 No team members found.", style="yellow")
            console.print(
                "Make sure GitHub integration is set up: roadmap sync setup",
                style="dim",
            )
            return

        console.print(
            f"👥 {len(team_members)} team member{'s' if len(team_members) != 1 else ''}",
            style="bold cyan",
        )
        console.print()

        for member in team_members:
            if member == current_user:
                console.print(f"  👤 {member} (you)", style="bold magenta")
            else:
                console.print(f"  👤 {member}", style="white")

    except Exception as e:
        console.print(f"❌ Failed to get team members: {e}", style="bold red")


@team.command("assignments")
@click.pass_context
def show_team_assignments(ctx: click.Context):
    """Show issue assignments for all team members."""
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return

    try:
        assigned_issues = core.get_all_assigned_issues()

        if not assigned_issues:
            console.print("📋 No assigned issues found.", style="yellow")
            console.print(
                "Create issues with: roadmap issue create 'Title' --assignee username",
                style="dim",
            )
            return

        console.print("📋 Team Issue Assignments", style="bold cyan")
        console.print()

        for assignee, issues in assigned_issues.items():
            console.print(
                f"👤 {assignee} ({len(issues)} issue{'s' if len(issues) != 1 else ''})",
                style="bold magenta",
            )

            for issue in issues:
                status_style = {
                    Status.TODO: "white",
                    Status.IN_PROGRESS: "yellow",
                    Status.BLOCKED: "red",
                    Status.REVIEW: "blue",
                    Status.DONE: "green",
                }.get(issue.status, "white")

                console.print(
                    f"  📝 {issue.id}: {issue.title} [{issue.status.value}]",
                    style=status_style,
                )
            console.print()

    except Exception as e:
        console.print(f"❌ Failed to show assignments: {e}", style="bold red")


@team.command("workload")
@click.pass_context
def show_team_workload(ctx: click.Context):
    """Show workload summary for all team members."""
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return

    try:
        assigned_issues = core.get_all_assigned_issues()
        team_members = core.get_team_members()

        console.print("📊 Team Workload Summary", style="bold cyan")
        console.print()

        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Team Member", style="white")
        table.add_column("Total", style="cyan", width=8)
        table.add_column("Todo", style="white", width=8)
        table.add_column("In Progress", style="yellow", width=12)
        table.add_column("Blocked", style="red", width=8)
        table.add_column("Review", style="blue", width=8)
        table.add_column("Done", style="green", width=8)
        table.add_column("Est. Time", style="green", width=10)

        for member in team_members:
            issues = assigned_issues.get(member, [])

            # Count by status
            status_counts = {status: 0 for status in Status}
            for issue in issues:
                status_counts[issue.status] += 1

            # Calculate total estimated time for remaining work
            remaining_hours = sum(
                issue.estimated_hours or 0
                for issue in issues
                if issue.status != Status.DONE and issue.estimated_hours is not None
            )

            # Format estimated time display
            if remaining_hours == 0:
                time_display = "-"
            elif remaining_hours < 8:
                time_display = f"{remaining_hours:.1f}h"
            else:
                days = remaining_hours / 8
                time_display = f"{days:.1f}d"

            table.add_row(
                member,
                str(len(issues)),
                str(status_counts[Status.TODO]),
                str(status_counts[Status.IN_PROGRESS]),
                str(status_counts[Status.BLOCKED]),
                str(status_counts[Status.REVIEW]),
                str(status_counts[Status.DONE]),
                time_display,
            )

        console.print(table)

        # Show unassigned issues count with estimated time
        all_issues = core.list_issues()
        unassigned = [i for i in all_issues if not i.assignee]
        if unassigned:
            unassigned_hours = sum(
                issue.estimated_hours or 0
                for issue in unassigned
                if issue.estimated_hours is not None
            )

            time_info = ""
            if unassigned_hours > 0:
                if unassigned_hours < 8:
                    time_info = f" ({unassigned_hours:.1f}h estimated)"
                else:
                    days = unassigned_hours / 8
                    time_info = f" ({days:.1f}d estimated)"

            console.print()
            console.print(
                f"📋 {len(unassigned)} unassigned issue{'s' if len(unassigned) != 1 else ''}{time_info}",
                style="yellow",
            )

    except Exception as e:
        console.print(f"❌ Failed to show workload: {e}", style="bold red")


# Enhanced reporting commands
@main.group()
def report():
    """Generate detailed reports and analytics."""
    pass


@main.group()
def timeline():
    """Generate project timelines and Gantt charts."""
    pass


@timeline.command("show")
@click.option("--assignee", "-a", help="Filter by assignee")
@click.option("--milestone", "-m", help="Filter by milestone")
@click.option(
    "--format",
    "-f",
    type=click.Choice(["text", "gantt"]),
    default="text",
    help="Output format",
)
@click.option(
    "--days",
    "-d",
    type=int,
    default=30,
    help="Number of days to show in timeline (default: 30)",
)
@click.pass_context
def show_timeline(
    ctx: click.Context, assignee: str, milestone: str, format: str, days: int
):
    """Show project timeline with dependencies and estimated completion dates.

    The timeline shows issues ordered by dependencies and estimates completion
    dates based on estimated hours and working days.
    """
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return

    try:
        issues = core.list_issues()

        # Filter issues
        if assignee:
            issues = [i for i in issues if i.assignee == assignee]
        if milestone:
            issues = [i for i in issues if i.milestone == milestone]

        # Only show issues that aren't done
        issues = [i for i in issues if i.status != Status.DONE]

        if not issues:
            console.print("📅 No issues found for timeline", style="dim")
            return

        if format == "gantt":
            _display_gantt_chart(issues, days)
        else:
            _display_text_timeline(issues, days)

    except Exception as e:
        console.print(f"❌ Failed to show timeline: {e}", style="bold red")


@timeline.command("critical-path")
@click.option("--milestone", "-m", help="Filter by milestone")
@click.pass_context
def critical_path(ctx: click.Context, milestone: str):
    """Show the critical path through the project dependencies.

    The critical path is the longest sequence of dependent tasks that
    determines the minimum project completion time.
    """
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return

    try:
        issues = core.list_issues()

        if milestone:
            issues = [i for i in issues if i.milestone == milestone]

        # Only consider issues that aren't done
        issues = [i for i in issues if i.status != Status.DONE]

        if not issues:
            console.print("📅 No issues found for critical path analysis", style="dim")
            return

        critical_paths = _calculate_critical_path(issues)
        _display_critical_path(critical_paths, core)

    except Exception as e:
        console.print(f"❌ Failed to calculate critical path: {e}", style="bold red")


def _display_text_timeline(issues, days):
    """Display a text-based timeline."""
    import datetime

    console.print("📅 Project Timeline", style="bold blue")
    console.print()

    # Calculate start dates based on dependencies
    issue_schedule = _calculate_issue_schedule(issues)

    if not issue_schedule:
        console.print("📅 No issues with estimates found for timeline", style="dim")
        console.print(
            "Add estimates with: roadmap issue update ISSUE_ID --estimate HOURS",
            style="yellow",
        )
        return

    # Sort by start date
    sorted_schedule = sorted(issue_schedule.items(), key=lambda x: x[1]["start_date"])

    # Display timeline
    today = datetime.date.today()

    console.print(f"📊 Timeline (starting {today}):", style="bold")
    console.print()

    for issue_id, schedule in sorted_schedule:
        issue = next((i for i in issues if i.id == issue_id), None)
        if not issue:
            continue

        start_date = schedule["start_date"]
        end_date = schedule["end_date"]
        duration = schedule["duration_days"]

        # Calculate days from today
        days_from_today = (start_date - today).days

        status_emoji = {
            "todo": "📋",
            "in-progress": "🔄",
            "blocked": "🚫",
            "review": "👀",
        }.get(issue.status.value, "❓")

        type_emoji = {"feature": "✨", "bug": "🐛", "other": "📝"}.get(
            issue.issue_type.value, "❓"
        )

        # Format dates and timing
        if days_from_today <= 0:
            timing = (
                "Starting now"
                if days_from_today == 0
                else f"Started {abs(days_from_today)}d ago"
            )
            timing_style = "green" if days_from_today == 0 else "yellow"
        else:
            timing = f"Starts in {days_from_today}d"
            timing_style = "cyan"

        console.print(
            f"{status_emoji} {type_emoji} {issue.id}: {issue.title}", style="white"
        )

        # Show if dates are actual or projected
        date_type = "Actual" if schedule.get("is_actual", False) else "Projected"
        date_style = "green" if schedule.get("is_actual", False) else "cyan"

        console.print(
            f"   📅 {start_date} → {end_date} ({duration}d) [{date_type}]",
            style=date_style,
        )
        console.print(f"   ⏰ {timing}", style=timing_style)

        # Show progress if available
        if issue.progress_percentage is not None:
            console.print(f"   📊 Progress: {issue.progress_display}", style="blue")

        if issue.assignee:
            console.print(f"   👤 {issue.assignee}", style="magenta")

        if issue.depends_on:
            console.print(
                f"   🔒 Depends on: {', '.join(issue.depends_on)}", style="yellow"
            )

        # Show actual vs estimated if completed
        if issue.actual_end_date and issue.estimated_hours:
            actual_hours = issue.actual_duration_hours
            if actual_hours:
                if actual_hours > issue.estimated_hours:
                    over = actual_hours - issue.estimated_hours
                    console.print(f"   ⚠️  Over estimate by {over:.1f}h", style="yellow")
                else:
                    under = issue.estimated_hours - actual_hours
                    console.print(
                        f"   🎯 Under estimate by {under:.1f}h", style="green"
                    )

        console.print()


def _display_gantt_chart(issues, days):
    """Display a simple text-based Gantt chart."""
    import datetime

    console.print("📊 Gantt Chart", style="bold blue")
    console.print()

    # Calculate schedule
    issue_schedule = _calculate_issue_schedule(issues)

    if not issue_schedule:
        console.print("📅 No issues with estimates found for Gantt chart", style="dim")
        return

    # Determine timeline bounds
    today = datetime.date.today()
    end_date = today + datetime.timedelta(days=days)

    # Create date header
    console.print("Issue ID    │ Title                 │ Timeline")
    console.print("────────────┼───────────────────────┼" + "─" * days)

    # Sort by start date
    sorted_schedule = sorted(issue_schedule.items(), key=lambda x: x[1]["start_date"])

    for issue_id, schedule in sorted_schedule:
        issue = next((i for i in issues if i.id == issue_id), None)
        if not issue:
            continue

        start_date = schedule["start_date"]
        issue_end_date = schedule["end_date"]

        # Create timeline bar
        timeline_bar = _create_timeline_bar(start_date, issue_end_date, today, days)

        # Truncate title if needed
        title = (
            issue.title[:20] + "..." if len(issue.title) > 23 else issue.title.ljust(23)
        )

        console.print(f"{issue_id[:11]} │ {title} │ {timeline_bar}")

    # Add date legend
    console.print("────────────┼───────────────────────┼" + "─" * days)

    # Show week markers
    week_markers = ""
    for i in range(0, days, 7):
        marker_date = today + datetime.timedelta(days=i)
        if i == 0:
            week_markers += f"{marker_date.strftime('%m/%d')}"
        else:
            week_markers += " " * (
                7 - len(marker_date.strftime("%m/%d"))
            ) + marker_date.strftime("%m/%d")

    console.print(f"{'Date':11} │ {'Week markers':23} │ {week_markers}")


def _create_timeline_bar(start_date, end_date, today, total_days):
    """Create a text timeline bar for Gantt chart."""
    import datetime

    bar = ""

    for day in range(total_days):
        current_date = today + datetime.timedelta(days=day)

        if start_date <= current_date <= end_date:
            if current_date == start_date:
                bar += "◄"  # Start marker
            elif current_date == end_date:
                bar += "►"  # End marker
            else:
                bar += "━"  # Progress bar
        elif current_date == today:
            bar += "│"  # Today marker
        else:
            bar += " "  # Empty space

    return bar


def _calculate_issue_schedule(issues):
    """Calculate start and end dates for issues based on dependencies, estimates, and actual dates."""
    import datetime

    # Only consider issues with estimates or actual dates
    trackable_issues = [i for i in issues if i.estimated_hours or i.actual_start_date]

    if not trackable_issues:
        return {}

    # Build dependency graph
    issue_map = {issue.id: issue for issue in trackable_issues}

    # Calculate schedule using topological sort
    schedule = {}
    today = datetime.date.today()

    # Handle issues with actual dates first
    for issue in trackable_issues:
        if issue.actual_start_date or issue.actual_end_date:
            start_date = (
                issue.actual_start_date.date() if issue.actual_start_date else today
            )

            if issue.actual_end_date:
                # Issue is completed - use actual dates
                end_date = issue.actual_end_date.date()
            elif issue.estimated_hours:
                # Issue started but not finished - project end date
                duration_days = max(1, int((issue.estimated_hours + 7) / 8))
                end_date = _add_workdays(start_date, duration_days - 1)
            else:
                # No estimate, assume 1 day
                end_date = start_date

            schedule[issue.id] = {
                "start_date": start_date,
                "end_date": end_date,
                "duration_days": (end_date - start_date).days + 1,
                "is_actual": True,
            }

    # Now handle estimated issues (not yet started)
    estimated_issues = [
        i for i in trackable_issues if i.id not in schedule and i.estimated_hours
    ]

    # Start with issues that have no dependencies
    ready_issues = [i for i in estimated_issues if not i.depends_on]
    scheduled = set(schedule.keys())

    current_date = today

    while ready_issues or len(scheduled) < len(trackable_issues):
        if not ready_issues:
            # If no ready issues, pick the next unscheduled issue
            unscheduled = [i for i in estimated_issues if i.id not in scheduled]
            if unscheduled:
                ready_issues = [unscheduled[0]]
            else:
                break

        # Schedule the next ready issue
        issue = ready_issues.pop(0)

        if issue.id in scheduled:
            continue

        # Calculate duration in work days (assuming 8 hour work days)
        duration_days = max(1, int((issue.estimated_hours + 7) / 8))  # Round up

        # Find the latest dependency end date
        dep_end_date = current_date
        if issue.depends_on:
            for dep_id in issue.depends_on:
                if dep_id in schedule:
                    dep_end = schedule[dep_id]["end_date"]
                    if dep_end > dep_end_date:
                        dep_end_date = dep_end

        # Skip weekends for start date
        start_date = _next_workday(dep_end_date)
        end_date = _add_workdays(start_date, duration_days - 1)

        schedule[issue.id] = {
            "start_date": start_date,
            "end_date": end_date,
            "duration_days": duration_days,
            "is_actual": False,
        }

        scheduled.add(issue.id)

        # Check if any new issues are now ready
        for other_issue in estimated_issues:
            if (
                other_issue.id not in scheduled
                and other_issue not in ready_issues
                and other_issue.depends_on
                and all(dep_id in scheduled for dep_id in other_issue.depends_on)
            ):
                ready_issues.append(other_issue)

    return schedule


def _next_workday(date):
    """Get the next workday (Monday-Friday)."""
    import datetime

    # If it's a weekend, move to Monday
    if date.weekday() >= 5:  # Saturday = 5, Sunday = 6
        days_to_monday = 7 - date.weekday()
        return date + datetime.timedelta(days=days_to_monday)
    return date


def _add_workdays(start_date, workdays):
    """Add workdays to a date, skipping weekends."""
    import datetime

    current_date = start_date
    days_added = 0

    while days_added < workdays:
        current_date += datetime.timedelta(days=1)
        # Only count weekdays
        if current_date.weekday() < 5:
            days_added += 1

    return current_date


def _calculate_critical_path(issues):
    """Calculate the critical path through project dependencies."""
    # Build dependency graph
    issue_map = {issue.id: issue for issue in issues}

    # Find all paths through the dependency graph
    paths = []

    # Start from issues with no dependencies
    root_issues = [i for i in issues if not i.depends_on]

    def find_paths(issue_id, current_path, total_time):
        current_path.append(issue_id)
        issue = issue_map.get(issue_id)

        if issue and issue.estimated_hours:
            total_time += issue.estimated_hours

        # Find issues that depend on this one
        dependents = [i for i in issues if issue_id in (i.depends_on or [])]

        if not dependents:
            # This is a leaf node, record the path
            paths.append((current_path.copy(), total_time))
        else:
            # Continue exploring dependent paths
            for dependent in dependents:
                find_paths(dependent.id, current_path.copy(), total_time)

    # Build all paths
    for root in root_issues:
        find_paths(root.id, [], 0)

    # Find the longest path(s) by time
    if not paths:
        return []

    max_time = max(path[1] for path in paths)
    critical_paths = [path for path in paths if path[1] == max_time]

    return critical_paths


def _display_critical_path(critical_paths, core):
    """Display the critical path analysis."""
    if not critical_paths:
        console.print(
            "📅 No critical path found - no connected dependencies", style="dim"
        )
        return

    console.print("🔥 Critical Path Analysis", style="bold red")
    console.print()

    for i, (path, total_time) in enumerate(critical_paths, 1):
        if len(critical_paths) > 1:
            console.print(f"Critical Path {i}:", style="bold yellow")

        console.print(
            f"Total Duration: {total_time:.1f} hours ({total_time/8:.1f} days)",
            style="bold green",
        )
        console.print()

        for j, issue_id in enumerate(path):
            issue = core.get_issue(issue_id)
            if issue:
                status_emoji = {
                    "todo": "📋",
                    "in-progress": "🔄",
                    "blocked": "🚫",
                    "review": "👀",
                }.get(issue.status.value, "❓")

                type_emoji = {"feature": "✨", "bug": "🐛", "other": "📝"}.get(
                    issue.issue_type.value, "❓"
                )

                connector = "└─ " if j == len(path) - 1 else "├─ "
                if j > 0:
                    connector = "   " + connector

                estimate_str = (
                    f" ({issue.estimated_hours}h)"
                    if issue.estimated_hours
                    else " (no estimate)"
                )

                console.print(
                    f"{connector}{status_emoji} {type_emoji} {issue_id}: {issue.title}{estimate_str}",
                    style="cyan",
                )

                if issue.assignee:
                    prefix = "   " if j == len(path) - 1 else "│  "
                    console.print(f"{prefix}   👤 {issue.assignee}", style="dim")

        console.print()


@report.command("assignee")
@click.argument("assignee", required=False)
@click.option(
    "--status",
    "-s",
    multiple=True,
    type=click.Choice(["todo", "in-progress", "blocked", "review", "done"]),
    help="Filter by status (can be used multiple times)",
)
@click.option(
    "--type",
    "-t",
    multiple=True,
    type=click.Choice(["feature", "bug", "other"]),
    help="Filter by issue type (can be used multiple times)",
)
@click.option(
    "--priority",
    "-p",
    multiple=True,
    type=click.Choice(["critical", "high", "medium", "low"]),
    help="Filter by priority (can be used multiple times)",
)
@click.option("--milestone", "-m", help="Filter by milestone")
@click.option(
    "--format",
    "-f",
    type=click.Choice(["table", "list", "summary"]),
    default="table",
    help="Output format",
)
@click.pass_context
def assignee_report(
    ctx: click.Context,
    assignee: str,
    status: tuple,
    type: tuple,
    priority: tuple,
    milestone: str,
    format: str,
):
    """Generate detailed report for a specific assignee or all assignees.

    If no assignee is specified, shows reports for all team members.
    """
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return

    try:
        # Build filters
        filters = {}
        if status:
            filters["status"] = [Status(s) for s in status]
        if type:
            filters["issue_type"] = [IssueType(t) for t in type]
        if priority:
            filters["priority"] = [Priority(p) for p in priority]
        if milestone:
            filters["milestone"] = milestone

        issues = core.list_issues()

        # Apply filters
        filtered_issues = []
        for issue in issues:
            if filters.get("status") and issue.status not in filters["status"]:
                continue
            if (
                filters.get("issue_type")
                and issue.issue_type not in filters["issue_type"]
            ):
                continue
            if filters.get("priority") and issue.priority not in filters["priority"]:
                continue
            if filters.get("milestone") and issue.milestone != filters["milestone"]:
                continue
            filtered_issues.append(issue)

        if assignee:
            # Single assignee report
            assignee_issues = [i for i in filtered_issues if i.assignee == assignee]
            _display_assignee_report(assignee, assignee_issues, format)
        else:
            # All assignees report
            assignees = {}
            unassigned = []

            for issue in filtered_issues:
                if issue.assignee:
                    if issue.assignee not in assignees:
                        assignees[issue.assignee] = []
                    assignees[issue.assignee].append(issue)
                else:
                    unassigned.append(issue)

            # Display each assignee's report
            for assignee_name in sorted(assignees.keys()):
                _display_assignee_report(
                    assignee_name, assignees[assignee_name], format
                )
                console.print()  # Add spacing between assignees

            # Display unassigned issues
            if unassigned:
                _display_assignee_report("Unassigned", unassigned, format)

    except Exception as e:
        console.print(f"❌ Failed to generate assignee report: {e}", style="bold red")


@report.command("summary")
@click.option(
    "--type",
    "-t",
    multiple=True,
    type=click.Choice(["feature", "bug", "other"]),
    help="Filter by issue type (can be used multiple times)",
)
@click.option("--milestone", "-m", help="Filter by milestone")
@click.pass_context
def summary_report(ctx: click.Context, type: tuple, milestone: str):
    """Generate a comprehensive summary report with analytics."""
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return

    try:
        issues = core.list_issues()

        # Apply filters
        if type:
            type_filters = [IssueType(t) for t in type]
            issues = [i for i in issues if i.issue_type in type_filters]
        if milestone:
            issues = [i for i in issues if i.milestone == milestone]

        _display_summary_analytics(issues, milestone)

    except Exception as e:
        console.print(f"❌ Failed to generate summary report: {e}", style="bold red")


def _display_assignee_report(assignee_name: str, issues: list, format: str):
    """Display report for a specific assignee."""
    if not issues:
        console.print(f"📋 {assignee_name}: No issues found", style="dim")
        return

    # Calculate statistics
    total = len(issues)
    by_status = {}
    by_type = {}
    by_priority = {}
    total_estimated = 0

    for issue in issues:
        # Status breakdown
        status_key = issue.status.value
        by_status[status_key] = by_status.get(status_key, 0) + 1

        # Type breakdown
        type_key = issue.issue_type.value
        by_type[type_key] = by_type.get(type_key, 0) + 1

        # Priority breakdown
        priority_key = issue.priority.value
        by_priority[priority_key] = by_priority.get(priority_key, 0) + 1

        # Time estimates
        if issue.estimated_hours:
            total_estimated += issue.estimated_hours

    # Header
    console.print(
        f"👤 {assignee_name} ({total} issue{'s' if total != 1 else ''})",
        style="bold blue",
    )

    if format == "summary":
        # Compact summary format
        status_summary = ", ".join([f"{k}: {v}" for k, v in by_status.items()])
        console.print(f"   Status: {status_summary}", style="cyan")

        type_summary = ", ".join([f"{k}: {v}" for k, v in by_type.items()])
        console.print(f"   Types: {type_summary}", style="cyan")

        if total_estimated > 0:
            if total_estimated >= 8:
                days = total_estimated / 8
                console.print(
                    f"   Estimated: {total_estimated:.1f}h ({days:.1f}d)", style="cyan"
                )
            else:
                console.print(f"   Estimated: {total_estimated:.1f}h", style="cyan")

    elif format == "table":
        # Detailed table format
        table = Table(title=f"{assignee_name}'s Issues")
        table.add_column("ID", style="cyan", no_wrap=True)
        table.add_column("Type", style="blue")
        table.add_column("Title")
        table.add_column("Status", style="yellow")
        table.add_column("Priority", style="magenta")
        table.add_column("Est.", style="green")

        for issue in sorted(issues, key=lambda x: (x.priority.value, x.status.value)):
            status_emoji = {
                "todo": "📋",
                "in-progress": "🔄",
                "blocked": "🚫",
                "review": "👀",
                "done": "✅",
            }.get(issue.status.value, "❓")

            type_emoji = {"feature": "✨", "bug": "🐛", "other": "📝"}.get(
                issue.issue_type.value, "❓"
            )

            estimate_str = issue.estimated_time_display if issue.estimated_hours else ""

            table.add_row(
                issue.id,
                f"{type_emoji} {issue.issue_type.value}",
                issue.title,
                f"{status_emoji} {issue.status.value}",
                issue.priority.value,
                estimate_str,
            )

        console.print(table)

        # Summary statistics
        console.print("\n📊 Statistics:", style="bold")
        for status, count in by_status.items():
            console.print(f"   {status}: {count}", style="cyan")

        if total_estimated > 0:
            if total_estimated >= 8:
                days = total_estimated / 8
                console.print(
                    f"   Total estimated: {total_estimated:.1f}h ({days:.1f}d)",
                    style="green",
                )
            else:
                console.print(
                    f"   Total estimated: {total_estimated:.1f}h", style="green"
                )

    elif format == "list":
        # Simple list format
        for issue in sorted(issues, key=lambda x: (x.priority.value, x.status.value)):
            status_emoji = {
                "todo": "📋",
                "in-progress": "🔄",
                "blocked": "🚫",
                "review": "👀",
                "done": "✅",
            }.get(issue.status.value, "❓")

            type_emoji = {"feature": "✨", "bug": "🐛", "other": "📝"}.get(
                issue.issue_type.value, "❓"
            )

            console.print(
                f"   {status_emoji} {type_emoji} {issue.id}: {issue.title}",
                style="cyan",
            )


def _display_summary_analytics(issues: list, milestone_filter: str = None):
    """Display comprehensive analytics summary."""
    if not issues:
        console.print("📊 No issues found for analysis", style="dim")
        return

    title = "📊 Project Summary"
    if milestone_filter:
        title += f" - {milestone_filter}"

    console.print(title, style="bold blue")
    console.print()

    # Overall statistics
    total = len(issues)
    console.print(f"Total Issues: {total}", style="bold")

    # Status breakdown
    status_counts = {}
    for issue in issues:
        status = issue.status.value
        status_counts[status] = status_counts.get(status, 0) + 1

    console.print("\n📋 Status Breakdown:", style="bold")
    for status in ["todo", "in-progress", "blocked", "review", "done"]:
        count = status_counts.get(status, 0)
        if count > 0:
            percentage = (count / total) * 100
            emoji = {
                "todo": "📋",
                "in-progress": "🔄",
                "blocked": "🚫",
                "review": "👀",
                "done": "✅",
            }.get(status, "❓")
            console.print(
                f"   {emoji} {status}: {count} ({percentage:.1f}%)", style="cyan"
            )

    # Type breakdown
    type_counts = {}
    for issue in issues:
        issue_type = issue.issue_type.value
        type_counts[issue_type] = type_counts.get(issue_type, 0) + 1

    console.print("\n🏷️  Type Breakdown:", style="bold")
    for issue_type in ["feature", "bug", "other"]:
        count = type_counts.get(issue_type, 0)
        if count > 0:
            percentage = (count / total) * 100
            emoji = {"feature": "✨", "bug": "🐛", "other": "📝"}.get(issue_type, "❓")
            console.print(
                f"   {emoji} {issue_type}: {count} ({percentage:.1f}%)", style="blue"
            )

    # Priority breakdown
    priority_counts = {}
    for issue in issues:
        priority = issue.priority.value
        priority_counts[priority] = priority_counts.get(priority, 0) + 1

    console.print("\n⚡ Priority Breakdown:", style="bold")
    for priority in ["critical", "high", "medium", "low"]:
        count = priority_counts.get(priority, 0)
        if count > 0:
            percentage = (count / total) * 100
            console.print(
                f"   {priority}: {count} ({percentage:.1f}%)", style="magenta"
            )

    # Assignee breakdown
    assignee_counts = {}
    unassigned = 0
    for issue in issues:
        if issue.assignee:
            assignee_counts[issue.assignee] = assignee_counts.get(issue.assignee, 0) + 1
        else:
            unassigned += 1

    console.print("\n👥 Assignee Breakdown:", style="bold")
    for assignee in sorted(assignee_counts.keys()):
        count = assignee_counts[assignee]
        percentage = (count / total) * 100
        console.print(f"   {assignee}: {count} ({percentage:.1f}%)", style="yellow")

    if unassigned > 0:
        percentage = (unassigned / total) * 100
        console.print(f"   Unassigned: {unassigned} ({percentage:.1f}%)", style="dim")

    # Time estimates
    total_estimated = sum(
        issue.estimated_hours for issue in issues if issue.estimated_hours
    )
    estimated_count = len([i for i in issues if i.estimated_hours])

    if total_estimated > 0:
        console.print("\n⏱️  Time Estimates:", style="bold")
        console.print(
            f"   Issues with estimates: {estimated_count}/{total} ({(estimated_count/total)*100:.1f}%)",
            style="green",
        )

        if total_estimated >= 8:
            days = total_estimated / 8
            console.print(
                f"   Total estimated: {total_estimated:.1f}h ({days:.1f}d)",
                style="green",
            )
        else:
            console.print(f"   Total estimated: {total_estimated:.1f}h", style="green")

        avg_estimate = total_estimated / estimated_count
        console.print(f"   Average estimate: {avg_estimate:.1f}h", style="green")


# Git Integration Commands


@main.command()
@click.pass_context
def git_status(ctx: click.Context):
    """Show Git repository status and roadmap integration info."""
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return

    try:
        git_context = core.get_git_context()

        if not git_context.get("is_git_repo", False):
            console.print("📁 Not in a Git repository", style="yellow")
            return

        console.print("🔍 Git Repository Status", style="bold blue")
        console.print()

        # Repository info
        if git_context.get("origin_url"):
            console.print(f"📍 Origin: {git_context['origin_url']}", style="cyan")

        if git_context.get("github_owner") and git_context.get("github_repo"):
            console.print(
                f"🐙 GitHub: {git_context['github_owner']}/{git_context['github_repo']}",
                style="cyan",
            )

        # Current branch and linked issue
        if git_context.get("current_branch"):
            console.print(
                f"🌿 Current branch: {git_context['current_branch']}", style="green"
            )

            linked_issue = git_context.get("linked_issue")
            if linked_issue:
                console.print("🔗 Linked issue:", style="bold")
                console.print(f"   📋 {linked_issue['title']}", style="cyan")
                console.print(f"   🆔 {linked_issue['id']}", style="dim")
                console.print(f"   📊 Status: {linked_issue['status']}", style="yellow")
                console.print(
                    f"   ⚡ Priority: {linked_issue['priority']}",
                    style="red" if linked_issue["priority"] == "critical" else "yellow",
                )
            else:
                console.print("   💡 No linked issue found", style="dim")

        # Branch-issue mapping
        branch_issues = core.get_branch_linked_issues()
        if branch_issues:
            console.print("\n🌿 Branch-Issue Links:", style="bold")
            for branch, issue_ids in branch_issues.items():
                for issue_id in issue_ids:
                    issue = core.get_issue(issue_id)
                    if issue:
                        marker = (
                            "👉"
                            if branch == git_context.get("current_branch")
                            else "  "
                        )
                        console.print(
                            f"{marker} {branch} → {issue.title[:50]}{'...' if len(issue.title) > 50 else ''}",
                            style="cyan",
                        )

        # Recent commits with roadmap references
        if core.git.is_git_repository():
            recent_commits = core.git.get_recent_commits(count=5)
            roadmap_commits = [
                c for c in recent_commits if c.extract_roadmap_references()
            ]

            if roadmap_commits:
                console.print("\n📝 Recent Roadmap Commits:", style="bold")
                for commit in roadmap_commits[:3]:
                    console.print(
                        f"   {commit.short_hash} {commit.message[:60]}{'...' if len(commit.message) > 60 else ''}",
                        style="dim",
                    )
                    refs = commit.extract_roadmap_references()
                    if refs:
                        console.print(
                            f"     🔗 References: {', '.join(refs)}", style="cyan"
                        )

    except Exception as e:
        console.print(f"❌ Failed to get Git status: {e}", style="bold red")


@main.command()
@click.argument("issue_id")
@click.option(
    "--checkout/--no-checkout", default=True, help="Checkout the branch after creation"
)
@click.pass_context
def git_branch(ctx: click.Context, issue_id: str, checkout: bool):
    """Create a Git branch for an issue."""
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return

    if not core.git.is_git_repository():
        console.print("❌ Not in a Git repository", style="bold red")
        return

    try:
        issue = core.get_issue(issue_id)
        if not issue:
            console.print(f"❌ Issue not found: {issue_id}", style="bold red")
            return

        branch_name = core.suggest_branch_name_for_issue(issue_id)
        if not branch_name:
            console.print(
                f"❌ Could not suggest branch name for issue", style="bold red"
            )
            return

        # Create the branch
        success = core.git.create_branch_for_issue(issue, checkout=checkout)

        if success:
            console.print(f"🌿 Created branch: {branch_name}", style="bold green")
            if checkout:
                console.print(f"✅ Checked out branch: {branch_name}", style="green")
            console.print(f"🔗 Linked to issue: {issue.title}", style="cyan")

            # Update issue status to in-progress if it's todo
            if issue.status == Status.TODO:
                core.update_issue(issue_id, status=Status.IN_PROGRESS)
                console.print("📊 Updated issue status to: in-progress", style="yellow")
        else:
            console.print(f"❌ Failed to create branch", style="bold red")

    except Exception as e:
        console.print(f"❌ Failed to create Git branch: {e}", style="bold red")


@main.command()
@click.argument("issue_id")
@click.pass_context
def git_link(ctx: click.Context, issue_id: str):
    """Link an issue to the current Git branch."""
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return

    if not core.git.is_git_repository():
        console.print("❌ Not in a Git repository", style="bold red")
        return

    try:
        current_branch = core.git.get_current_branch()
        if not current_branch:
            console.print("❌ Could not determine current branch", style="bold red")
            return

        issue = core.get_issue(issue_id)
        if not issue:
            console.print(f"❌ Issue not found: {issue_id}", style="bold red")
            return

        success = core.link_issue_to_current_branch(issue_id)

        if success:
            console.print(
                f"🔗 Linked issue to branch: {current_branch.name}", style="bold green"
            )
            console.print(f"📋 Issue: {issue.title}", style="cyan")
        else:
            console.print("❌ Failed to link issue to branch", style="bold red")

    except Exception as e:
        console.print(f"❌ Failed to link issue: {e}", style="bold red")


@main.command()
@click.argument("issue_id")
@click.option("--since", help="Show commits since date (e.g., '1 week ago')")
@click.pass_context
def git_commits(ctx: click.Context, issue_id: str, since: Optional[str]):
    """Show Git commits that reference an issue."""
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return

    if not core.git.is_git_repository():
        console.print("❌ Not in a Git repository", style="bold red")
        return

    try:
        issue = core.get_issue(issue_id)
        if not issue:
            console.print(f"❌ Issue not found: {issue_id}", style="bold red")
            return

        commits = core.get_commits_for_issue(issue_id, since)

        if not commits:
            console.print(
                f"📝 No commits found referencing issue {issue_id}", style="yellow"
            )
            if since:
                console.print(f"   (searched since: {since})", style="dim")
            return

        console.print(f"📝 Commits for: {issue.title}", style="bold blue")
        console.print(f"🆔 Issue ID: {issue_id}", style="dim")
        console.print()

        for commit in commits:
            console.print(f"🔸 {commit.short_hash} {commit.author}", style="cyan")
            console.print(
                f"   📅 {commit.date.strftime('%Y-%m-%d %H:%M')}", style="dim"
            )
            console.print(f"   💬 {commit.message}", style="white")

            # Show progress info if available
            progress = commit.extract_progress_info()
            if progress is not None:
                console.print(f"   📊 Progress: {progress}%", style="yellow")

            # Show file changes
            if commit.files_changed:
                file_count = len(commit.files_changed)
                console.print(
                    f"   📁 {file_count} file{'s' if file_count != 1 else ''} changed",
                    style="green",
                )
                if commit.insertions or commit.deletions:
                    console.print(
                        f"   ➕ {commit.insertions} ➖ {commit.deletions}",
                        style="green",
                    )

            console.print()

    except Exception as e:
        console.print(f"❌ Failed to show commits: {e}", style="bold red")


@main.command()
@click.argument("issue_id")
@click.pass_context
def git_sync(ctx: click.Context, issue_id: str):
    """Sync issue status from Git commit activity."""
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return

    if not core.git.is_git_repository():
        console.print("❌ Not in a Git repository", style="bold red")
        return

    try:
        issue = core.get_issue(issue_id)
        if not issue:
            console.print(f"❌ Issue not found: {issue_id}", style="bold red")
            return

        old_status = issue.status.value
        old_progress = getattr(issue, "progress_percentage", None)

        success = core.update_issue_from_git_activity(issue_id)

        if success:
            # Reload issue to see changes
            updated_issue = core.get_issue(issue_id)
            console.print(
                f"🔄 Synced issue from Git activity: {issue.title}", style="bold green"
            )

            if updated_issue.status.value != old_status:
                console.print(
                    f"   📊 Status: {old_status} → {updated_issue.status.value}",
                    style="yellow",
                )

            if (
                hasattr(updated_issue, "progress_percentage")
                and updated_issue.progress_percentage != old_progress
            ):
                console.print(
                    f"   📈 Progress: {old_progress or 0}% → {updated_issue.progress_percentage}%",
                    style="cyan",
                )
        else:
            console.print(
                f"📝 No Git activity found for issue {issue_id}", style="yellow"
            )
            console.print(
                "   💡 Add commit messages with [roadmap:issue-id] to track progress",
                style="dim",
            )

    except Exception as e:
        console.print(f"❌ Failed to sync from Git: {e}", style="bold red")


@main.command("git-hooks-install")
@click.option(
    "--hooks",
    "-h",
    multiple=True,
    type=click.Choice(["post-commit", "pre-push", "post-merge", "post-checkout"]),
    help="Specific hooks to install (installs all if not specified)",
)
@click.pass_context
def git_hooks_install(ctx: click.Context, hooks: tuple):
    """Install Git hooks for automated roadmap integration."""
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return

    try:
        from .git_hooks import GitHookManager

        # Check if we're in a Git repository
        if not Path(".git").exists():
            console.print("❌ Not in a Git repository", style="bold red")
            console.print("Navigate to your Git project root first", style="dim")
            return

        hook_manager = GitHookManager(core)
        hooks_list = list(hooks) if hooks else None

        success = hook_manager.install_hooks(hooks_list)

        if success:
            installed_hooks = hooks_list or [
                "post-commit",
                "pre-push",
                "post-merge",
                "post-checkout",
            ]
            console.print("✅ Git hooks installed successfully!", style="bold green")
            console.print(
                f"   🪝 Installed hooks: {', '.join(installed_hooks)}", style="cyan"
            )
            console.print()
            console.print("🎯 Automated Features Enabled:", style="bold blue")
            console.print(
                "   • Issue status updates from commit messages", style="green"
            )
            console.print(
                "   • Progress tracking via [progress:X%] tags", style="green"
            )
            console.print(
                "   • Automatic issue completion with [closes roadmap:id]",
                style="green",
            )
            console.print("   • Milestone progress updates", style="green")
            console.print("   • Branch context tracking", style="green")
            console.print()
            console.print("💡 Usage Examples:", style="bold yellow")
            console.print(
                '   git commit -m "feat: add login [roadmap:abc123] [progress:50%]"',
                style="dim",
            )
            console.print(
                '   git commit -m "fix: auth bug [closes roadmap:def456]"', style="dim"
            )
        else:
            console.print("❌ Failed to install Git hooks", style="bold red")
            console.print(
                "Check that you have write permissions to .git/hooks/", style="dim"
            )

    except Exception as e:
        console.print(f"❌ Failed to install Git hooks: {e}", style="bold red")


@main.command("git-hooks-uninstall")
@click.pass_context
def git_hooks_uninstall(ctx: click.Context):
    """Remove roadmap Git hooks."""
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return

    try:
        from .git_hooks import GitHookManager

        hook_manager = GitHookManager(core)
        success = hook_manager.uninstall_hooks()

        if success:
            console.print("✅ Git hooks removed successfully", style="bold green")
            console.print("   🪝 Automated roadmap integration disabled", style="cyan")
        else:
            console.print("❌ Failed to remove Git hooks", style="bold red")

    except Exception as e:
        console.print(f"❌ Failed to remove Git hooks: {e}", style="bold red")


@main.command("workflow-automation-setup")
@click.option(
    "--features",
    "-f",
    multiple=True,
    type=click.Choice(["git-hooks", "status-automation", "progress-tracking"]),
    help="Specific automation features to enable (enables all if not specified)",
)
@click.pass_context
def workflow_automation_setup(ctx: click.Context, features: tuple):
    """Setup comprehensive workflow automation."""
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return

    try:
        from .git_hooks import WorkflowAutomation

        automation = WorkflowAutomation(core)
        features_list = list(features) if features else None

        console.print("🚀 Setting up workflow automation...", style="bold blue")

        results = automation.setup_automation(features_list)

        console.print("📊 Automation Setup Results:", style="bold white")

        for feature, success in results.items():
            status = "✅" if success else "❌"
            style = "green" if success else "red"
            feature_name = feature.replace("-", " ").title()
            console.print(f"   {status} {feature_name}", style=style)

        if all(results.values()):
            console.print()
            console.print("🎉 Workflow automation fully enabled!", style="bold green")
            console.print()
            console.print("🎯 Available Automation Features:", style="bold blue")

            if "git-hooks" not in features or not features:
                console.print("   🪝 Git Hooks:", style="cyan")
                console.print(
                    "      • Auto-update issue status from commits", style="dim"
                )
                console.print(
                    "      • Progress tracking via commit messages", style="dim"
                )
                console.print("      • Milestone progress automation", style="dim")

            if "status-automation" not in features or not features:
                console.print("   🔄 Status Automation:", style="cyan")
                console.print("      • Smart status transitions", style="dim")
                console.print("      • Blocked status detection", style="dim")
                console.print("      • Auto-completion on merge", style="dim")

            if "progress-tracking" not in features or not features:
                console.print("   📈 Progress Tracking:", style="cyan")
                console.print("      • Velocity metrics", style="dim")
                console.print("      • Team productivity insights", style="dim")
                console.print("      • Automatic progress updates", style="dim")

            console.print()
            console.print("🔧 Quick Start:", style="bold yellow")
            console.print("   1. Create issues with automatic branches:", style="white")
            console.print(
                "      roadmap issue create 'New feature' --git-branch", style="dim"
            )
            console.print("   2. Work with progress tracking:", style="white")
            console.print(
                '      git commit -m "feat: implement feature [roadmap:id] [progress:75%]"',
                style="dim",
            )
            console.print("   3. Complete issues automatically:", style="white")
            console.print(
                '      git commit -m "feat: finalize feature [closes roadmap:id]"',
                style="dim",
            )
            console.print("   4. Sync all issues from Git activity:", style="white")
            console.print("      roadmap workflow-sync-all", style="dim")
        else:
            console.print()
            console.print(
                "⚠️  Some automation features failed to set up", style="yellow"
            )
            console.print("Check permissions and try again", style="dim")

    except Exception as e:
        console.print(f"❌ Failed to setup workflow automation: {e}", style="bold red")


@main.command("workflow-automation-disable")
@click.pass_context
def workflow_automation_disable(ctx: click.Context):
    """Disable all workflow automation."""
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return

    try:
        from .git_hooks import WorkflowAutomation

        automation = WorkflowAutomation(core)
        success = automation.disable_automation()

        if success:
            console.print("✅ Workflow automation disabled", style="bold green")
            console.print("   🪝 Git hooks removed", style="cyan")
            console.print("   📁 Configuration files cleaned up", style="cyan")
        else:
            console.print("❌ Failed to disable automation", style="bold red")

    except Exception as e:
        console.print(f"❌ Failed to disable automation: {e}", style="bold red")


@main.command("workflow-sync-all")
@click.option(
    "--dry-run", is_flag=True, help="Show what would be synced without making changes"
)
@click.pass_context
def workflow_sync_all(ctx: click.Context, dry_run: bool):
    """Sync all issues with their Git activity."""
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return

    try:
        from .git_hooks import WorkflowAutomation

        automation = WorkflowAutomation(core)

        if dry_run:
            console.print("🔍 Dry run - analyzing Git activity...", style="yellow")
        else:
            console.print("🔄 Syncing all issues with Git activity...", style="blue")

        results = automation.sync_all_issues_with_git()

        console.print()
        console.print("📊 Sync Results:", style="bold white")
        console.print(f"   📝 Issues analyzed: {len(core.list_issues())}", style="cyan")
        console.print(f"   🔄 Issues synced: {results['synced_issues']}", style="green")

        if results["updated_issues"]:
            console.print()
            console.print("📈 Updated Issues:", style="bold blue")
            for update in results["updated_issues"]:
                console.print(f"   ✅ {update['title']}", style="green")
                console.print(
                    f"      📌 {update['id']} | {update['commits']} commit(s)",
                    style="dim",
                )

        if results["errors"]:
            console.print()
            console.print("⚠️  Errors:", style="bold red")
            for error in results["errors"]:
                console.print(f"   • {error}", style="red")

        if not results["updated_issues"] and not results["errors"]:
            console.print("   ✅ All issues already in sync", style="green")

        console.print()
        if not dry_run:
            console.print("💡 Next Steps:", style="bold yellow")
            console.print(
                "   • Review updated issue statuses: roadmap issue list", style="dim"
            )
            console.print(
                "   • Check milestone progress: roadmap milestone list", style="dim"
            )
            console.print(
                "   • View Git integration status: roadmap git-status", style="dim"
            )

    except Exception as e:
        console.print(f"❌ Failed to sync issues: {e}", style="bold red")


@main.group()
def analytics():
    """🔬 EXPERIMENTAL: Advanced analytics and insights commands."""
    pass


@analytics.command("developer")
@click.argument("developer_name")
@click.option(
    "--days", "-d", type=int, default=30, help="Analysis period in days (default: 30)"
)
@click.option("--save", "-s", help="Save report to file with given name")
@click.pass_context
def analytics_developer(ctx: click.Context, developer_name: str, days: int, save: str):
    """🔬 EXPERIMENTAL: Analyze individual developer productivity and patterns."""
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return

    try:
        from .analytics import GitHistoryAnalyzer

        analyzer = GitHistoryAnalyzer(core)
        metrics = analyzer.analyze_developer_productivity(developer_name, days)

        console.print(f"👤 Developer Analytics: {metrics.name}", style="bold blue")
        console.print(f"📅 Analysis Period: {days} days", style="dim")
        console.print()

        # Productivity Overview
        console.print("📊 Productivity Overview", style="bold white")
        console.print(f"   📝 Total Commits: {metrics.total_commits}", style="cyan")
        console.print(
            f"   ✅ Issues Completed: {metrics.issues_completed}", style="green"
        )
        console.print(
            f"   📈 Avg Commits/Day: {metrics.avg_commits_per_day:.1f}", style="yellow"
        )
        console.print(
            f"   ⏱️  Avg Completion Time: {metrics.avg_completion_time_hours:.1f}h",
            style="blue",
        )
        console.print()

        # Productivity Score
        score_style = (
            "bold green"
            if metrics.productivity_score >= 70
            else "yellow" if metrics.productivity_score >= 40 else "red"
        )
        console.print(
            f"🎯 Productivity Score: {metrics.productivity_score:.1f}/100",
            style=score_style,
        )
        console.print()

        # Specialization Areas
        if metrics.specialization_areas:
            console.print("🔧 Specialization Areas", style="bold white")
            for area in metrics.specialization_areas:
                console.print(f"   • {area}", style="cyan")
            console.print()

        # Collaboration Score
        collab_style = (
            "green"
            if metrics.collaboration_score >= 50
            else "yellow" if metrics.collaboration_score >= 25 else "red"
        )
        console.print(
            f"🤝 Collaboration Score: {metrics.collaboration_score:.1f}/100",
            style=collab_style,
        )
        console.print()

        # Performance Insights
        console.print("💡 Insights", style="bold yellow")
        if metrics.productivity_score >= 80:
            console.print(
                "   🌟 Excellent productivity! Keep up the great work.", style="green"
            )
        elif metrics.productivity_score >= 60:
            console.print(
                "   👍 Good productivity with room for improvement.", style="yellow"
            )
        else:
            console.print(
                "   📈 Consider focusing on smaller, more frequent commits.",
                style="red",
            )

        if metrics.collaboration_score < 30:
            console.print(
                "   🤝 Consider more collaborative work and code reviews.",
                style="yellow",
            )

        if metrics.avg_completion_time_hours > 72:
            console.print(
                "   ⏰ Try breaking issues into smaller tasks for faster completion.",
                style="yellow",
            )

        # Save report if requested
        if save:
            import json
            from pathlib import Path

            report_data = {
                "developer": metrics.name,
                "analysis_date": datetime.now().isoformat(),
                "period_days": days,
                "metrics": {
                    "total_commits": metrics.total_commits,
                    "issues_completed": metrics.issues_completed,
                    "avg_commits_per_day": metrics.avg_commits_per_day,
                    "avg_completion_time_hours": metrics.avg_completion_time_hours,
                    "productivity_score": metrics.productivity_score,
                    "collaboration_score": metrics.collaboration_score,
                    "specialization_areas": metrics.specialization_areas,
                },
            }

            report_path = Path(save)
            with create_secure_file(report_path, "w") as f:
                json.dump(report_data, f, indent=2)

            console.print(
                f"💾 Report saved to: {report_path.absolute()}", style="green"
            )

    except Exception as e:
        console.print(f"❌ Failed to analyze developer: {e}", style="bold red")


@analytics.command("team")
@click.option(
    "--days", "-d", type=int, default=30, help="Analysis period in days (default: 30)"
)
@click.option("--save", "-s", help="Save report to file with given name")
@click.option(
    "--format",
    "-f",
    type=click.Choice(["table", "detailed"]),
    default="table",
    help="Output format (default: table)",
)
@click.pass_context
def analytics_team(ctx: click.Context, days: int, save: str, format: str):
    """🔬 EXPERIMENTAL: Analyze team performance and collaboration patterns."""
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return

    try:
        from .analytics import AnalyticsReportGenerator, GitHistoryAnalyzer

        analyzer = GitHistoryAnalyzer(core)
        report_gen = AnalyticsReportGenerator(analyzer)

        console.print("🔍 Generating team analytics...", style="blue")

        if format == "detailed":
            # Generate comprehensive report
            report = report_gen.generate_team_report(days)

            if "error" in report:
                console.print(f"❌ {report['error']}", style="bold red")
                return

            console.print(f"👥 Team Analytics Report", style="bold blue")
            console.print(f"📅 Period: {days} days", style="dim")
            console.print()

            # Team Overview
            overview = report["team_overview"]
            console.print("📊 Team Overview", style="bold white")
            console.print(
                f"   👥 Total Developers: {overview['total_developers']}", style="cyan"
            )
            console.print(
                f"   📈 Avg Team Velocity: {overview['avg_team_velocity']:.1f}",
                style="yellow",
            )
            console.print()

            # Top Performers
            if overview["top_performers"]:
                console.print("🌟 Top Performers", style="bold green")
                for performer in overview["top_performers"][:3]:
                    console.print(f"   • {performer}", style="green")
                console.print()

            # Bottlenecks
            if overview["bottlenecks"]:
                console.print("⚠️  Potential Bottlenecks", style="bold red")
                for bottleneck in overview["bottlenecks"]:
                    console.print(f"   • {bottleneck}", style="red")
                console.print()

            # Code Quality
            quality = report["code_quality"]
            console.print("🔍 Code Quality Metrics", style="bold white")
            console.print(
                f"   🐛 Bug Fix Ratio: {quality['bug_fix_ratio']:.1%}", style="red"
            )
            console.print(
                f"   ✨ Feature Ratio: {quality['feature_ratio']:.1%}", style="green"
            )
            console.print(
                f"   🔧 Refactor Ratio: {quality['refactor_ratio']:.1%}", style="blue"
            )
            console.print(
                f"   📏 Avg Commit Size: {quality['avg_commit_size']:.0f} lines",
                style="yellow",
            )
            quality_score = quality.get("quality_score", 0)
            quality_style = (
                "green"
                if quality_score >= 70
                else "yellow" if quality_score >= 40 else "red"
            )
            console.print(
                f"   🎯 Quality Score: {quality_score:.1f}/100", style=quality_style
            )
            console.print()

            # Recommendations
            if overview["recommendations"]:
                console.print("💡 Recommendations", style="bold yellow")
                for rec in overview["recommendations"]:
                    console.print(f"   • {rec}", style="yellow")
                console.print()

        else:
            # Table format - show team insights
            insights = analyzer.generate_team_insights(days)

            console.print(
                f"👥 Team Performance Summary ({days} days)", style="bold blue"
            )
            console.print()

            # Get individual metrics for table
            since_date = (datetime.now() - timedelta(days=days)).isoformat()
            all_commits = analyzer.git_integration.get_recent_commits(
                count=1000, since=since_date
            )
            developers = list(set(c.author for c in all_commits))

            table = Table(title="Developer Performance")
            table.add_column("Developer", style="cyan")
            table.add_column("Commits", justify="center", style="yellow")
            table.add_column("Issues", justify="center", style="green")
            table.add_column("Productivity", justify="center", style="blue")
            table.add_column("Collaboration", justify="center", style="magenta")

            for dev in developers:
                try:
                    metrics = analyzer.analyze_developer_productivity(dev, days)
                    table.add_row(
                        metrics.name,
                        str(metrics.total_commits),
                        str(metrics.issues_completed),
                        f"{metrics.productivity_score:.0f}/100",
                        f"{metrics.collaboration_score:.0f}/100",
                    )
                except Exception:
                    continue

            console.print(table)
            console.print()

            # Summary stats
            console.print("📈 Team Summary", style="bold white")
            console.print(
                f"   👥 Active Developers: {insights.total_developers}", style="cyan"
            )
            console.print(
                f"   📊 Avg Team Velocity: {insights.avg_team_velocity:.1f}",
                style="yellow",
            )

            if insights.top_performers:
                console.print(
                    f"   🌟 Top Performer: {insights.top_performers[0]}", style="green"
                )

            if insights.bottleneck_areas:
                console.print(
                    f"   ⚠️  Key Bottleneck: {insights.bottleneck_areas[0]}", style="red"
                )

        # Save report if requested
        if save:
            if format == "detailed":
                report_path = report_gen.save_report_to_file(report, save)
            else:
                # Generate detailed report for saving even if showing table
                detailed_report = report_gen.generate_team_report(days)
                report_path = report_gen.save_report_to_file(detailed_report, save)

            console.print(f"💾 Detailed report saved to: {report_path}", style="green")

    except Exception as e:
        console.print(f"❌ Failed to analyze team: {e}", style="bold red")


@analytics.command("velocity")
@click.option(
    "--period",
    "-p",
    type=click.Choice(["week", "month", "quarter"]),
    default="week",
    help="Period for velocity analysis (default: week)",
)
@click.option(
    "--count",
    "-c",
    type=int,
    default=12,
    help="Number of periods to analyze (default: 12)",
)
@click.option("--chart", is_flag=True, help="Show ASCII chart of velocity trends")
@click.pass_context
def analytics_velocity(ctx: click.Context, period: str, count: int, chart: bool):
    """🔬 EXPERIMENTAL: Analyze project velocity trends over time."""
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return

    try:
        from .analytics import GitHistoryAnalyzer

        analyzer = GitHistoryAnalyzer(core)
        velocities = analyzer.analyze_project_velocity(period, count)

        if not velocities:
            console.print("📊 No velocity data available", style="yellow")
            return

        console.print(f"📈 Project Velocity Analysis ({period}ly)", style="bold blue")
        console.print()

        # Create velocity table
        table = Table(title=f"Velocity Trends ({count} {period}s)")
        table.add_column("Period", style="cyan")
        table.add_column("Commits", justify="center", style="yellow")
        table.add_column("Issues", justify="center", style="green")
        table.add_column("Lines +/-", justify="center", style="blue")
        table.add_column("Velocity", justify="center", style="magenta")
        table.add_column("Trend", justify="center", style="white")

        for velocity in velocities:
            trend_icon = {"increasing": "📈", "decreasing": "📉", "stable": "➡️"}.get(
                velocity.trend_direction, "➡️"
            )

            lines_change = f"+{velocity.lines_added}/-{velocity.lines_removed}"

            table.add_row(
                velocity.start_date.strftime("%m/%d"),
                str(velocity.commits_count),
                str(velocity.issues_completed),
                lines_change,
                f"{velocity.velocity_score:.1f}",
                f"{trend_icon} {velocity.trend_direction}",
            )

        console.print(table)
        console.print()

        # Calculate trend summary
        recent_velocities = [v.velocity_score for v in velocities[-4:]]
        if len(recent_velocities) > 1:
            avg_recent = statistics.mean(recent_velocities)
            trend_direction = velocities[-1].trend_direction

            console.print("📊 Velocity Summary", style="bold white")
            console.print(f"   📈 Current Avg: {avg_recent:.1f}", style="cyan")
            console.print(f"   📊 Trend: {trend_direction.title()}", style="yellow")

            if trend_direction == "increasing":
                console.print("   💡 Team velocity is improving! 🚀", style="green")
            elif trend_direction == "decreasing":
                console.print(
                    "   💡 Consider investigating velocity decline", style="red"
                )
            else:
                console.print("   💡 Steady velocity - good consistency", style="blue")

        # ASCII chart if requested
        if chart and len(velocities) > 1:
            console.print()
            console.print("📊 Velocity Chart", style="bold white")

            scores = [v.velocity_score for v in velocities]
            max_score = max(scores) if scores else 1

            for i, velocity in enumerate(velocities):
                bar_length = (
                    int((velocity.velocity_score / max_score) * 40)
                    if max_score > 0
                    else 0
                )
                bar = "█" * bar_length
                period_label = velocity.start_date.strftime("%m/%d")
                console.print(
                    f"   {period_label} │{bar:<40}│ {velocity.velocity_score:.1f}",
                    style="cyan",
                )

    except Exception as e:
        console.print(f"❌ Failed to analyze velocity: {e}", style="bold red")


@analytics.command("quality")
@click.option(
    "--days", "-d", type=int, default=90, help="Analysis period in days (default: 90)"
)
@click.pass_context
def analytics_quality(ctx: click.Context, days: int):
    """🔬 EXPERIMENTAL: Analyze code quality trends and metrics."""
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return

    try:
        from .analytics import GitHistoryAnalyzer

        analyzer = GitHistoryAnalyzer(core)
        quality = analyzer.analyze_code_quality_trends(days)

        console.print(f"🔍 Code Quality Analysis ({days} days)", style="bold blue")
        console.print()

        # Quality Metrics
        console.print("📊 Quality Metrics", style="bold white")
        console.print(f"   📝 Total Commits: {quality['total_commits']}", style="cyan")
        console.print(
            f"   🐛 Bug Fix Ratio: {quality['bug_fix_ratio']:.1%}", style="red"
        )
        console.print(
            f"   ✨ Feature Ratio: {quality['feature_ratio']:.1%}", style="green"
        )
        console.print(
            f"   🔧 Refactor Ratio: {quality['refactor_ratio']:.1%}", style="blue"
        )
        console.print(
            f"   📏 Avg Commit Size: {quality['avg_commit_size']:.0f} lines",
            style="yellow",
        )
        console.print(
            f"   📦 Large Commits: {quality['large_commits_ratio']:.1%}",
            style="orange1",
        )
        console.print()

        # Quality Score
        quality_score = quality.get("quality_score", 0)
        if quality_score >= 80:
            score_style = "bold green"
            score_message = "Excellent code quality! 🌟"
        elif quality_score >= 60:
            score_style = "yellow"
            score_message = "Good code quality with room for improvement"
        elif quality_score >= 40:
            score_style = "orange1"
            score_message = "Moderate code quality - consider improvements"
        else:
            score_style = "red"
            score_message = "Code quality needs attention"

        console.print(f"🎯 Quality Score: {quality_score:.1f}/100", style=score_style)
        console.print(f"   {score_message}", style="dim")
        console.print()

        # Quality Insights
        console.print("🔍 Quality Insights", style="bold white")

        if quality["bug_fix_ratio"] > 0.3:
            console.print(
                "   🐛 High bug fix ratio - consider more testing", style="red"
            )
        elif quality["bug_fix_ratio"] < 0.1:
            console.print("   ✅ Low bug ratio - good code stability", style="green")

        if quality["large_commits_ratio"] > 0.3:
            console.print(
                "   📦 Many large commits - break down changes", style="orange1"
            )
        elif quality["large_commits_ratio"] < 0.1:
            console.print("   📏 Good commit sizing - easy to review", style="green")

        if quality["refactor_ratio"] < 0.05:
            console.print(
                "   🔧 Low refactoring - schedule cleanup time", style="orange1"
            )
        elif quality["refactor_ratio"] > 0.2:
            console.print("   🔧 Active refactoring - good maintenance", style="green")

        console.print()

        # Recommendations
        if quality.get("recommendations"):
            console.print("💡 Recommendations", style="bold yellow")
            for rec in quality["recommendations"]:
                console.print(f"   • {rec}", style="yellow")

    except Exception as e:
        console.print(f"❌ Failed to analyze code quality: {e}", style="bold red")


@analytics.command("enhanced")
@click.option(
    "--period",
    "-p",
    type=click.Choice(["D", "W", "M", "Q"]),
    default="W",
    help="Analysis period for velocity trends (D=daily, W=weekly, M=monthly, Q=quarterly)",
)
@click.option(
    "--days",
    "-d",
    type=int,
    default=30,
    help="Days of recent data to analyze (default: 30)",
)
@click.option("--export", "-e", help="Export detailed analysis to file")
@click.option(
    "--format",
    "-f",
    type=click.Choice(["json", "excel"]),
    default="json",
    help="Export format (used with --export)",
)
@click.pass_context
def analytics_enhanced(
    ctx: click.Context, period: str, days: int, export: str, format: str
):
    """🔬 EXPERIMENTAL: Enhanced analytics with pandas-powered insights.

    Provides comprehensive analysis including:
    - Completion trends over time
    - Workload distribution across team
    - Milestone progress and health
    - Issue lifecycle bottlenecks
    - Velocity consistency analysis
    - Productivity insights with recommendations

    Examples:
        roadmap analytics enhanced --period W --days 60
        roadmap analytics enhanced --export analysis.json
        roadmap analytics enhanced --export analysis.excel --format excel
    """
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return

    try:
        analyzer = EnhancedAnalyzer(core)

        console.print("🚀 Enhanced Analytics Dashboard", style="bold blue")
        console.print("🔬 EXPERIMENTAL: Pandas-powered insights", style="dim")
        console.print()

        # 1. Completion Trends
        console.print("📈 Completion Trends", style="bold cyan")
        trends_df = analyzer.analyze_completion_trends(period=period, months=3)

        if not trends_df.empty:
            # Show recent trends
            recent_trends = trends_df.tail(5)
            table = Table(title=f"Recent Completion Trends ({period}ly)")
            table.add_column("Period", style="cyan")
            table.add_column("Issues", justify="center", style="green")
            table.add_column("Est. Hours", justify="center", style="yellow")
            table.add_column("Act. Hours", justify="center", style="blue")
            table.add_column("Efficiency", justify="center", style="magenta")
            table.add_column("Velocity", justify="center", style="white")

            for _, row in recent_trends.iterrows():
                efficiency = f"{row['efficiency_ratio']:.2f}"
                efficiency_style = "green" if row["efficiency_ratio"] >= 1.0 else "red"

                table.add_row(
                    str(row["completion_period"]),
                    str(int(row["issues_completed"])),
                    f"{row['total_estimated_hours']:.1f}h",
                    f"{row['total_actual_hours']:.1f}h",
                    efficiency,
                    f"{row['velocity_score']:.1f}",
                )

            console.print(table)
        else:
            console.print(
                "   📊 No completion data available for trend analysis", style="dim"
            )
        console.print()

        # 2. Workload Distribution
        console.print("👥 Team Workload Distribution", style="bold cyan")
        workload_df = analyzer.analyze_workload_distribution()

        if not workload_df.empty:
            # Show top team members by workload
            top_workload = workload_df.head(5)
            table = Table(title="Team Workload Analysis")
            table.add_column("Assignee", style="cyan")
            table.add_column("Active", justify="center", style="yellow")
            table.add_column("Total", justify="center", style="green")
            table.add_column("Completion %", justify="center", style="blue")
            table.add_column("Workload Score", justify="center", style="magenta")
            table.add_column("Status", style="white")

            for _, row in top_workload.iterrows():
                # Determine status based on workload score
                if row["workload_score"] > 20:
                    status = "🔴 Overloaded"
                elif row["workload_score"] > 10:
                    status = "🟡 Busy"
                else:
                    status = "🟢 Available"

                table.add_row(
                    row["assignee"],
                    str(int(row["active_issues"])),
                    str(int(row["total_issues"])),
                    f"{row['completion_rate']:.1f}%",
                    f"{row['workload_score']:.1f}",
                    status,
                )

            console.print(table)
        else:
            console.print("   📊 No workload data available", style="dim")
        console.print()

        # 3. Milestone Health
        console.print("🎯 Milestone Health Analysis", style="bold cyan")
        milestones_df = analyzer.analyze_milestone_progress()

        if not milestones_df.empty:
            table = Table(title="Milestone Health Dashboard")
            table.add_column("Milestone", style="cyan")
            table.add_column("Progress", justify="center", style="green")
            table.add_column("Health", justify="center", style="blue")
            table.add_column("Due Date", justify="center", style="yellow")
            table.add_column("Risk", justify="center", style="white")
            table.add_column("Urgency", style="magenta")

            for _, row in milestones_df.iterrows():
                # Health status styling
                health_score = row["health_score"]
                if health_score >= 85:
                    health_display = f"🟢 {health_score:.0f}"
                elif health_score >= 60:
                    health_display = f"🟡 {health_score:.0f}"
                else:
                    health_display = f"🔴 {health_score:.0f}"

                # Risk styling
                risk = row["delivery_risk"]
                risk_display = {
                    "Low": "🟢 Low",
                    "Medium": "🟡 Medium",
                    "High": "🔴 High",
                }.get(risk, risk)

                table.add_row(
                    row["name"],
                    f"{row['completion_percentage']:.1f}%",
                    health_display,
                    (
                        row["due_date"].strftime("%Y-%m-%d")
                        if pd.notna(row["due_date"])
                        else "No date"
                    ),
                    risk_display,
                    str(row["urgency_level"]),
                )

            console.print(table)
        else:
            console.print("   📊 No milestone data available", style="dim")
        console.print()

        # 4. Productivity Insights
        console.print("💡 Productivity Insights", style="bold cyan")
        insights = analyzer.generate_productivity_insights(days=days)

        if "error" not in insights:
            console.print(
                f"📊 Analysis Period: {insights['analysis_period_days']} days",
                style="dim",
            )
            console.print()

            # Summary metrics
            summary = insights["summary"]
            console.print("📈 Summary Metrics:", style="bold white")
            console.print(
                f"   ✅ Completion Rate: {summary['completion_rate']:.1f}%",
                style="green",
            )
            console.print(
                f"   ⏰ Average Estimate: {summary['avg_estimated_hours']:.1f}h",
                style="yellow",
            )
            console.print(
                f"   🚧 Overdue Issues: {summary['overdue_percentage']:.1f}%",
                style="red",
            )
            console.print(
                f"   🚫 Blocked Issues: {summary['blocked_percentage']:.1f}%",
                style="orange1",
            )
            console.print()

            # Recommendations
            if insights["recommendations"]:
                console.print("💡 Recommendations:", style="bold yellow")
                for rec in insights["recommendations"]:
                    console.print(f"   • {rec}", style="yellow")
                console.print()

        # 5. Velocity Consistency
        console.print("📊 Velocity Consistency", style="bold cyan")
        velocity_analysis = analyzer.analyze_velocity_consistency(weeks=8)

        if "error" not in velocity_analysis:
            console.print(
                f"📈 Average Velocity: {velocity_analysis['avg_velocity_score']:.1f}",
                style="green",
            )
            console.print(
                f"📊 Consistency: {velocity_analysis['consistency_rating']}",
                style="blue",
            )
            console.print(
                f"🎯 Trend: {velocity_analysis['trend_direction']}", style="yellow"
            )
            console.print(
                f"📅 Issues/Week: {velocity_analysis['avg_issues_per_week']:.1f}",
                style="cyan",
            )
        else:
            console.print("   📊 No velocity data available", style="dim")

        # Export functionality
        if export:
            console.print()
            console.print(f"💾 Exporting enhanced analytics...", style="bold blue")

            export_data = {
                "analysis_metadata": {
                    "generated_at": datetime.now().isoformat(),
                    "period": period,
                    "days_analyzed": days,
                    "analysis_type": "enhanced_analytics",
                },
                "completion_trends": (
                    trends_df.to_dict("records") if not trends_df.empty else []
                ),
                "workload_distribution": (
                    workload_df.to_dict("records") if not workload_df.empty else []
                ),
                "milestone_health": (
                    milestones_df.to_dict("records") if not milestones_df.empty else []
                ),
                "productivity_insights": insights,
                "velocity_consistency": velocity_analysis,
            }

            export_path = Path(export)

            if format == "json":
                with create_secure_file(export_path, "w") as f:
                    import json

                    json.dump(export_data, f, indent=2, default=str)

            elif format == "excel":
                # Create multi-sheet Excel export
                data_sheets = {}

                if not trends_df.empty:
                    data_sheets["Completion_Trends"] = trends_df
                if not workload_df.empty:
                    data_sheets["Team_Workload"] = workload_df
                if not milestones_df.empty:
                    data_sheets["Milestone_Health"] = milestones_df

                # Add summary sheet
                summary_data = []
                if "error" not in insights:
                    for key, value in insights["summary"].items():
                        summary_data.append({"metric": key, "value": value})

                if summary_data:
                    data_sheets["Summary_Metrics"] = pd.DataFrame(summary_data)

                if data_sheets:
                    DataFrameAdapter.export_multiple_sheets(data_sheets, export_path)
                else:
                    console.print(
                        "   ⚠️ No data available for Excel export", style="yellow"
                    )
                    return

            console.print(
                f"✅ Enhanced analytics exported to {export_path.absolute()}",
                style="bold green",
            )
            console.print(f"📊 Format: {format.upper()}", style="dim")

    except Exception as e:
        console.print(
            f"❌ Failed to generate enhanced analytics: {e}", style="bold red"
        )


@main.group()
def predict():
    """🔬 EXPERIMENTAL: Predictive intelligence and forecasting commands."""
    pass


@predict.command("estimate")
@click.argument("issue_ids", nargs=-1)
@click.option("--developer", "-d", help="Developer to assign (affects estimation)")
@click.option("--all", "estimate_all", is_flag=True, help="Estimate all active issues")
@click.option("--save", "-s", help="Save estimates to file with given name")
@click.pass_context
def predict_estimate(
    ctx: click.Context, issue_ids: tuple, developer: str, estimate_all: bool, save: str
):
    """🔬 EXPERIMENTAL: Estimate completion time for issues using ML algorithms."""
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return

    try:
        from .predictive import IssueEstimator

        estimator = IssueEstimator(core)

        # Get issues to estimate
        if estimate_all:
            issues = [
                i
                for i in core.list_issues()
                if i.status in [Status.TODO, Status.IN_PROGRESS]
            ]
            if not issues:
                console.print("📋 No active issues to estimate", style="yellow")
                return
        elif issue_ids:
            issues = []
            for issue_id in issue_ids:
                issue = core.get_issue(issue_id)
                if issue:
                    issues.append(issue)
                else:
                    console.print(f"⚠️  Issue {issue_id} not found", style="orange1")
            if not issues:
                return
        else:
            console.print(
                "❌ Please specify issue IDs or use --all flag", style="bold red"
            )
            return

        console.print(f"🔮 Estimating {len(issues)} issue(s)...", style="bold blue")
        if developer:
            console.print(f"👤 Developer: {developer}", style="dim")
        console.print()

        # Generate estimates
        estimates = [
            estimator.estimate_issue_time(issue, developer) for issue in issues
        ]

        # Create results table
        table = Table(title="🎯 Issue Time Estimates")
        table.add_column("Issue ID", style="cyan", no_wrap=True)
        table.add_column("Title", style="white", max_width=40)
        table.add_column("Est. Hours", justify="center", style="green")
        table.add_column("Confidence", justify="center", style="blue")
        table.add_column("Range", justify="center", style="yellow")
        table.add_column("Complexity", justify="center", style="magenta")

        total_hours = 0
        high_uncertainty_count = 0

        for issue, estimate in zip(issues, estimates):
            # Confidence styling
            conf_style = {
                "very_high": "bright_green",
                "high": "green",
                "medium": "yellow",
                "low": "red",
            }.get(estimate.confidence_level.value, "white")

            # Complexity styling
            complexity_emoji = (
                "🟢"
                if estimate.complexity_score < 4
                else "🟡" if estimate.complexity_score < 7 else "🔴"
            )

            table.add_row(
                issue.id,
                issue.title[:40] + "..." if len(issue.title) > 40 else issue.title,
                f"{estimate.estimated_hours:.1f}h",
                f"[{conf_style}]{estimate.confidence_level.value}[/{conf_style}]",
                f"{estimate.uncertainty_range[0]:.1f}-{estimate.uncertainty_range[1]:.1f}h",
                f"{complexity_emoji} {estimate.complexity_score:.1f}",
            )

            total_hours += estimate.estimated_hours
            if estimate.confidence_level.value == "low":
                high_uncertainty_count += 1

        console.print(table)
        console.print()

        # Summary
        console.print("📊 Estimation Summary", style="bold white")
        console.print(f"   📝 Total Issues: {len(estimates)}")
        console.print(f"   ⏱️  Total Estimated Time: {total_hours:.1f} hours")
        console.print(f"   📅 Estimated Days: {total_hours/8:.1f} working days")
        if high_uncertainty_count:
            console.print(
                f"   ⚠️  High Uncertainty Issues: {high_uncertainty_count}",
                style="orange1",
            )

        # Factors and insights
        common_factors = {}
        for estimate in estimates:
            for factor in estimate.factors_considered:
                common_factors[factor] = common_factors.get(factor, 0) + 1

        if common_factors:
            console.print()
            console.print("🔍 Estimation Factors", style="bold yellow")
            for factor, count in sorted(
                common_factors.items(), key=lambda x: x[1], reverse=True
            ):
                console.print(f"   • {factor} ({count} issues)")

        # Save if requested
        if save:
            import json
            from pathlib import Path

            filename = save if save.endswith(".json") else f"{save}.json"
            report_data = {
                "generated": datetime.now().isoformat(),
                "developer": developer,
                "total_issues": len(estimates),
                "total_hours": total_hours,
                "estimates": [
                    {
                        "issue_id": est.issue_id,
                        "estimated_hours": est.estimated_hours,
                        "confidence_level": est.confidence_level.value,
                        "confidence_score": est.confidence_score,
                        "complexity_score": est.complexity_score,
                        "uncertainty_range": est.uncertainty_range,
                        "factors": est.factors_considered,
                    }
                    for est in estimates
                ],
            }

            with create_secure_file(filename, "w") as f:
                json.dump(report_data, f, indent=2)

            console.print(
                f"💾 Estimates saved to {Path(filename).absolute()}", style="green"
            )

    except Exception as e:
        console.print(f"❌ Failed to estimate issues: {e}", style="bold red")


@predict.command("risks")
@click.option(
    "--days", "-d", type=int, default=30, help="Risk assessment period (default: 30)"
)
@click.option(
    "--level",
    type=click.Choice(["all", "high", "critical"]),
    default="all",
    help="Filter by risk level",
)
@click.option("--save", "-s", help="Save risk assessment to file")
@click.pass_context
def predict_risks(ctx: click.Context, days: int, level: str, save: str):
    """🔬 EXPERIMENTAL: Assess potential project risks and mitigation strategies."""
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return

    try:
        from .predictive import RiskLevel, RiskPredictor

        predictor = RiskPredictor(core)
        risks = predictor.assess_project_risks(days)

        # Filter by level if specified
        if level != "all":
            if level == "critical":
                risks = [r for r in risks if r.risk_level == RiskLevel.CRITICAL]
            elif level == "high":
                risks = [
                    r
                    for r in risks
                    if r.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]
                ]

        console.print(f"⚠️  Risk Assessment ({days} days ahead)", style="bold red")
        console.print(f"🔍 Risk Level Filter: {level.title()}", style="dim")
        console.print()

        if not risks:
            console.print("✅ No significant risks identified!", style="bold green")
            console.print("   Your project appears to be on track.", style="green")
            return

        # Risk summary
        risk_counts = {}
        for risk_level in RiskLevel:
            count = len([r for r in risks if r.risk_level == risk_level])
            if count > 0:
                risk_counts[risk_level.value] = count

        console.print("📊 Risk Summary", style="bold white")
        for level_name, count in risk_counts.items():
            level_style = {
                "critical": "bright_red",
                "high": "red",
                "medium": "orange1",
                "low": "yellow",
            }.get(level_name, "white")

            emoji = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}.get(
                level_name, "⚪"
            )
            console.print(
                f"   {emoji} {level_name.title()}: {count} risk(s)", style=level_style
            )

        console.print()

        # Detailed risk analysis
        for i, risk in enumerate(risks[:10], 1):  # Show top 10 risks
            # Risk level styling
            level_style = {
                RiskLevel.CRITICAL: "bright_red",
                RiskLevel.HIGH: "red",
                RiskLevel.MEDIUM: "orange1",
                RiskLevel.LOW: "yellow",
            }.get(risk.risk_level, "white")

            level_emoji = {
                RiskLevel.CRITICAL: "🔴",
                RiskLevel.HIGH: "🟠",
                RiskLevel.MEDIUM: "🟡",
                RiskLevel.LOW: "🟢",
            }.get(risk.risk_level, "⚪")

            console.print(
                f"[bold]{i}. {risk.risk_type}[/bold] {level_emoji}", style=level_style
            )
            console.print(f"   📝 {risk.description}")
            console.print(
                f"   📊 Probability: {risk.probability*100:.0f}% | Impact: {risk.impact_score}/10"
            )

            if risk.indicators:
                console.print("   🔍 Indicators:")
                for indicator in risk.indicators:
                    console.print(f"      • {indicator}", style="dim")

            if risk.mitigation_suggestions:
                console.print("   💡 Mitigation:")
                for suggestion in risk.mitigation_suggestions:
                    console.print(f"      • {suggestion}", style="cyan")

            if risk.affected_issues:
                console.print(f"   🎯 Affects {len(risk.affected_issues)} issue(s)")

            if risk.deadline_impact_days:
                console.print(
                    f"   ⏰ Potential Delay: {risk.deadline_impact_days} days",
                    style="orange1",
                )

            console.print()

        if len(risks) > 10:
            console.print(f"... and {len(risks) - 10} more risks", style="dim")
            console.print()

        # Top mitigation priorities
        high_impact_risks = [
            r
            for r in risks
            if r.impact_score >= 7
            or r.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]
        ]
        if high_impact_risks:
            console.print("🚨 Immediate Action Required", style="bold red")
            for risk in high_impact_risks[:3]:
                console.print(f"   • {risk.description}", style="red")
                if risk.mitigation_suggestions:
                    console.print(
                        f"     → {risk.mitigation_suggestions[0]}", style="yellow"
                    )

        # Save if requested
        if save:
            import json
            from pathlib import Path

            filename = save if save.endswith(".json") else f"{save}.json"
            report_data = {
                "generated": datetime.now().isoformat(),
                "assessment_period_days": days,
                "risk_level_filter": level,
                "total_risks": len(risks),
                "risk_summary": risk_counts,
                "risks": [
                    {
                        "risk_id": r.risk_id,
                        "type": r.risk_type,
                        "level": r.risk_level.value,
                        "probability": r.probability,
                        "impact_score": r.impact_score,
                        "description": r.description,
                        "indicators": r.indicators,
                        "mitigation_suggestions": r.mitigation_suggestions,
                        "affected_issues": r.affected_issues,
                        "deadline_impact_days": r.deadline_impact_days,
                    }
                    for r in risks
                ],
            }

            with create_secure_file(filename, "w") as f:
                json.dump(report_data, f, indent=2)

            console.print(
                f"💾 Risk assessment saved to {Path(filename).absolute()}",
                style="green",
            )

    except Exception as e:
        console.print(f"❌ Failed to assess risks: {e}", style="bold red")


@predict.command("deadline")
@click.option("--target", "-t", help="Target completion date (YYYY-MM-DD)")
@click.option(
    "--milestone", "-m", multiple=True, help="Focus on specific milestone issues"
)
@click.option("--save", "-s", help="Save forecast to file")
@click.pass_context
def predict_deadline(ctx: click.Context, target: str, milestone: tuple, save: str):
    """🔬 EXPERIMENTAL: Forecast project completion with scenario analysis."""
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return

    try:
        from .predictive import DeadlineForecaster

        forecaster = DeadlineForecaster(core)

        # Parse target date if provided
        target_date = None
        if target:
            try:
                target_date = datetime.strptime(target, "%Y-%m-%d")
            except ValueError:
                console.print(
                    "❌ Invalid target date format. Use YYYY-MM-DD", style="bold red"
                )
                return

        # Generate forecast
        if milestone:
            console.print(
                f"🎯 Forecasting milestone: {', '.join(milestone)}", style="bold blue"
            )
            forecast = forecaster.forecast_milestone_completion(list(milestone))
        else:
            console.print("📅 Forecasting project completion...", style="bold blue")
            forecast = forecaster.forecast_project_completion(target_date)

        console.print()

        # Main forecast results
        console.print("🔮 Completion Forecast", style="bold white")

        if target_date:
            console.print(f"🎯 Target Date: {target_date.strftime('%Y-%m-%d')}")

            # Delay probability styling
            delay_prob = forecast.delay_probability
            if delay_prob < 0.3:
                delay_style, delay_emoji = "green", "✅"
            elif delay_prob < 0.6:
                delay_style, delay_emoji = "yellow", "⚠️"
            else:
                delay_style, delay_emoji = "red", "🚨"

            console.print(
                f"{delay_emoji} Delay Probability: [{delay_style}]{delay_prob*100:.0f}%[/{delay_style}]"
            )

        console.print(
            f"📅 Predicted Completion: {forecast.predicted_completion.strftime('%Y-%m-%d')}"
        )

        # Confidence level styling
        conf_style = {
            "very_high": "bright_green",
            "high": "green",
            "medium": "yellow",
            "low": "red",
        }.get(forecast.confidence_level.value, "white")

        console.print(
            f"🎯 Confidence Level: [{conf_style}]{forecast.confidence_level.value.replace('_', ' ').title()}[/{conf_style}]"
        )
        console.print()

        # Scenario analysis
        scenarios = forecast.scenario_analysis
        console.print("📊 Scenario Analysis", style="bold white")

        scenario_table = Table()
        scenario_table.add_column("Scenario", style="cyan")
        scenario_table.add_column("Completion Date", style="white")
        scenario_table.add_column("Days from Now", justify="center", style="yellow")

        today = datetime.now()
        for scenario_name, scenario_date in scenarios.items():
            days_diff = (scenario_date - today).days
            scenario_table.add_row(
                scenario_name.title(),
                scenario_date.strftime("%Y-%m-%d"),
                f"{days_diff} days",
            )

        console.print(scenario_table)
        console.print()

        # Critical path
        if forecast.critical_path_issues:
            console.print("🔥 Critical Path Issues", style="bold red")
            for issue_id in forecast.critical_path_issues:
                try:
                    issue = core.get_issue(issue_id)
                    if issue:
                        priority_emoji = {
                            "low": "🟢",
                            "medium": "🟡",
                            "high": "🟠",
                            "critical": "🔴",
                        }.get(issue.priority.value, "⚪")
                        console.print(f"   {priority_emoji} {issue.id}: {issue.title}")
                except:
                    console.print(f"   • {issue_id}")
            console.print()

        # Resource constraints
        if forecast.resource_constraints:
            console.print("⚠️  Resource Constraints", style="bold orange1")
            for constraint in forecast.resource_constraints:
                console.print(f"   • {constraint}", style="orange1")
            console.print()

        # Optimization suggestions
        if forecast.optimization_suggestions:
            console.print("💡 Optimization Suggestions", style="bold yellow")
            for suggestion in forecast.optimization_suggestions:
                console.print(f"   • {suggestion}", style="yellow")
            console.print()

        # If target date provided, show impact analysis
        if target_date and forecast.predicted_completion > target_date:
            days_late = (forecast.predicted_completion - target_date).days
            console.print(
                f"🚨 [bold red]Projected to miss target by {days_late} days[/bold red]"
            )
            console.print("🎯 Consider these actions:", style="bold yellow")
            console.print(
                "   • Reduce scope or defer non-critical features", style="yellow"
            )
            console.print(
                "   • Add additional resources to critical path", style="yellow"
            )
            console.print("   • Negotiate deadline extension", style="yellow")
        elif target_date and forecast.predicted_completion <= target_date:
            days_early = (target_date - forecast.predicted_completion).days
            console.print(
                f"✅ [bold green]On track to meet target (with {days_early} days buffer)[/bold green]"
            )

        # Save if requested
        if save:
            import json
            from pathlib import Path

            filename = save if save.endswith(".json") else f"{save}.json"
            report_data = {
                "generated": datetime.now().isoformat(),
                "target_date": target_date.isoformat() if target_date else None,
                "milestone_focus": list(milestone) if milestone else None,
                "predicted_completion": forecast.predicted_completion.isoformat(),
                "confidence_level": forecast.confidence_level.value,
                "delay_probability": forecast.delay_probability,
                "scenario_analysis": {k: v.isoformat() for k, v in scenarios.items()},
                "critical_path_issues": forecast.critical_path_issues,
                "resource_constraints": forecast.resource_constraints,
                "optimization_suggestions": forecast.optimization_suggestions,
            }

            with create_secure_file(filename, "w") as f:
                json.dump(report_data, f, indent=2)

            console.print(
                f"💾 Forecast saved to {Path(filename).absolute()}", style="green"
            )

    except Exception as e:
        console.print(f"❌ Failed to generate forecast: {e}", style="bold red")


@predict.command("intelligence")
@click.option("--target", "-t", help="Target completion date (YYYY-MM-DD)")
@click.option("--save", "-s", help="Save intelligence report to file")
@click.pass_context
def predict_intelligence(ctx: click.Context, target: str, save: str):
    """🔬 EXPERIMENTAL: Generate comprehensive predictive intelligence report."""
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return

    try:
        from .predictive import PredictiveReportGenerator

        # Parse target date if provided
        target_date = None
        if target:
            try:
                target_date = datetime.strptime(target, "%Y-%m-%d")
            except ValueError:
                console.print(
                    "❌ Invalid target date format. Use YYYY-MM-DD", style="bold red"
                )
                return

        console.print(
            "🧠 Generating Predictive Intelligence Report...", style="bold blue"
        )
        console.print("   📊 Analyzing project data...")
        console.print("   🔮 Running ML algorithms...")
        console.print("   ⚠️  Assessing risks...")
        console.print("   📅 Forecasting timelines...")
        console.print()

        generator = PredictiveReportGenerator(core)

        # Generate filename if save requested but no name provided
        if save is True or save == "":
            save = (
                f"intelligence_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            )

        report = generator.generate_intelligence_report(target_date, save)

        if "error" in report:
            console.print(f"❌ {report['error']}", style="bold red")
            return

        # Display executive summary
        console.print("🧠 Predictive Intelligence Report", style="bold blue")
        console.print(
            f"📅 Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", style="dim"
        )
        if target_date:
            console.print(
                f"🎯 Target Date: {target_date.strftime('%Y-%m-%d')}", style="dim"
            )
        console.print()

        # Project forecast summary
        forecast = report["project_forecast"]
        console.print("📈 Project Forecast", style="bold white")
        console.print(
            f"   📅 Predicted Completion: {datetime.fromisoformat(forecast['predicted_completion']).strftime('%Y-%m-%d')}"
        )

        conf_style = {
            "very_high": "bright_green",
            "high": "green",
            "medium": "yellow",
            "low": "red",
        }.get(forecast["confidence_level"], "white")

        console.print(
            f"   🎯 Confidence: [{conf_style}]{forecast['confidence_level'].replace('_', ' ').title()}[/{conf_style}]"
        )

        if forecast["delay_probability"] > 0:
            delay_style = (
                "red"
                if forecast["delay_probability"] > 0.6
                else "yellow" if forecast["delay_probability"] > 0.3 else "green"
            )
            console.print(
                f"   ⚠️  Delay Risk: [{delay_style}]{forecast['delay_probability']*100:.0f}%[/{delay_style}]"
            )

        console.print()

        # Risk analysis summary
        risk_analysis = report["risk_analysis"]
        console.print("⚠️  Risk Analysis", style="bold red")
        console.print(f"   📊 Total Risks: {risk_analysis['total_risks_identified']}")
        console.print(f"   🚨 High Priority: {risk_analysis['high_priority_risks']}")

        if risk_analysis["top_risks"]:
            console.print("   🔥 Top Risks:")
            for risk in risk_analysis["top_risks"][:3]:
                level_emoji = {
                    "critical": "🔴",
                    "high": "🟠",
                    "medium": "🟡",
                    "low": "🟢",
                }.get(risk["level"], "⚪")
                console.print(f"      {level_emoji} {risk['description']}")

        console.print()

        # Work estimates summary
        estimates = report["work_estimates"]
        console.print("📊 Work Analysis", style="bold white")
        console.print(f"   📝 Active Issues: {estimates['total_issues']}")
        console.print(f"   ⏱️  Total Hours: {estimates['total_estimated_hours']:.1f}")
        console.print(f"   📅 Working Days: {estimates['total_estimated_hours']/8:.1f}")

        if estimates["high_uncertainty_issues"]:
            console.print(
                f"   ⚠️  High Uncertainty: {estimates['high_uncertainty_issues']} issues",
                style="orange1",
            )

        avg_conf = estimates["average_confidence"]
        conf_color = "green" if avg_conf > 70 else "yellow" if avg_conf > 50 else "red"
        console.print(
            f"   🎯 Avg Confidence: [{conf_color}]{avg_conf:.0f}%[/{conf_color}]"
        )

        console.print()

        # Key recommendations
        if report["optimization_recommendations"]:
            console.print("💡 Key Recommendations", style="bold yellow")
            for rec in report["optimization_recommendations"][:5]:
                console.print(f"   • {rec}", style="yellow")
            console.print()

        # Critical path
        if report["critical_path"]:
            console.print("🔥 Critical Path", style="bold red")
            for issue_id in report["critical_path"][:5]:
                try:
                    issue = core.get_issue(issue_id)
                    if issue:
                        console.print(f"   • {issue.id}: {issue.title[:50]}...")
                except:
                    console.print(f"   • {issue_id}")

            if len(report["critical_path"]) > 5:
                console.print(f"   ... and {len(report['critical_path']) - 5} more")

        console.print()

        # Resource constraints
        if (
            report["resource_constraints"]
            and report["resource_constraints"][0]
            != "No significant resource constraints identified"
        ):
            console.print("⚠️  Resource Constraints", style="bold orange1")
            for constraint in report["resource_constraints"]:
                console.print(f"   • {constraint}", style="orange1")
            console.print()

        # Save confirmation
        if save and "error" not in report:
            console.print(f"💾 Full intelligence report saved to {save}", style="green")
            console.print(
                "   📊 Includes detailed estimates, risk analysis, and forecasts",
                style="dim",
            )

        console.print()
        console.print(
            "🎯 Use individual predict commands for detailed analysis:",
            style="bold cyan",
        )
        console.print("   • roadmap predict estimate --all", style="cyan")
        console.print("   • roadmap predict risks --level high", style="cyan")
        console.print("   • roadmap predict deadline --target YYYY-MM-DD", style="cyan")

    except Exception as e:
        console.print(
            f"❌ Failed to generate intelligence report: {e}", style="bold red"
        )


# Helper function for export file extensions
def _get_file_extension(format: str) -> str:
    """Get the correct file extension for export format."""
    extension_map = {"csv": "csv", "excel": "xlsx", "json": "json"}
    return extension_map.get(format, format)


def _get_export_path(
    core: RoadmapCore, output: Optional[str], prefix: str, format: str
) -> Path:
    """Generate export path, defaulting to artifacts directory if no output specified."""
    if output:
        # User specified a path - validate it for security
        output_path = Path(output)

        # Check for path traversal and other dangerous patterns
        if any(".." in part for part in output_path.parts):
            log_security_event(
                "path_traversal_blocked",
                {
                    "original_path": str(output_path),
                    "reason": "Directory traversal detected",
                },
            )
            # Sanitize the entire path by taking only the filename
            sanitized_name = sanitize_filename(output_path.name)
            output_path = Path(sanitized_name)
        else:
            # Sanitize the filename component only if no traversal detected
            sanitized_name = sanitize_filename(output_path.name)
            if sanitized_name != output_path.name:
                log_security_event(
                    "filename_sanitized_in_export",
                    {"original": output_path.name, "sanitized": sanitized_name},
                )
                output_path = output_path.parent / sanitized_name

        return output_path

    # Generate default path in artifacts directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    extension = _get_file_extension(format)
    filename = f"{prefix}-{timestamp}.{extension}"

    # Sanitize the generated filename (should be safe, but be defensive)
    filename = sanitize_filename(filename)

    # Ensure artifacts directory and format subdirectory exist
    if core.is_initialized():
        core.artifacts_dir.mkdir(exist_ok=True)
        
        # Create subdirectory based on format
        format_subdir = None
        if format in ["csv"]:
            format_subdir = core.artifacts_dir / "csv"
        elif format in ["excel", "xlsx"]:
            format_subdir = core.artifacts_dir / "excel"
        elif format in ["json"]:
            format_subdir = core.artifacts_dir / "json"
        else:
            # Default to artifacts root for unknown formats
            format_subdir = core.artifacts_dir
        
        format_subdir.mkdir(exist_ok=True)
        return format_subdir / filename
    else:
        # Fallback to current directory if not initialized
        return Path(filename)


# Export Command Group
@main.group("export")
def export():
    """📊 Export roadmap data to various formats (CSV, Excel, JSON).

    🔬 EXPERIMENTAL: Advanced data export with pandas integration

    Export your roadmap data for analysis, reporting, and integration
    with other tools. Supports filtering, advanced queries, and
    multiple output formats.
    """
    pass


@export.command("issues")
@click.option(
    "--format",
    "-f",
    type=click.Choice(["csv", "excel", "json"]),
    default="csv",
    help="Export format",
)
@click.option(
    "--output", "-o", help="Output file path (auto-generated if not provided)"
)
@click.option("--milestone", "-m", help="Filter by milestone")
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
@click.option("--assignee", "-a", help="Filter by assignee")
@click.option("--labels", help="Filter by labels (comma-separated)")
@click.option("--date-from", help="Filter issues created from date (YYYY-MM-DD)")
@click.option("--date-to", help="Filter issues created to date (YYYY-MM-DD)")
@click.option("--completed-from", help="Filter issues completed from date (YYYY-MM-DD)")
@click.option("--completed-to", help="Filter issues completed to date (YYYY-MM-DD)")
@click.option("--search", help="Search text in title and content")
@click.pass_context
def export_issues(
    ctx: click.Context,
    format: str,
    output: str,
    milestone: str,
    status: str,
    priority: str,
    assignee: str,
    labels: str,
    date_from: str,
    date_to: str,
    completed_from: str,
    completed_to: str,
    search: str,
):
    """Export issues to CSV, Excel, or JSON format.

    🔬 EXPERIMENTAL: Advanced data export with filtering and analysis

    Examples:
        roadmap export issues --format excel --milestone "v1.0"
        roadmap export issues --format csv --status done --assignee john
        roadmap export issues --format json --search "authentication"
    """
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return

    try:
        console.print("📊 Exporting issues...", style="bold blue")

        # Get all issues
        issues = core.list_issues()

        if not issues:
            console.print("📋 No issues found to export", style="dim")
            return

        # Convert to DataFrame
        df = DataFrameAdapter.issues_to_dataframe(issues)

        # Apply filters
        filters = {}
        if milestone:
            filters["milestone"] = milestone
        if status:
            filters["status"] = status
        if priority:
            filters["priority"] = priority
        if assignee:
            filters["assignee"] = assignee

        if filters:
            df = QueryBuilder.filter_by_criteria(df, **filters)

        # Date filters
        from datetime import datetime

        if date_from or date_to:
            start_date = datetime.fromisoformat(date_from) if date_from else None
            end_date = datetime.fromisoformat(date_to) if date_to else None
            df = QueryBuilder.filter_by_date_range(df, "created", start_date, end_date)

        if completed_from or completed_to:
            start_date = (
                datetime.fromisoformat(completed_from) if completed_from else None
            )
            end_date = datetime.fromisoformat(completed_to) if completed_to else None
            df = QueryBuilder.filter_by_date_range(
                df, "actual_end_date", start_date, end_date
            )

        # Label filter
        if labels:
            label_list = [l.strip() for l in labels.split(",")]
            mask = df["labels"].str.contains("|".join(label_list), case=False, na=False)
            df = df[mask]

        # Text search
        if search:
            df = QueryBuilder.search_text(df, search, ["title", "content"])

        if df.empty:
            console.print("📋 No issues match the specified filters", style="dim")
            return

        # Generate export path (defaults to artifacts directory)
        output_path = _get_export_path(core, output, "roadmap-issues", format)

        # Export based on format
        if format == "csv":
            DataFrameAdapter.export_to_csv(df, output_path)
        elif format == "excel":
            DataFrameAdapter.export_to_excel(df, output_path, sheet_name="Issues")
        elif format == "json":
            DataFrameAdapter.export_to_json(df, output_path)

        console.print(
            f"✅ Exported {len(df)} issues to {output_path.name}", style="bold green"
        )
        console.print(f"📁 Full path: {output_path.absolute()}", style="dim")

        # Show summary
        console.print()
        console.print("📊 Export Summary:", style="bold")
        console.print(f"   • Total issues: {len(df)}")
        console.print(f"   • Format: {format.upper()}")
        if filters:
            console.print(
                f"   • Filters applied: {', '.join(f'{k}={v}' for k, v in filters.items())}"
            )

    except Exception as e:
        console.print(f"❌ Failed to export issues: {e}", style="bold red")


@export.command("milestones")
@click.option(
    "--format",
    "-f",
    type=click.Choice(["csv", "excel", "json"]),
    default="csv",
    help="Export format",
)
@click.option(
    "--output", "-o", help="Output file path (auto-generated if not provided)"
)
@click.option(
    "--status", "-s", type=click.Choice(["open", "closed"]), help="Filter by status"
)
@click.option("--due-from", help="Filter milestones due from date (YYYY-MM-DD)")
@click.option("--due-to", help="Filter milestones due to date (YYYY-MM-DD)")
@click.pass_context
def export_milestones(
    ctx: click.Context,
    format: str,
    output: str,
    status: str,
    due_from: str,
    due_to: str,
):
    """Export milestones to CSV, Excel, or JSON format.

    🔬 EXPERIMENTAL: Advanced data export with calculated metrics

    Examples:
        roadmap export milestones --format excel
        roadmap export milestones --format csv --status open
    """
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return

    try:
        console.print("📊 Exporting milestones...", style="bold blue")

        # Get all milestones and issues
        milestones = core.list_milestones()
        issues = core.list_issues()

        if not milestones:
            console.print("📋 No milestones found to export", style="dim")
            return

        # Convert to DataFrame
        df = DataFrameAdapter.milestones_to_dataframe(milestones, issues)

        # Apply filters
        if status:
            df = df[df["status"] == status]

        # Date filters
        from datetime import datetime

        if due_from or due_to:
            start_date = datetime.fromisoformat(due_from) if due_from else None
            end_date = datetime.fromisoformat(due_to) if due_to else None
            df = QueryBuilder.filter_by_date_range(df, "due_date", start_date, end_date)

        if df.empty:
            console.print("📋 No milestones match the specified filters", style="dim")
            return

        # Generate export path (defaults to artifacts directory)
        output_path = _get_export_path(core, output, "roadmap-milestones", format)

        # Export based on format
        if format == "csv":
            DataFrameAdapter.export_to_csv(df, output_path)
        elif format == "excel":
            DataFrameAdapter.export_to_excel(df, output_path, sheet_name="Milestones")
        elif format == "json":
            DataFrameAdapter.export_to_json(df, output_path)

        console.print(
            f"✅ Exported {len(df)} milestones to {output_path.name}",
            style="bold green",
        )
        console.print(f"📁 Full path: {output_path.absolute()}", style="dim")

        # Show summary
        console.print()
        console.print("📊 Export Summary:", style="bold")
        console.print(f"   • Total milestones: {len(df)}")
        console.print(f"   • Format: {format.upper()}")
        console.print(f"   • Total issues across milestones: {df['issue_count'].sum()}")
        console.print(
            f"   • Average completion: {df['completion_percentage'].mean():.1f}%"
        )

    except Exception as e:
        console.print(f"❌ Failed to export milestones: {e}", style="bold red")


@export.command("analytics")
@click.option(
    "--format",
    "-f",
    type=click.Choice(["csv", "excel", "json"]),
    default="excel",
    help="Export format",
)
@click.option(
    "--output", "-o", help="Output file path (auto-generated if not provided)"
)
@click.option(
    "--period",
    "-p",
    type=click.Choice(["D", "W", "M", "Q"]),
    default="W",
    help="Analysis period (D=daily, W=weekly, M=monthly, Q=quarterly)",
)
@click.option(
    "--days", "-d", type=int, default=90, help="Number of days of history to analyze"
)
@click.pass_context
def export_analytics(
    ctx: click.Context, format: str, output: str, period: str, days: int
):
    """Export comprehensive analytics to Excel with multiple sheets.

    🔬 EXPERIMENTAL: Advanced analytics export with multiple data views

    Creates a comprehensive analytics export with:
    - Issues data with all fields
    - Milestones with calculated metrics
    - Velocity trends over time
    - Team performance analysis
    - Milestone health assessment
    - Bottleneck identification

    Examples:
        roadmap export analytics --format excel
        roadmap export analytics --period M --days 180
    """
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return

    try:
        console.print(
            "📊 Generating comprehensive analytics export...", style="bold blue"
        )

        # Get all data
        issues = core.list_issues()
        milestones = core.list_milestones()

        if not issues:
            console.print("📋 No data found to export", style="dim")
            return

        # Convert to DataFrames
        issues_df = DataFrameAdapter.issues_to_dataframe(issues)
        milestones_df = DataFrameAdapter.milestones_to_dataframe(milestones, issues)

        # Generate analytics
        velocity_df = DataAnalyzer.analyze_velocity_trends(issues_df, period)
        team_df = DataAnalyzer.analyze_team_performance(issues_df)
        health_df = DataAnalyzer.analyze_milestone_health(milestones_df)
        bottlenecks = DataAnalyzer.find_bottlenecks(issues_df)

        # Generate export path (defaults to artifacts directory)
        output_path = _get_export_path(core, output, "roadmap-analytics", format)

        if format == "excel":
            # Create multi-sheet Excel export
            data_sheets = {
                "Issues": issues_df,
                "Milestones": milestones_df,
            }

            if not velocity_df.empty:
                data_sheets["Velocity_Trends"] = velocity_df
            if not team_df.empty:
                data_sheets["Team_Performance"] = team_df
            if not health_df.empty:
                data_sheets["Milestone_Health"] = health_df

            # Add bottlenecks as a summary sheet
            if bottlenecks:
                bottleneck_data = []
                for category, data in bottlenecks.items():
                    if isinstance(data, dict):
                        for key, value in data.items():
                            bottleneck_data.append(
                                {"category": category, "item": key, "value": value}
                            )
                    else:
                        bottleneck_data.append(
                            {"category": category, "item": "count", "value": data}
                        )

                if bottleneck_data:
                    data_sheets["Bottlenecks"] = pd.DataFrame(bottleneck_data)

            DataFrameAdapter.export_multiple_sheets(data_sheets, output_path)

        elif format == "csv":
            # Export main issues data for CSV
            DataFrameAdapter.export_to_csv(issues_df, output_path)

        elif format == "json":
            # Create combined JSON export
            export_data = {
                "issues": issues_df.to_dict("records"),
                "milestones": milestones_df.to_dict("records"),
                "velocity_trends": (
                    velocity_df.to_dict("records") if not velocity_df.empty else []
                ),
                "team_performance": (
                    team_df.to_dict("records") if not team_df.empty else []
                ),
                "milestone_health": (
                    health_df.to_dict("records") if not health_df.empty else []
                ),
                "bottlenecks": bottlenecks,
                "export_metadata": {
                    "export_date": datetime.now().isoformat(),
                    "period": period,
                    "days_analyzed": days,
                    "total_issues": len(issues_df),
                    "total_milestones": len(milestones_df),
                },
            }

            with create_secure_file(output_path, "w") as f:
                import json

                json.dump(export_data, f, indent=2, default=str)

        console.print(
            f"✅ Exported comprehensive analytics to {output_path.name}",
            style="bold green",
        )
        console.print(f"📁 Full path: {output_path.absolute()}", style="dim")

        # Show summary
        console.print()
        console.print("📊 Analytics Export Summary:", style="bold")
        console.print(f"   • Issues analyzed: {len(issues_df)}")
        console.print(f"   • Milestones: {len(milestones_df)}")
        console.print(f"   • Period: {period} (last {days} days)")
        console.print(f"   • Format: {format.upper()}")

        if format == "excel":
            console.print(f"   • Sheets created: {len(data_sheets)}")
            console.print(
                "   • Includes: Issues, Milestones, Velocity, Team Performance, Health"
            )

        if bottlenecks:
            console.print(f"   • Bottlenecks identified: {len(bottlenecks)} categories")

    except Exception as e:
        console.print(f"❌ Failed to export analytics: {e}", style="bold red")


# Visualization commands
@main.group()
def visualize():
    """📊 Generate charts and visualizations from roadmap data."""
    pass


@visualize.command("status")
@click.option(
    "--chart-type",
    "-t",
    type=click.Choice(["pie", "bar", "donut"]),
    default="donut",
    help="Type of chart to generate",
)
@click.option(
    "--format",
    "-f",
    type=click.Choice(["png", "html", "svg"]),
    default="html",
    help="Output format",
)
@click.option(
    "--output", "-o", help="Output file path (auto-generated if not provided)"
)
@click.option("--milestone", "-m", help="Filter issues by milestone")
@click.option("--assignee", "-a", help="Filter issues by assignee")
@click.pass_context
def visualize_status(
    ctx: click.Context,
    chart_type: str,
    format: str,
    output: str,
    milestone: str,
    assignee: str,
):
    """Generate status distribution chart.

    Creates visual charts showing the distribution of issues across different statuses
    (todo, in-progress, blocked, review, done). Useful for understanding project health
    and identifying bottlenecks.

    Examples:
        roadmap visualize status --chart-type donut --format html
        roadmap visualize status --chart-type bar --milestone "v1.0"
        roadmap visualize status --assignee john --format png
    """
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return

    try:
        console.print("📊 Generating status distribution chart...", style="bold blue")

        # Get and filter issues
        issues = core.list_issues()

        if milestone:
            issues = [i for i in issues if i.milestone == milestone]
            console.print(f"🎯 Filtered to milestone: {milestone}")

        if assignee:
            issues = [i for i in issues if i.assignee == assignee]
            console.print(f"👤 Filtered to assignee: {assignee}")

        if not issues:
            console.print("📋 No issues found with the specified filters", style="dim")
            return

        # Generate chart
        chart_gen = ChartGenerator(core.artifacts_dir)
        output_path = chart_gen.generate_status_distribution_chart(
            issues, chart_type=chart_type, output_format=format
        )

        # Handle custom output path
        if output:
            custom_path = Path(output)
            custom_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.rename(custom_path)
            output_path = custom_path

        console.print(
            f"✅ Status chart generated: {output_path.name}", style="bold green"
        )
        console.print(f"📁 Location: {output_path.absolute()}", style="dim")
        console.print(f"📊 Chart type: {chart_type}, Format: {format}", style="cyan")
        console.print(f"📋 Issues analyzed: {len(issues)}", style="cyan")

    except VisualizationError as e:
        console.print(f"❌ Visualization error: {e}", style="bold red")
    except Exception as e:
        console.print(f"❌ Failed to generate status chart: {e}", style="bold red")


@visualize.command("burndown")
@click.option(
    "--format",
    "-f",
    type=click.Choice(["png", "html", "svg"]),
    default="html",
    help="Output format",
)
@click.option(
    "--output", "-o", help="Output file path (auto-generated if not provided)"
)
@click.option("--milestone", "-m", help="Generate burndown for specific milestone")
@click.pass_context
def visualize_burndown(ctx: click.Context, format: str, output: str, milestone: str):
    """Generate burndown chart showing work remaining over time.

    Creates a burndown chart that shows the ideal vs actual work completion rate.
    Helps track progress against planned timelines and identify velocity issues.

    Examples:
        roadmap visualize burndown --milestone "Sprint 1"
        roadmap visualize burndown --format png
    """
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return

    try:
        console.print("📈 Generating burndown chart...", style="bold blue")

        # Get issues
        issues = core.list_issues()

        if milestone:
            console.print(f"🎯 Analyzing milestone: {milestone}")

        if not issues:
            console.print("📋 No issues found", style="dim")
            return

        # Generate chart
        chart_gen = ChartGenerator(core.artifacts_dir)
        output_path = chart_gen.generate_burndown_chart(
            issues, milestone_name=milestone, output_format=format
        )

        # Handle custom output path
        if output:
            custom_path = Path(output)
            custom_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.rename(custom_path)
            output_path = custom_path

        console.print(
            f"✅ Burndown chart generated: {output_path.name}", style="bold green"
        )
        console.print(f"📁 Location: {output_path.absolute()}", style="dim")
        console.print(f"📊 Format: {format}", style="cyan")
        if milestone:
            console.print(f"🎯 Milestone: {milestone}", style="cyan")

    except VisualizationError as e:
        console.print(f"❌ Visualization error: {e}", style="bold red")
    except Exception as e:
        console.print(f"❌ Failed to generate burndown chart: {e}", style="bold red")


@visualize.command("velocity")
@click.option(
    "--format",
    "-f",
    type=click.Choice(["png", "html", "svg"]),
    default="html",
    help="Output format",
)
@click.option(
    "--output", "-o", help="Output file path (auto-generated if not provided)"
)
@click.option(
    "--period",
    "-p",
    type=click.Choice(["D", "W", "M"]),
    default="W",
    help="Time period for analysis (D=daily, W=weekly, M=monthly)",
)
@click.pass_context
def visualize_velocity(ctx: click.Context, format: str, output: str, period: str):
    """Generate team velocity trends chart.

    Shows how team velocity (issues completed and velocity score) changes over time.
    Helps identify productivity trends and plan future work capacity.

    Examples:
        roadmap visualize velocity --period W
        roadmap visualize velocity --period M --format png
    """
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return

    try:
        console.print("🚀 Generating velocity chart...", style="bold blue")

        # Get issues
        issues = core.list_issues()

        if not issues:
            console.print("📋 No issues found", style="dim")
            return

        # Generate chart
        chart_gen = ChartGenerator(core.artifacts_dir)
        output_path = chart_gen.generate_velocity_chart(
            issues, period=period, output_format=format
        )

        # Handle custom output path
        if output:
            custom_path = Path(output)
            custom_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.rename(custom_path)
            output_path = custom_path

        period_name = {"D": "Daily", "W": "Weekly", "M": "Monthly"}[period]

        console.print(
            f"✅ Velocity chart generated: {output_path.name}", style="bold green"
        )
        console.print(f"📁 Location: {output_path.absolute()}", style="dim")
        console.print(f"📊 Format: {format}, Period: {period_name}", style="cyan")
        console.print(f"📋 Issues analyzed: {len(issues)}", style="cyan")

    except VisualizationError as e:
        console.print(f"❌ Visualization error: {e}", style="bold red")
    except Exception as e:
        console.print(f"❌ Failed to generate velocity chart: {e}", style="bold red")


@visualize.command("milestones")
@click.option(
    "--format",
    "-f",
    type=click.Choice(["png", "html", "svg"]),
    default="html",
    help="Output format",
)
@click.option(
    "--output", "-o", help="Output file path (auto-generated if not provided)"
)
@click.pass_context
def visualize_milestones(ctx: click.Context, format: str, output: str):
    """Generate milestone progress overview chart.

    Shows progress for all milestones with completion percentages and issue counts.
    Provides a high-level view of project milestone health and completion status.

    Examples:
        roadmap visualize milestones
        roadmap visualize milestones --format png
    """
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return

    try:
        console.print("🎯 Generating milestone progress chart...", style="bold blue")

        # Get milestones and issues
        milestones = core.list_milestones()
        issues = core.list_issues()

        if not milestones:
            console.print("📋 No milestones found", style="dim")
            return

        # Generate chart
        chart_gen = ChartGenerator(core.artifacts_dir)
        output_path = chart_gen.generate_milestone_progress_chart(
            milestones, issues, output_format=format
        )

        # Handle custom output path
        if output:
            custom_path = Path(output)
            custom_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.rename(custom_path)
            output_path = custom_path

        console.print(
            f"✅ Milestone chart generated: {output_path.name}", style="bold green"
        )
        console.print(f"📁 Location: {output_path.absolute()}", style="dim")
        console.print(f"📊 Format: {format}", style="cyan")
        console.print(f"🎯 Milestones analyzed: {len(milestones)}", style="cyan")

    except VisualizationError as e:
        console.print(f"❌ Visualization error: {e}", style="bold red")
    except Exception as e:
        console.print(f"❌ Failed to generate milestone chart: {e}", style="bold red")


@visualize.command("team")
@click.option(
    "--format",
    "-f",
    type=click.Choice(["png", "html", "svg"]),
    default="html",
    help="Output format",
)
@click.option(
    "--output", "-o", help="Output file path (auto-generated if not provided)"
)
@click.pass_context
def visualize_team(ctx: click.Context, format: str, output: str):
    """Generate team workload distribution chart.

    Shows workload distribution across team members including issue counts
    and estimated hours. Helps identify workload imbalances and capacity planning.

    Examples:
        roadmap visualize team
        roadmap visualize team --format png
    """
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return

    try:
        console.print("👥 Generating team workload chart...", style="bold blue")

        # Get issues
        issues = core.list_issues()

        if not issues:
            console.print("📋 No issues found", style="dim")
            return

        # Generate chart
        chart_gen = ChartGenerator(core.artifacts_dir)
        output_path = chart_gen.generate_team_workload_chart(
            issues, output_format=format
        )

        # Handle custom output path
        if output:
            custom_path = Path(output)
            custom_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.rename(custom_path)
            output_path = custom_path

        console.print(
            f"✅ Team workload chart generated: {output_path.name}", style="bold green"
        )
        console.print(f"📁 Location: {output_path.absolute()}", style="dim")
        console.print(f"📊 Format: {format}", style="cyan")
        console.print(f"📋 Issues analyzed: {len(issues)}", style="cyan")

    except VisualizationError as e:
        console.print(f"❌ Visualization error: {e}", style="bold red")
    except Exception as e:
        console.print(f"❌ Failed to generate team chart: {e}", style="bold red")


@visualize.command("dashboard")
@click.option(
    "--output", "-o", help="Output file path (auto-generated if not provided)"
)
@click.option("--milestone", "-m", help="Filter issues by milestone")
@click.pass_context
def visualize_dashboard(ctx: click.Context, output: str, milestone: str):
    """Generate comprehensive stakeholder dashboard.

    Creates an interactive HTML dashboard combining multiple visualizations
    including status distribution, milestone progress, velocity trends, and
    team workload. Perfect for stakeholder presentations and executive reports.

    Examples:
        roadmap visualize dashboard
        roadmap visualize dashboard --milestone "v1.0"
        roadmap visualize dashboard --output stakeholder_report.html
    """
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return

    try:
        console.print(
            "🚀 Generating comprehensive stakeholder dashboard...", style="bold blue"
        )

        # Get data
        issues = core.list_issues()
        milestones = core.list_milestones()

        if milestone:
            issues = [i for i in issues if i.milestone == milestone]
            milestones = [m for m in milestones if m.name == milestone]
            console.print(f"🎯 Filtered to milestone: {milestone}")

        if not issues:
            console.print("📋 No issues found with the specified filters", style="dim")
            return

        # Generate dashboard
        dashboard_gen = DashboardGenerator(core.artifacts_dir)
        output_path = dashboard_gen.generate_stakeholder_dashboard(issues, milestones)

        # Handle custom output path
        if output:
            custom_path = Path(output)
            custom_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.rename(custom_path)
            output_path = custom_path

        console.print(f"✅ Dashboard generated: {output_path.name}", style="bold green")
        console.print(f"📁 Location: {output_path.absolute()}", style="dim")
        console.print(
            f"📊 Includes: Status, Milestones, Velocity, Team Workload", style="cyan"
        )
        console.print(
            f"📋 Issues: {len(issues)}, Milestones: {len(milestones)}", style="cyan"
        )

        # Show how to open
        console.print("\n💡 To view the dashboard:", style="yellow")
        console.print(
            f"   Open in browser: file://{output_path.absolute()}", style="dim"
        )

    except VisualizationError as e:
        console.print(f"❌ Visualization error: {e}", style="bold red")
    except Exception as e:
        console.print(f"❌ Failed to generate dashboard: {e}", style="bold red")


@main.command("project-overview")
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    help="Custom output directory for project analysis artifacts",
)
@click.option(
    "--format",
    "-f",
    type=click.Choice(["rich", "json", "csv"]),
    default="rich",
    help="Output format for project analysis",
)
@click.option(
    "--include-charts",
    is_flag=True,
    default=True,
    help="Generate visualization charts with the analysis",
)
@click.pass_context
def project_overview(ctx: click.Context, output: Optional[str], format: str, include_charts: bool) -> None:
    """Comprehensive project-level analysis and reporting.
    
    Provides high-level insights into project progress, milestone progression,
    technical debt indicators, team workload, and overall project health.
    """
    try:
        core = ctx.obj.get("core")
        if not core:
            console.print("❌ No roadmap found. Run 'roadmap init' first.", style="bold red")
            return

        console.print("🔍 Analyzing project...", style="bold blue")
        
        # Get all data
        issues = core.list_issues()
        milestones = core.list_milestones()
        
        if not issues:
            console.print("📝 No issues found in the project.", style="yellow")
            return
            
        if not milestones:
            console.print("📅 No milestones found in the project.", style="yellow")
            return

        # Initialize analyzers
        analyzer = EnhancedAnalyzer(core)
        chart_gen = ChartGenerator(core.artifacts_dir)
        
        # Project-level metrics
        total_issues = len(issues)
        closed_issues = len([i for i in issues if i.status == Status.DONE])
        open_issues = total_issues - closed_issues
        completion_rate = (closed_issues / total_issues * 100) if total_issues > 0 else 0
        
        # Issue type distribution
        issue_types = {}
        for issue in issues:
            issue_types[issue.issue_type] = issue_types.get(issue.issue_type, 0) + 1
        
        # Technical debt indicators
        bugs_open = len([i for i in issues if i.issue_type == IssueType.BUG and i.status != Status.DONE])
        bugs_total = len([i for i in issues if i.issue_type == IssueType.BUG])
        tech_debt_ratio = (bugs_open / bugs_total * 100) if bugs_total > 0 else 0
        
        # Team workload
        assigned_issues = [i for i in issues if i.assignee and i.status != Status.DONE]
        assignee_workload = {}
        for issue in assigned_issues:
            assignee_workload[issue.assignee] = assignee_workload.get(issue.assignee, 0) + 1
        
        # Milestone progression analysis
        milestone_stats = []
        for milestone in sorted(milestones, key=lambda m: m.due_date or datetime.max):
            milestone_issues = [i for i in issues if i.milestone == milestone.name]
            milestone_closed = len([i for i in milestone_issues if i.status == Status.DONE])
            milestone_total = len(milestone_issues)
            milestone_completion = (milestone_closed / milestone_total * 100) if milestone_total > 0 else 0
            
            # Issue type breakdown for this milestone
            milestone_bugs = len([i for i in milestone_issues if i.issue_type == IssueType.BUG])
            milestone_features = len([i for i in milestone_issues if i.issue_type == IssueType.FEATURE])
            milestone_tasks = len([i for i in milestone_issues if i.issue_type == IssueType.OTHER])
            
            milestone_stats.append({
                'milestone': milestone.name,
                'due_date': milestone.due_date,
                'completion': milestone_completion,
                'total_issues': milestone_total,
                'closed_issues': milestone_closed,
                'bugs': milestone_bugs,
                'features': milestone_features,
                'tasks': milestone_tasks,
                'status': 'completed' if milestone_completion == 100 else 'in_progress' if milestone_completion > 0 else 'planned'
            })

        if format == "rich":
            # Display comprehensive project overview
            console.print("\n" + "="*80, style="bold blue")
            console.print("📊 PROJECT OVERVIEW", style="bold blue", justify="center")
            console.print("="*80, style="bold blue")
            
            # Overall stats panel
            stats_table = Table(title="📈 Overall Project Statistics", show_header=True, header_style="bold magenta")
            stats_table.add_column("Metric", style="cyan", min_width=20)
            stats_table.add_column("Value", style="white", min_width=15)
            stats_table.add_column("Indicator", style="green", min_width=10)
            
            stats_table.add_row("Total Issues", str(total_issues), "📊")
            stats_table.add_row("Completed", f"{closed_issues} ({completion_rate:.1f}%)", "✅" if completion_rate > 70 else "⚠️" if completion_rate > 40 else "❌")
            stats_table.add_row("Open Issues", str(open_issues), "📝")
            stats_table.add_row("Open Bugs", f"{bugs_open} ({tech_debt_ratio:.1f}%)", "🐛" if tech_debt_ratio < 20 else "⚠️" if tech_debt_ratio < 40 else "🚨")
            stats_table.add_row("Milestones", str(len(milestones)), "🎯")
            
            console.print(stats_table)
            console.print()
            
            # Milestone progression
            milestone_table = Table(title="🎯 Milestone Progression", show_header=True, header_style="bold magenta")
            milestone_table.add_column("Milestone", style="cyan", min_width=15)
            milestone_table.add_column("Due Date", style="white", min_width=12)
            milestone_table.add_column("Progress", style="white", min_width=15)
            milestone_table.add_column("Issues", style="white", min_width=15)
            milestone_table.add_column("Bugs", style="red", min_width=8)
            milestone_table.add_column("Features", style="green", min_width=10)
            milestone_table.add_column("Tasks", style="blue", min_width=8)
            milestone_table.add_column("Status", style="white", min_width=12)
            
            for stats in milestone_stats:
                due_str = stats['due_date'].strftime('%Y-%m-%d') if stats['due_date'] else "No date"
                progress_str = f"{stats['completion']:.1f}% ({stats['closed_issues']}/{stats['total_issues']})"
                status_emoji = "✅" if stats['status'] == 'completed' else "🚧" if stats['status'] == 'in_progress' else "📋"
                
                milestone_table.add_row(
                    stats['milestone'],
                    due_str,
                    progress_str,
                    str(stats['total_issues']),
                    str(stats['bugs']),
                    str(stats['features']),
                    str(stats['tasks']),
                    f"{status_emoji} {stats['status'].replace('_', ' ').title()}"
                )
            
            console.print(milestone_table)
            console.print()
            
            # Team workload
            if assignee_workload:
                workload_table = Table(title="👥 Team Workload (Open Issues)", show_header=True, header_style="bold magenta")
                workload_table.add_column("Team Member", style="cyan", min_width=20)
                workload_table.add_column("Open Issues", style="white", min_width=15)
                workload_table.add_column("Load Level", style="white", min_width=15)
                
                avg_workload = sum(assignee_workload.values()) / len(assignee_workload) if assignee_workload else 0
                
                for assignee, count in sorted(assignee_workload.items(), key=lambda x: x[1], reverse=True):
                    load_indicator = "🔥 Heavy" if count > avg_workload * 1.5 else "⚖️ Balanced" if count > avg_workload * 0.5 else "🕊️ Light"
                    workload_table.add_row(assignee, str(count), load_indicator)
                
                console.print(workload_table)
                console.print()
            
            # Issue type distribution
            type_table = Table(title="📋 Issue Type Distribution", show_header=True, header_style="bold magenta")
            type_table.add_column("Issue Type", style="cyan", min_width=15)
            type_table.add_column("Count", style="white", min_width=10)
            type_table.add_column("Percentage", style="white", min_width=12)
            
            for issue_type, count in sorted(issue_types.items(), key=lambda x: x[1], reverse=True):
                percentage = (count / total_issues * 100) if total_issues > 0 else 0
                type_table.add_row(issue_type.value, str(count), f"{percentage:.1f}%")
            
            console.print(type_table)
            
        elif format == "json":
            import json
            project_data = {
                "project_overview": {
                    "total_issues": total_issues,
                    "closed_issues": closed_issues,
                    "open_issues": open_issues,
                    "completion_rate": completion_rate,
                    "tech_debt_ratio": tech_debt_ratio,
                    "milestone_count": len(milestones)
                },
                "milestones": milestone_stats,
                "team_workload": assignee_workload,
                "issue_types": {k.value: v for k, v in issue_types.items()},
                "generated_at": datetime.now().isoformat()
            }
            console.print(json.dumps(project_data, indent=2))
            
        elif format == "csv":
            # Export milestone data as CSV
            df_data = []
            for stats in milestone_stats:
                df_data.append({
                    "Milestone": stats['milestone'],
                    "Due_Date": stats['due_date'].strftime('%Y-%m-%d') if stats['due_date'] else "",
                    "Completion_Percent": stats['completion'],
                    "Total_Issues": stats['total_issues'],
                    "Closed_Issues": stats['closed_issues'],
                    "Bugs": stats['bugs'],
                    "Features": stats['features'],
                    "Tasks": stats['tasks'],
                    "Status": stats['status']
                })
            
            df = pd.DataFrame(df_data)
            csv_output = df.to_csv(index=False)
            console.print(csv_output)
        
        # Generate visualization charts if requested
        if include_charts and format == "rich":
            console.print("\n🎨 Generating project visualization charts...", style="bold blue")
            
            try:
                # Milestone progression chart
                chart_data = []
                for stats in milestone_stats:
                    chart_data.append({
                        'milestone': stats['milestone'],
                        'completion': stats['completion'],
                        'bugs': stats['bugs'],
                        'features': stats['features'],
                        'tasks': stats['tasks']
                    })
                
                output_dir = Path(output) if output else core.artifacts_dir
                output_dir.mkdir(parents=True, exist_ok=True)
                
                # Generate milestone progression flow chart
                chart_path = chart_gen.generate_milestone_progression_chart(chart_data, output_dir)
                console.print(f"📊 Milestone progression chart: {chart_path.name}", style="green")
                
                # Generate project health dashboard
                health_data = {
                    'completion_rate': completion_rate,
                    'tech_debt_ratio': tech_debt_ratio,
                    'milestone_stats': milestone_stats,
                    'team_workload': assignee_workload,
                    'issue_types': {k.value: v for k, v in issue_types.items()}
                }
                
                health_path = chart_gen.generate_project_health_dashboard(health_data, output_dir)
                console.print(f"📈 Project health dashboard: {health_path.name}", style="green")
                
                console.print(f"\n📁 Charts saved to: {output_dir.absolute()}", style="dim")
                
            except Exception as e:
                console.print(f"⚠️ Could not generate charts: {e}", style="yellow")
        
        console.print("\n✅ Project analysis complete!", style="bold green")
        
    except Exception as e:
        console.print(f"❌ Failed to analyze project: {e}", style="bold red")


@main.group()
def project():
    """Manage projects."""
    pass


@project.command("create")
@click.argument("name")
@click.option(
    "--description",
    "-d",
    default="Project description",
    help="Project description",
)
@click.option(
    "--owner",
    "-o",
    help="Project owner",
)
@click.option(
    "--priority",
    "-p",
    type=click.Choice(["critical", "high", "medium", "low"]),
    default="medium",
    help="Project priority",
)
@click.option(
    "--start-date",
    "-s",
    help="Project start date (YYYY-MM-DD)",
)
@click.option(
    "--target-end-date",
    "-e",
    help="Target end date (YYYY-MM-DD)",
)
@click.option(
    "--estimated-hours",
    "-h",
    type=float,
    help="Estimated hours to complete",
)
@click.option(
    "--milestones",
    "-m",
    multiple=True,
    help="Milestone names (can be specified multiple times)",
)
def create_project(
    name: str,
    description: str,
    owner: Optional[str],
    priority: str,
    start_date: Optional[str],
    target_end_date: Optional[str],
    estimated_hours: Optional[float],
    milestones: tuple,
) -> None:
    """Create a new project."""
    try:
        from datetime import datetime
        import uuid
        from pathlib import Path
        
        core = RoadmapCore()
        
        # Generate project ID
        project_id = str(uuid.uuid4())[:8]
        
        # Parse dates
        parsed_start_date = None
        parsed_target_end_date = None
        
        if start_date:
            try:
                parsed_start_date = datetime.strptime(start_date, "%Y-%m-%d").isoformat()
            except ValueError:
                console.print("❌ Invalid start date format. Use YYYY-MM-DD", style="bold red")
                return
                
        if target_end_date:
            try:
                parsed_target_end_date = datetime.strptime(target_end_date, "%Y-%m-%d").isoformat()
            except ValueError:
                console.print("❌ Invalid target end date format. Use YYYY-MM-DD", style="bold red")
                return
        
        # Create projects directory if it doesn't exist
        projects_dir = core.roadmap_dir / "projects"
        projects_dir.mkdir(exist_ok=True)
        
        # Load and process template
        template_path = core.templates_dir / "project.md"
        if not template_path.exists():
            console.print("❌ Project template not found. Run 'roadmap init' first.", style="bold red")
            return
            
        template_content = template_path.read_text()
        
        # Replace template variables
        current_time = datetime.now().isoformat()
        
        # Convert milestones tuple to list for template
        milestone_list = list(milestones) if milestones else ["milestone_1", "milestone_2"]
        
        replacements = {
            "{{ project_id }}": project_id,
            "{{ project_name }}": name,
            "{{ project_description }}": description,
            "{{ project_owner }}": owner or "",
            "{{ start_date }}": parsed_start_date or "",
            "{{ target_end_date }}": parsed_target_end_date or "",
            "{{ created_date }}": current_time,
            "{{ updated_date }}": current_time,
            "{{ estimated_hours }}": str(estimated_hours) if estimated_hours else "0",
            "{{ milestone_1 }}": milestone_list[0] if len(milestone_list) > 0 else "",
            "{{ milestone_2 }}": milestone_list[1] if len(milestone_list) > 1 else "",
        }
        
        project_content = template_content
        for placeholder, value in replacements.items():
            project_content = project_content.replace(placeholder, value)
        
        # Handle priority replacement (template has hardcoded "medium")
        project_content = project_content.replace('priority: "medium"', f'priority: "{priority}"')
        
        # Handle status replacement
        project_content = project_content.replace('**Status:** {{ status }}', f'**Status:** planning')
        
        # Handle milestone list in YAML (more complex replacement)
        if milestones:
            milestone_yaml = "\n".join([f'  - "{milestone}"' for milestone in milestones])
            project_content = project_content.replace(
                'milestones:\n  - "{{ milestone_1}}"\n  - "{{ milestone_2}}"',
                f"milestones:\n{milestone_yaml}"
            )
        
        # Save project file
        project_filename = f"{project_id}-{name.lower().replace(' ', '-')}.md"
        project_path = projects_dir / project_filename
        
        with open(project_path, "w") as f:
            f.write(project_content)
        
        console.print("✅ Created project:", style="bold green")
        console.print(f"   ID: {project_id}")
        console.print(f"   Name: {name}")
        console.print(f"   Priority: {priority}")
        if owner:
            console.print(f"   Owner: {owner}")
        if estimated_hours:
            console.print(f"   Estimated: {estimated_hours}h")
        console.print(f"   File: {project_path.relative_to(core.root_path)}")
        
    except Exception as e:
        console.print(f"❌ Failed to create project: {e}", style="bold red")


@project.command("overview")
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    help="Custom output directory for project analysis artifacts",
)
@click.option(
    "--format",
    "-f",
    type=click.Choice(["rich", "json", "csv"]),
    default="rich",
    help="Output format for project analysis",
)
@click.option(
    "--include-charts",
    is_flag=True,
    default=True,
    help="Generate visualization charts with the analysis",
)
@click.pass_context
def project_overview_subcommand(ctx: click.Context, output: Optional[str], format: str, include_charts: bool) -> None:
    """Comprehensive project-level analysis and reporting."""
    # Call the existing project_overview function
    project_overview(ctx, output, format, include_charts)


if __name__ == "__main__":
    main()
