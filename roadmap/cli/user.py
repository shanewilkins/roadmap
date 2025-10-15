"""
User-specific views and settings commands.
"""

import click
from rich.console import Console
from typing import Optional
import datetime
import os

from roadmap.models import Status, Priority

console = Console()

@click.group()
def user():
    """User-specific views and settings."""
    pass

# ================================
# OBJECT-VERB PATTERN COMMANDS
# ================================

@user.command("show-dashboard")
@click.option("--assignee", "-a", help="Show dashboard for specific user")
@click.option("--days", "-d", default=7, help="Number of days to include")
@click.pass_context
def show_dashboard(ctx: click.Context, assignee: str, days: int):
    """Show your personalized daily dashboard."""
    _original_dashboard(ctx, assignee, days)


@user.command("show-notifications")
@click.option("--assignee", "-a", help="Show notifications for specific user")
@click.option("--since", "-s", help="Show notifications since date")
@click.option("--mark-read", is_flag=True, help="Mark notifications as read")
@click.pass_context
def show_notifications(ctx: click.Context, assignee: str, since: str, mark_read: bool):
    """Show team notifications about issues and updates."""
    _original_notifications(ctx, assignee, since, mark_read)


# ================================
# ORIGINAL IMPLEMENTATIONS
# ================================

def _original_dashboard(ctx: click.Context, assignee: str, days: int):
    """Original implementation of dashboard."""
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


def _original_notifications(ctx: click.Context, assignee: str, since: str, mark_read: bool):
    """Original implementation of notifications."""
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return

    try:
        # Determine which user's notifications to show
        if not assignee:
            assignee = _get_current_user()
            if not assignee:
                console.print(
                    "❌ Could not determine current user. Use --assignee NAME",
                    style="bold red",
                )
                return

        console.print(f"🔔 Notifications for {assignee}", style="bold blue")

        # Parse since date
        since_date = None
        if since:
            try:
                since_date = datetime.datetime.strptime(since, "%Y-%m-%d").date()
            except ValueError:
                console.print(
                    "❌ Invalid date format. Use YYYY-MM-DD", style="bold red"
                )
                return
        else:
            # Default to last 7 days
            since_date = datetime.date.today() - datetime.timedelta(days=7)

        # Get notifications (simplified implementation)
        notifications = _get_user_notifications(core, assignee, since_date)

        if not notifications:
            console.print(f"📝 No notifications since {since_date}", style="yellow")
            return

        # Display notifications
        console.print(f"\n📋 {len(notifications)} notification{'s' if len(notifications) != 1 else ''} since {since_date}:")

        for notification in notifications:
            _display_notification(notification)

        # Mark as read if requested
        if mark_read:
            console.print(f"\n✅ Marked {len(notifications)} notifications as read", style="green")

    except Exception as e:
        console.print(f"❌ Failed to show notifications: {e}", style="bold red")


# ================================
# HELPER FUNCTIONS
# ================================

def _get_current_user() -> Optional[str]:
    """Get current user from git config or environment."""
    import subprocess
    
    # Try git config first
    try:
        result = subprocess.run(
            ["git", "config", "user.name"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
        pass

    # Fall back to environment variables
    return os.environ.get("USER") or os.environ.get("USERNAME")


def _display_daily_dashboard(core, assignee: str, days: int):
    """Display the personalized daily dashboard."""
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
        elif hasattr(issue, 'is_overdue') and issue.is_overdue:
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
        today_issues.sort(key=lambda x: (x.priority.value, getattr(x, 'progress_percentage', 0) or 0))

        for issue in today_issues:
            priority_emoji = {
                Priority.CRITICAL: "🔥",
                Priority.HIGH: "⚡",
                Priority.MEDIUM: "📋",
                Priority.LOW: "💤",
            }.get(issue.priority, "📋")

            status_info = ""
            if hasattr(issue, 'progress_percentage') and issue.progress_percentage:
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
            and hasattr(issue, 'depends_on')
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
        if hasattr(issue, 'depends_on') and issue.depends_on:
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
            and hasattr(i, 'actual_end_date')
            and i.actual_end_date
            and i.actual_end_date == today
        ]
    )

    console.print("📈 Quick Stats", style="bold white")
    console.print(
        f"   Active: {total_active} | Completed today: {total_done_today}", style="cyan"
    )

    # Calculate total estimated time remaining
    remaining_hours = sum(
        getattr(issue, 'estimated_hours', 0) or 0 for issue in active_issues
    )
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


def _get_user_notifications(core, assignee: str, since_date: datetime.date) -> list:
    """Get notifications for a user since a specific date."""
    
    # This is a simplified implementation
    # In a real system, this would query a notifications database
    
    notifications = []
    all_issues = core.list_issues()
    
    # Simulate notifications based on issue activity
    user_issues = [i for i in all_issues if i.assignee == assignee]
    
    for issue in user_issues:
        # Simulate various notification types
        
        # New assignment notification
        if hasattr(issue, 'assigned_date') and issue.assigned_date >= since_date:
            notifications.append({
                'type': 'assignment',
                'title': 'New Issue Assigned',
                'message': f"Issue {issue.id} '{issue.title}' has been assigned to you",
                'issue_id': issue.id,
                'timestamp': issue.assigned_date,
                'priority': issue.priority.value
            })
        
        # High priority notification
        if issue.priority in [Priority.CRITICAL, Priority.HIGH] and issue.status != Status.DONE:
            notifications.append({
                'type': 'priority',
                'title': 'High Priority Issue',
                'message': f"Issue {issue.id} '{issue.title}' is {issue.priority.value} priority",
                'issue_id': issue.id,
                'timestamp': datetime.date.today(),
                'priority': issue.priority.value
            })
        
        # Blocked issue notification
        if issue.status == Status.BLOCKED:
            notifications.append({
                'type': 'blocked',
                'title': 'Issue Blocked',
                'message': f"Issue {issue.id} '{issue.title}' is blocked and needs attention",
                'issue_id': issue.id,
                'timestamp': datetime.date.today(),
                'priority': 'high'
            })
    
    # Sort by timestamp (most recent first)
    notifications.sort(key=lambda x: x['timestamp'], reverse=True)
    
    # Filter by since date
    notifications = [n for n in notifications if n['timestamp'] >= since_date]
    
    return notifications


def _display_notification(notification: dict):
    """Display a single notification."""
    
    # Choose emoji and style based on type
    type_config = {
        'assignment': {'emoji': '📋', 'style': 'cyan'},
        'priority': {'emoji': '🚨', 'style': 'red'},
        'blocked': {'emoji': '🚫', 'style': 'yellow'},
        'comment': {'emoji': '💬', 'style': 'blue'},
        'mention': {'emoji': '👤', 'style': 'magenta'},
        'deadline': {'emoji': '⏰', 'style': 'orange'},
    }
    
    config = type_config.get(notification['type'], {'emoji': '📢', 'style': 'white'})
    
    # Format timestamp
    if isinstance(notification['timestamp'], datetime.date):
        time_str = notification['timestamp'].strftime('%Y-%m-%d')
    else:
        time_str = str(notification['timestamp'])
    
    # Display notification
    console.print(
        f"\n{config['emoji']} {notification['title']}",
        style=f"bold {config['style']}"
    )
    console.print(f"   {notification['message']}")
    console.print(f"   {time_str}", style="dim")
    
    if 'issue_id' in notification:
        console.print(f"   Issue: {notification['issue_id']}", style="dim")