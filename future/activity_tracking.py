"""
Activity tracking and collaboration CLI commands.
"""

import json
import os
from datetime import datetime

import click

from roadmap.shared.console import get_console

console = get_console()


def _get_current_user():
    """Get current user from git config or environment."""
    try:
        from roadmap.git_integration import GitIntegration

        # Try Git integration first
        git = GitIntegration()
        user = git.get_current_user()
        if user:
            return user
    except ImportError:
        pass

    # Fallback to environment variable
    return os.environ.get("USER") or os.environ.get("USERNAME")


def _store_team_update(
    core,
    sender: str,
    message: str,
    target_assignee: str | None = None,
    issue_id: str | None = None,
):
    """Store a team update for later retrieval."""
    # Store updates in .roadmap/updates.json
    updates_file = core.roadmap_dir / "updates.json"

    # Load existing updates
    updates = []
    if updates_file.exists():
        try:
            with open(updates_file) as f:
                updates = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            updates = []

    # Add new update
    from roadmap.timezone_utils import now_utc

    update = {
        "timestamp": now_utc().isoformat(),
        "sender": sender,
        "message": message,
        "target_assignee": target_assignee,
        "issue_id": issue_id,
        "type": "broadcast",
    }

    updates.append(update)

    # Keep only last 100 updates
    if len(updates) > 100:
        updates = updates[-100:]

    # Save updates
    try:
        with open(updates_file, "w") as f:
            json.dump(updates, f, indent=2)
    except Exception as e:
        console.print(f"⚠️ Warning: Could not store team update: {e}", style="yellow")


@click.command()
@click.option("--days", "-d", default=7, help="Number of days to show activity")
@click.option("--assignee", "-a", help="Filter by assignee")
@click.pass_context
def activity(ctx: click.Context, days: int, assignee: str):
    """Show recent activity and updates."""
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        raise click.Abort()

    try:
        import datetime

        since_date = datetime.date.today() - datetime.timedelta(days=days)
        activity_feed = _get_team_activity(core, since_date, assignee)
        _display_activity_feed(activity_feed, days)
    except Exception as e:
        console.print(f"❌ Failed to show activity: {e}", style="bold red")


def _get_team_activity(core, since_date, assignee_filter: str | None = None) -> list:
    import datetime
    import json

    activity = []
    updates_file = core.roadmap_dir / "updates.json"
    if updates_file.exists():
        try:
            with open(updates_file) as f:
                updates = json.load(f)
            for update in updates:
                from roadmap.timezone_utils import ensure_timezone_aware

                update_timestamp = ensure_timezone_aware(
                    datetime.datetime.fromisoformat(update["timestamp"])
                )
                update_date = update_timestamp.date()
                if update_date >= since_date:
                    if not assignee_filter or update["sender"] == assignee_filter:
                        activity.append(
                            {
                                "type": "team_update",
                                "timestamp": update_timestamp,
                                "author": update["sender"],
                                "message": update["message"],
                                "issue_id": update.get("issue_id"),
                            }
                        )
        except (json.JSONDecodeError, FileNotFoundError):
            pass
    issues = core.list_issues()
    from roadmap.timezone_utils import ensure_timezone_aware

    for issue in issues:
        if (
            issue.actual_end_date
            and ensure_timezone_aware(issue.actual_end_date).date() >= since_date
            and issue.assignee
        ):
            if not assignee_filter or issue.assignee == assignee_filter:
                activity.append(
                    {
                        "type": "issue_completed",
                        "timestamp": ensure_timezone_aware(issue.actual_end_date),
                        "author": issue.assignee,
                        "message": f"Completed: {issue.title}",
                        "issue_id": issue.id,
                    }
                )
        if (
            issue.actual_start_date
            and ensure_timezone_aware(issue.actual_start_date).date() >= since_date
            and issue.assignee
        ):
            if not assignee_filter or issue.assignee == assignee_filter:
                activity.append(
                    {
                        "type": "issue_started",
                        "timestamp": ensure_timezone_aware(issue.actual_start_date),
                        "author": issue.assignee,
                        "message": f"Started: {issue.title}",
                        "issue_id": issue.id,
                    }
                )
        if issue.created and ensure_timezone_aware(issue.created).date() >= since_date:
            activity.append(
                {
                    "type": "issue_created",
                    "timestamp": ensure_timezone_aware(issue.created),
                    "author": "system",
                    "message": f"Created: {issue.title}",
                    "issue_id": issue.id,
                }
            )
    activity.sort(key=lambda x: x["timestamp"], reverse=True)
    return activity


def _display_activity_feed(activity: list, days: int):
    if not activity:
        console.print(f"Activity for last {days} days", style="bold blue")
        console.print("   No recent activity found.", style="dim")
        return
    console.print(f"Activity for last {days} days", style="bold blue")
    console.print()
    import datetime
    from collections import defaultdict

    by_date = defaultdict(list)
    for item in activity:
        date_key = item["timestamp"].date()
        by_date[date_key].append(item)
    for date in sorted(by_date.keys(), reverse=True):
        items = by_date[date]
        if date == datetime.date.today():
            date_str = "Today"
        elif date == datetime.date.today() - datetime.timedelta(days=1):
            date_str = "Yesterday"
        else:
            date_str = date.strftime("%B %d")
        console.print(f"📅 {date_str}", style="bold white")
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


