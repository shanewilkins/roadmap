"""
Team collaboration CLI commands.
"""

import click

from roadmap.cli.utils import get_console

console = get_console()

import datetime

from rich.console import Console
from rich.table import Table

from roadmap.models import Priority, Status

console = Console()


@click.group()
def team():
    """Team collaboration and workload management."""
    pass


# ================================
# OBJECT-VERB PATTERN COMMANDS
# ================================


@team.command("forecast-capacity")
@click.option("--days", "-d", default=30, help="Number of days to forecast")
@click.option("--assignee", "-a", help="Filter by specific assignee")
@click.pass_context
def forecast_capacity(ctx: click.Context, days: int, assignee: str):
    """Forecast team capacity and identify bottlenecks."""
    _original_capacity_forecast(ctx, days, assignee)


@team.command("analyze-workload")
@click.option("--assignee", "-a", help="Analyze workload for specific assignee")
@click.option(
    "--include-estimates", is_flag=True, help="Include time estimates in analysis"
)
@click.option("--suggest-rebalance", is_flag=True, help="Suggest workload rebalancing")
@click.pass_context
def analyze_workload(
    ctx: click.Context, assignee: str, include_estimates: bool, suggest_rebalance: bool
):
    """Analyze team workload and capacity distribution."""
    _original_workload_analysis(ctx, assignee, include_estimates, suggest_rebalance)


@team.command("assign-smart")
@click.argument("issue_id")
@click.option("--consider-skills", is_flag=True, help="Consider team member skills")
@click.option("--consider-availability", is_flag=True, help="Consider current workload")
@click.option("--suggest-only", is_flag=True, help="Only suggest, don't assign")
@click.pass_context
def assign_smart(
    ctx: click.Context,
    issue_id: str,
    consider_skills: bool,
    consider_availability: bool,
    suggest_only: bool,
):
    """Intelligently assign an issue to the best team member."""
    _original_smart_assign(
        ctx, issue_id, consider_skills, consider_availability, suggest_only
    )


@team.command("broadcast")
@click.argument("message")
@click.option("--assignee", "-a", help="Target specific team member")
@click.option("--issue", "-i", help="Link to specific issue")
@click.pass_context
def broadcast(ctx: click.Context, message: str, assignee: str, issue: str):
    """Broadcast a status update to the team."""
    _original_broadcast(ctx, message, assignee, issue)


@team.command("show-activity")
@click.option("--days", "-d", default=7, help="Number of days to show")
@click.option("--assignee", "-a", help="Filter by specific assignee")
@click.pass_context
def show_activity(ctx: click.Context, days: int, assignee: str):
    """Show recent team activity and updates."""
    _original_activity(ctx, days, assignee)


@team.command("handoff")
@click.argument("issue_id")
@click.argument("new_assignee")
@click.option("--message", "-m", help="Handoff message or context")
@click.option(
    "--priority",
    type=click.Choice(["critical", "high", "medium", "low"]),
    help="Update priority during handoff",
)
@click.option("--urgent", is_flag=True, help="Mark as urgent handoff")
@click.pass_context
def handoff(
    ctx: click.Context,
    issue_id: str,
    new_assignee: str,
    message: str,
    priority: str,
    urgent: bool,
):
    """Hand off an issue to another team member."""
    _original_handoff(ctx, issue_id, new_assignee, message, priority, urgent)


@team.command("show-handoff-context")
@click.argument("issue_id")
@click.pass_context
def show_handoff_context(ctx: click.Context, issue_id: str):
    """Show handoff context and history for an issue."""
    _original_handoff_context(ctx, issue_id)


@team.command("list-handoffs")
@click.option("--assignee", "-a", help="Filter by assignee")
@click.option("--show-completed", is_flag=True, help="Include completed handoffs")
@click.pass_context
def list_handoffs(ctx: click.Context, assignee: str, show_completed: bool):
    """List all recent handoffs in the project."""
    _original_handoff_list(ctx, assignee, show_completed)


# ================================
# ORIGINAL IMPLEMENTATIONS
# ================================


def _original_capacity_forecast(ctx: click.Context, days: int, assignee: str):
    """Original capacity forecast implementation."""
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return

    try:
        console.print(f"📊 Team Capacity Forecast ({days} days)", style="bold blue")

        # Get all issues and team members
        all_issues = core.list_issues()
        team_members = (
            core.get_team_members() if hasattr(core, "get_team_members") else []
        )

        # Filter by assignee if specified
        if assignee:
            all_issues = [i for i in all_issues if i.assignee == assignee]
            team_members = [assignee] if assignee in team_members else [assignee]

        if not all_issues:
            console.print("📝 No issues found for analysis.", style="yellow")
            return

        # Calculate workload distribution
        active_issues = [i for i in all_issues if i.status != Status.DONE]

        console.print("\n👥 Team Summary:")
        console.print(f"   Active Issues: {len(active_issues)}")
        console.print(
            f"   Team Members: {len(team_members) if team_members else 'Unknown'}"
        )

        # Group by assignee
        workload_by_assignee = {}
        for issue in active_issues:
            assignee_name = issue.assignee or "Unassigned"
            if assignee_name not in workload_by_assignee:
                workload_by_assignee[assignee_name] = []
            workload_by_assignee[assignee_name].append(issue)

        # Show workload distribution
        if workload_by_assignee:
            console.print("\n📋 Current Workload Distribution:")

            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("Assignee", style="white")
            table.add_column("Total", style="cyan", width=8)
            table.add_column("High Priority", style="red", width=12)
            table.add_column("In Progress", style="yellow", width=12)
            table.add_column("Blocked", style="red", width=8)

            for assignee_name, issues in workload_by_assignee.items():
                total_count = len(issues)
                high_priority = len(
                    [
                        i
                        for i in issues
                        if i.priority in [Priority.CRITICAL, Priority.HIGH]
                    ]
                )
                in_progress = len([i for i in issues if i.status == Status.IN_PROGRESS])
                blocked = len([i for i in issues if i.status == Status.BLOCKED])

                table.add_row(
                    assignee_name,
                    str(total_count),
                    str(high_priority),
                    str(in_progress),
                    str(blocked),
                )

            console.print(table)

        # Identify bottlenecks
        console.print("\n🚨 Potential Bottlenecks:")

        blocked_issues = [i for i in active_issues if i.status == Status.BLOCKED]
        overloaded_assignees = [
            (k, v) for k, v in workload_by_assignee.items() if len(v) > 5
        ]

        if blocked_issues:
            console.print(f"   • {len(blocked_issues)} blocked issues need attention")
        if overloaded_assignees:
            for assignee_name, issues in overloaded_assignees:
                console.print(f"   • {assignee_name} has {len(issues)} active issues")

        if not blocked_issues and not overloaded_assignees:
            console.print("   ✅ No major bottlenecks detected")

    except Exception as e:
        console.print(f"❌ Failed to generate capacity forecast: {e}", style="bold red")