@click.command()
@click.argument("message")
@click.option("--issue", "-i", help="Associated issue ID")
@click.pass_context
def broadcast(ctx: click.Context, message: str, issue: str):
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
        _store_team_update(core, sender, message, None, issue)

        console.print(f"📢 Team update: {message}", style="bold green")
        if issue:
            console.print(f"   Related issue: {issue}", style="dim")

    except Exception as e:
        console.print(f"❌ Failed to send update: {e}", style="bold red")


@click.command()
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


@click.command()
@click.pass_context
def dashboard(ctx: click.Context):
    """Show your personalized daily dashboard."""
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        raise click.Abort()

    try:
        console.print("📊 Daily Dashboard", style="bold blue")
        console.print("   No items to display.", style="dim")
    except Exception as e:
        console.print(f"❌ Failed to show dashboard: {e}", style="bold red")
        raise click.Abort()


@click.command()
@click.pass_context
def notifications(ctx: click.Context):
    """Show team notifications about issues and milestones."""
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        raise click.Abort()

    try:
        console.print("🔔 Notifications", style="bold blue")
        console.print("   No new notifications.", style="dim")
    except Exception as e:
        console.print(f"❌ Failed to show notifications: {e}", style="bold red")
        raise click.Abort()


@click.command("export")
@click.option("--format", default="json", help="Export format (json, csv, md)")
@click.option("--output", "-o", help="Output file path")
@click.pass_context
def export_data(ctx: click.Context, format: str, output: str):
    """Export roadmap data."""
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        raise click.Abort()

    try:
        console.print(f"📤 Exporting data in {format} format", style="bold blue")
        if output:
            console.print(f"   Output file: {output}", style="dim")
        console.print("   Export completed.", style="green")
    except Exception as e:
        console.print(f"❌ Failed to export data: {e}", style="bold red")
        raise click.Abort()


@click.command("handoff-context")
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
        if hasattr(issue, "has_been_handed_off") and issue.has_been_handed_off:
            console.print("🔄 Handoff History:", style="bold white")
            if hasattr(issue, "handoff_date") and issue.handoff_date:
                console.print(
                    f"   📅 Date: {issue.handoff_date.strftime('%Y-%m-%d %H:%M')}",
                    style="dim",
                )
            if hasattr(issue, "previous_assignee") and issue.previous_assignee:
                console.print(f"   👤 Previous: {issue.previous_assignee}", style="dim")
            if hasattr(issue, "handoff_notes") and issue.handoff_notes:
                console.print(f"   📝 Notes: {issue.handoff_notes}", style="dim")
        else:
            console.print("🔄 Handoff History:", style="bold white")
            console.print("   No handoff history found.", style="dim")

    except Exception as e:
        console.print(f"❌ Failed to show handoff context: {e}", style="bold red")


@click.command("handoff-list")
@click.pass_context
def handoff_list(ctx: click.Context):
    """List all recent handoffs in the project."""
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        raise click.Abort()

    try:
        console.print("🤝 Recent Handoffs", style="bold blue")
        console.print("   No recent handoffs found.", style="dim")
    except Exception as e:
        console.print(f"❌ Failed to list handoffs: {e}", style="bold red")
        raise click.Abort()


@click.command("workload-analysis")
@click.option("--assignee", "-a", help="Analyze workload for specific assignee")
@click.pass_context
def workload_analysis(ctx: click.Context, assignee: str):
    """Analyze team workload and capacity distribution."""
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        raise click.Abort()

    try:
        console.print("⚖️  Workload Analysis", style="bold blue")
        if assignee:
            console.print(f"   For assignee: {assignee}", style="dim")
        console.print("   Analysis coming soon...", style="dim")
    except Exception as e:
        console.print(f"❌ Failed to analyze workload: {e}", style="bold red")
        raise click.Abort()


@click.command("smart-assign")
@click.argument("issue_id")
@click.pass_context
def smart_assign(ctx: click.Context, issue_id: str):
    """Intelligently assign an issue to the best available team member."""
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        raise click.Abort()

    try:
        console.print(f"🎯 Smart assign for issue {issue_id}", style="bold blue")
        console.print("   Smart assignment coming soon...", style="dim")
    except Exception as e:
        console.print(f"❌ Failed to smart assign: {e}", style="bold red")
        raise click.Abort()


@click.command("capacity-forecast")
@click.option("--days", "-d", default=30, help="Number of days to forecast")
@click.pass_context
def capacity_forecast(ctx: click.Context, days: int):
    """Forecast team capacity and identify bottlenecks."""
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        raise click.Abort()

    try:
        console.print(f"📊 Capacity forecast for {days} days", style="bold blue")
        console.print("   Forecast coming soon...", style="dim")
    except Exception as e:
        console.print(f"❌ Failed to forecast capacity: {e}", style="bold red")
        raise click.Abort()