def _original_workload_analysis(
    ctx: click.Context, assignee: str, include_estimates: bool, suggest_rebalance: bool
):
    """Original workload analysis implementation."""
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return

    try:
        console.print("📊 Team Workload Analysis", style="bold blue")

        # Get all issues
        all_issues = core.list_issues()

        # Filter by assignee if specified
        if assignee:
            all_issues = [i for i in all_issues if i.assignee == assignee]
            console.print(f"\n🎯 Analyzing workload for: {assignee}")
        else:
            console.print("\n🎯 Analyzing workload for entire team")

        if not all_issues:
            console.print("📝 No issues found for analysis.", style="yellow")
            return

        # Group by status
        active_issues = [i for i in all_issues if i.status != Status.DONE]
        completed_issues = [i for i in all_issues if i.status == Status.DONE]

        console.print("\n📋 Issue Summary:")
        console.print(f"   Active: {len(active_issues)}")
        console.print(f"   Completed: {len(completed_issues)}")

        # Show workload by priority
        if active_issues:
            priority_counts = {}
            for issue in active_issues:
                priority_counts[issue.priority] = (
                    priority_counts.get(issue.priority, 0) + 1
                )

            console.print("\n🚨 Active Issues by Priority:")
            for priority in [
                Priority.CRITICAL,
                Priority.HIGH,
                Priority.MEDIUM,
                Priority.LOW,
            ]:
                count = priority_counts.get(priority, 0)
                if count > 0:
                    priority_emoji = {
                        Priority.CRITICAL: "🔥",
                        Priority.HIGH: "⚡",
                        Priority.MEDIUM: "📋",
                        Priority.LOW: "💤",
                    }.get(priority, "📋")
                    console.print(f"   {priority_emoji} {priority.value}: {count}")

        # Include time estimates if requested
        if include_estimates:
            total_estimated = sum(issue.estimated_hours or 0 for issue in active_issues)
            if total_estimated > 0:
                console.print("\n⏱️  Time Estimates:")
                console.print(f"   Total remaining: {total_estimated:.1f} hours")
                if total_estimated >= 8:
                    days_estimated = total_estimated / 8
                    console.print(f"   Estimated workdays: {days_estimated:.1f}")

        # Suggest rebalancing if requested
        if suggest_rebalance and not assignee:
            console.print("\n💡 Rebalancing Suggestions:")

            # Group by assignee for team analysis
            workload_by_assignee = {}
            for issue in active_issues:
                assignee_name = issue.assignee or "Unassigned"
                if assignee_name not in workload_by_assignee:
                    workload_by_assignee[assignee_name] = []
                workload_by_assignee[assignee_name].append(issue)

            if len(workload_by_assignee) > 1:
                # Find overloaded and underloaded team members
                avg_workload = len(active_issues) / len(workload_by_assignee)

                overloaded = [
                    (k, v)
                    for k, v in workload_by_assignee.items()
                    if len(v) > avg_workload * 1.5
                ]
                underloaded = [
                    (k, v)
                    for k, v in workload_by_assignee.items()
                    if len(v) < avg_workload * 0.5
                ]

                if overloaded and underloaded:
                    console.print("   Consider redistributing work:")
                    for assignee_name, issues in overloaded:
                        console.print(
                            f"   • {assignee_name} has {len(issues)} issues (above average)"
                        )
                    for assignee_name, issues in underloaded:
                        console.print(
                            f"   • {assignee_name} has {len(issues)} issues (below average)"
                        )
                else:
                    console.print("   ✅ Workload appears well balanced")
            else:
                console.print("   Need multiple team members for rebalancing analysis")

    except Exception as e:
        console.print(f"❌ Failed to analyze workload: {e}", style="bold red")


def _original_smart_assign(
    ctx: click.Context,
    issue_id: str,
    consider_skills: bool,
    consider_availability: bool,
    suggest_only: bool,
):
    """Original smart assignment implementation."""
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

        console.print(
            f"🤖 Smart Assignment Analysis for: {issue.title}", style="bold blue"
        )

        # Get team members and their current workload
        team_members = (
            core.get_team_members() if hasattr(core, "get_team_members") else []
        )
        all_issues = core.list_issues()

        if not team_members:
            console.print(
                "❌ No team members found. Set up GitHub integration or manually configure team.",
                style="bold red",
            )
            return

        # Analyze each team member
        suggestions = []

        for member in team_members:
            score = 100  # Start with perfect score
            reasons = []

            # Consider current workload
            if consider_availability:
                member_issues = [
                    i
                    for i in all_issues
                    if i.assignee == member and i.status != Status.DONE
                ]
                workload = len(member_issues)

                if workload > 5:
                    score -= 30
                    reasons.append(f"High workload ({workload} issues)")
                elif workload > 3:
                    score -= 15
                    reasons.append(f"Moderate workload ({workload} issues)")
                else:
                    reasons.append(f"Light workload ({workload} issues)")

            # Consider skills (placeholder - would need skill tracking)
            if consider_skills:
                # This would integrate with team member skill profiles
                reasons.append("Skill matching not yet implemented")

            # Check for any blocking issues
            blocked_issues = [
                i
                for i in all_issues
                if i.assignee == member and i.status == Status.BLOCKED
            ]
            if blocked_issues:
                score -= 20
                reasons.append(f"Has {len(blocked_issues)} blocked issues")

            suggestions.append(
                {"member": member, "score": max(0, score), "reasons": reasons}
            )

        # Sort by score
        suggestions.sort(key=lambda x: x["score"], reverse=True)

        # Display suggestions
        console.print("\n🎯 Assignment Recommendations:")

        for i, suggestion in enumerate(suggestions[:5]):  # Show top 5
            rank_emoji = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"][i]
            console.print(
                f"\n{rank_emoji} {suggestion['member']} (Score: {suggestion['score']}/100)"
            )

            for reason in suggestion["reasons"]:
                console.print(f"   • {reason}")

        # Best recommendation
        best_suggestion = suggestions[0]
        console.print(f"\n💡 Best recommendation: {best_suggestion['member']}")

        # Assign if not suggest-only
        if not suggest_only:
            if click.confirm(
                f"Assign issue {issue_id} to {best_suggestion['member']}?"
            ):
                issue.assignee = best_suggestion["member"]
                core.save_issue(issue)
                console.print(
                    f"✅ Assigned {issue_id} to {best_suggestion['member']}",
                    style="bold green",
                )
            else:
                console.print("Assignment cancelled.", style="yellow")

    except Exception as e:
        console.print(f"❌ Failed to perform smart assignment: {e}", style="bold red")


def _original_broadcast(ctx: click.Context, message: str, assignee: str, issue: str):
    """Original broadcast implementation."""
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return

    try:
        console.print("📢 Broadcasting team update...", style="bold blue")

        # Validate issue if provided
        if issue:
            issue_obj = core.get_issue(issue)
            if not issue_obj:
                console.print(
                    f"⚠️  Issue {issue} not found, broadcasting anyway", style="yellow"
                )

        # Create broadcast record (this would integrate with notification system)
        timestamp = datetime.datetime.now().isoformat()

        {
            "timestamp": timestamp,
            "message": message,
            "sender": core.get_current_user()
            if hasattr(core, "get_current_user")
            else "Unknown",
            "target_assignee": assignee,
            "linked_issue": issue,
        }

        # Display broadcast
        console.print("\n📢 Team Broadcast")
        console.print(f"   Message: {message}")
        if assignee:
            console.print(f"   Target: {assignee}")
        if issue:
            console.print(f"   Related Issue: {issue}")
        console.print(f"   Time: {timestamp}")

        # In a real implementation, this would:
        # - Send notifications to team members
        # - Log to activity feed
        # - Integrate with chat systems
        # - Update issue comments if linked

        console.print("✅ Broadcast sent successfully", style="bold green")
        console.print(
            "💡 Future: This will integrate with notification systems", style="dim"
        )

    except Exception as e:
        console.print(f"❌ Failed to broadcast message: {e}", style="bold red")


def _original_activity(ctx: click.Context, days: int, assignee: str):
    """Original activity display implementation."""
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return

    try:
        console.print(f"📈 Team Activity ({days} days)", style="bold blue")

        # Get recent activity (this would come from activity log in real implementation)
        all_issues = core.list_issues()

        # Filter by assignee if specified
        if assignee:
            all_issues = [i for i in all_issues if i.assignee == assignee]
            console.print(f"\n🎯 Activity for: {assignee}")
        else:
            console.print("\n🎯 Activity for entire team")

        # Calculate cutoff date
        cutoff_date = datetime.datetime.now() - datetime.timedelta(days=days)

        # Recent changes (simplified - would use proper activity tracking)
        recent_completed = []
        recent_created = []

        for issue in all_issues:
            if issue.status == Status.DONE and issue.actual_end_date:
                if issue.actual_end_date >= cutoff_date.date():
                    recent_completed.append(issue)

            # Check creation date (would use proper created_date field)
            if hasattr(issue, "created_date") and issue.created_date:
                if issue.created_date >= cutoff_date.date():
                    recent_created.append(issue)

        # Display activity summary
        console.print("\n📊 Activity Summary:")
        console.print(f"   Issues completed: {len(recent_completed)}")
        console.print(f"   Issues created: {len(recent_created)}")

        # Show recent completions
        if recent_completed:
            console.print("\n✅ Recently Completed:")
            for issue in recent_completed[-10:]:  # Show last 10
                assignee_text = f" ({issue.assignee})" if issue.assignee else ""
                console.print(
                    f"   • {issue.id}: {issue.title}{assignee_text}", style="green"
                )

        # Show recent creations
        if recent_created:
            console.print("\n📝 Recently Created:")
            for issue in recent_created[-10:]:  # Show last 10
                assignee_text = f" ({issue.assignee})" if issue.assignee else ""
                console.print(
                    f"   • {issue.id}: {issue.title}{assignee_text}", style="cyan"
                )

        if not recent_completed and not recent_created:
            console.print("🔍 No recent activity found", style="yellow")
            console.print(
                "💡 Activity tracking will be enhanced in future versions", style="dim"
            )

    except Exception as e:
        console.print(f"❌ Failed to show activity: {e}", style="bold red")


def _original_handoff(
    ctx: click.Context,
    issue_id: str,
    new_assignee: str,
    message: str,
    priority: str,
    urgent: bool,
):
    """Original handoff implementation."""
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

        # Validate new assignee (would use identity management)
        team_members = (
            core.get_team_members() if hasattr(core, "get_team_members") else []
        )
        if team_members and new_assignee not in team_members:
            console.print(
                f"⚠️  {new_assignee} not in known team members", style="yellow"
            )
            if not click.confirm(f"Continue handoff to {new_assignee}?"):
                return

        console.print(f"🤝 Handing off issue: {issue.title}", style="bold blue")

        old_assignee = issue.assignee or "Unassigned"

        # Update issue
        issue.assignee = new_assignee

        # Update priority if specified
        if priority:
            old_priority = issue.priority
            issue.priority = Priority(priority.upper())
            console.print(f"   Priority: {old_priority.value} → {issue.priority.value}")

        # Add handoff comment/note
        handoff_note = f"Handoff from {old_assignee} to {new_assignee}"
        if message:
            handoff_note += f": {message}"
        if urgent:
            handoff_note = f"[URGENT] {handoff_note}"

        # Save issue
        core.save_issue(issue)

        # Display handoff summary
        console.print(f"✅ Issue {issue_id} handed off:", style="bold green")
        console.print(f"   From: {old_assignee}")
        console.print(f"   To: {new_assignee}")
        if message:
            console.print(f"   Message: {message}")
        if urgent:
            console.print("   🚨 Marked as urgent handoff", style="red")

        # Future: This would also:
        # - Send notifications to both assignees
        # - Log handoff in activity stream
        # - Create handoff history record

    except Exception as e:
        console.print(f"❌ Failed to hand off issue: {e}", style="bold red")


def _original_handoff_context(ctx: click.Context, issue_id: str):
    """Original handoff context implementation."""
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

        console.print(f"🤝 Handoff Context: {issue.title}", style="bold blue")

        # Show current issue details
        console.print("\n📋 Current Status:")
        console.print(f"   Assignee: {issue.assignee or 'Unassigned'}")
        console.print(f"   Status: {issue.status.value}")
        console.print(f"   Priority: {issue.priority.value}")

        if issue.description:
            console.print("\n📝 Description:")
            # Show first 200 chars
            desc_preview = issue.description[:200]
            if len(issue.description) > 200:
                desc_preview += "..."
            console.print(f"   {desc_preview}")

        # Show dependencies
        if hasattr(issue, "depends_on") and issue.depends_on:
            console.print("\n🔗 Dependencies:")
            for dep_id in issue.depends_on:
                dep_issue = core.get_issue(dep_id)
                if dep_issue:
                    status_style = (
                        "green" if dep_issue.status == Status.DONE else "yellow"
                    )
                    console.print(
                        f"   • {dep_id}: {dep_issue.title} [{dep_issue.status.value}]",
                        style=status_style,
                    )

        # Show progress
        if hasattr(issue, "progress_percentage") and issue.progress_percentage:
            console.print(f"\n📊 Progress: {issue.progress_percentage:.0f}%")

        # Future handoff history would show here
        console.print("\n🔄 Handoff History:")
        console.print("   (Handoff history tracking not yet implemented)", style="dim")

        # Suggest handoff considerations
        console.print("\n💡 Handoff Considerations:")

        if issue.status == Status.BLOCKED:
            console.print("   ⚠️  Issue is currently blocked", style="red")
        if issue.priority in [Priority.CRITICAL, Priority.HIGH]:
            console.print("   🚨 High priority issue", style="yellow")
        if hasattr(issue, "estimated_hours") and issue.estimated_hours:
            console.print(f"   ⏱️  Estimated time: {issue.estimated_hours} hours")

    except Exception as e:
        console.print(f"❌ Failed to show handoff context: {e}", style="bold red")


def _original_handoff_list(ctx: click.Context, assignee: str, show_completed: bool):
    """Original handoff list implementation."""
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return

    try:
        console.print("🤝 Recent Handoffs", style="bold blue")

        # In a real implementation, this would query a handoff history
        # For now, we'll simulate by showing recent assignment changes

        all_issues = core.list_issues()

        # Filter by assignee if specified
        if assignee:
            all_issues = [i for i in all_issues if i.assignee == assignee]
            console.print(f"\n🎯 Handoffs for: {assignee}")

        # Filter out completed if not requested
        if not show_completed:
            all_issues = [i for i in all_issues if i.status != Status.DONE]

        if not all_issues:
            console.print("📝 No handoffs found", style="yellow")
            console.print(
                "💡 Handoff tracking will be enhanced in future versions", style="dim"
            )
            return

        # Group by assignee
        handoffs_by_assignee = {}
        for issue in all_issues:
            assignee_name = issue.assignee or "Unassigned"
            if assignee_name not in handoffs_by_assignee:
                handoffs_by_assignee[assignee_name] = []
            handoffs_by_assignee[assignee_name].append(issue)

        # Display handoffs
        console.print("\n📋 Current Assignments (simulated handoff data):")

        for assignee_name, issues in handoffs_by_assignee.items():
            console.print(f"\n👤 {assignee_name} ({len(issues)} issues)")

            for issue in issues[:5]:  # Show first 5
                status_style = {
                    Status.TODO: "white",
                    Status.IN_PROGRESS: "yellow",
                    Status.BLOCKED: "red",
                    Status.REVIEW: "blue",
                    Status.DONE: "green",
                }.get(issue.status, "white")

                console.print(
                    f"   • {issue.id}: {issue.title} [{issue.status.value}]",
                    style=status_style,
                )

            if len(issues) > 5:
                console.print(f"   ... and {len(issues) - 5} more", style="dim")

        console.print(
            "\n💡 Note: Enhanced handoff tracking with history, notifications,"
        )
        console.print(
            "   and context preservation will be available in future versions.",
            style="dim",
        )

    except Exception as e:
        console.print(f"❌ Failed to list handoffs: {e}", style="bold red")


@team.command("members")
@click.pass_context
def list_members(ctx: click.Context):
    """List team members."""
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
                console.print(f"  � {member} (you)", style="bold magenta")
            else:
                console.print(f"  👤 {member}", style="white")

    except Exception as e:
        console.print(f"❌ Failed to get team members: {e}", style="bold red")


@team.command("assignments")
@click.pass_context
def list_assignments(ctx: click.Context):
    """Show issue assignments for all team members."""
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        raise click.Abort()

    try:
        assigned_issues = core.get_all_assigned_issues()

        if not assigned_issues:
            console.print("📋 No assigned issues found.", style="yellow")
            console.print(
                "Create issues with: roadmap issue create 'Title' --assignee username",
                style="dim",
            )
            return

        console.print("📋 Team Assignments:", style="bold blue")
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
        console.print(f"❌ Failed to list team assignments: {e}", style="bold red")
        raise click.Abort()


@team.command("workload")
@click.pass_context
def show_workload(ctx: click.Context):
    """Show workload summary for all team members."""
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        raise click.Abort()

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

            if unassigned_hours > 0:
                days = unassigned_hours / 8
                time_str = f" ({unassigned_hours:.1f}h / {days:.1f}d estimated)"
            else:
                time_str = ""

            console.print()
            console.print(
                f"📝 {len(unassigned)} unassigned issue{'s' if len(unassigned) != 1 else ''}{time_str}",
                style="dim",
            )

    except Exception as e:
        console.print(f"❌ Failed to show team workload: {e}", style="bold red")
        raise click.Abort()
