"""
Issue management CLI commands.
"""

import click
import os
from roadmap.core import RoadmapCore
from roadmap.models import Priority, IssueType, Status
from roadmap.cli.utils import get_console

console = get_console()

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
        # Handle special assignee filters first
        if my_issues:
            issues = core.get_my_issues()
            filter_description = "my"
        elif assignee:
            issues = core.get_assigned_issues(assignee)
            filter_description = f"assigned to {assignee}"
        else:
            # Show all issues for now (can add more filters later)
            issues = core.list_issues()
            filter_description = "all"

        # Show results
        if not issues:
            console.print(f"📋 No {filter_description} issues found.", style="yellow")
            return

        # Display header with filter info
        header_text = f"📋 {len(issues)} {filter_description} issue{'s' if len(issues) != 1 else ''}"
        console.print(header_text, style="bold cyan")

        # Simple list for now
        for issue in issues:
            console.print(f"  {issue.id}: {issue.title}")

    except Exception as e:
        console.print(f"❌ Failed to list issues: {e}", style="bold red")

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
                    console.print(f"🔄 Resolved '{assignee}' to '{canonical_assignee}'", style="dim")

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
    except click.Abort:
        # Re-raise click.Abort to maintain proper exit code
        raise
    except Exception as e:
        console.print(f"❌ Failed to create issue: {e}", style="bold red")
        raise click.Abort()

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
    reason: str,
):
    """Update an existing issue."""
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        raise click.Abort()

    try:
        # Check if issue exists
        issue = core.get_issue(issue_id)
        if not issue:
            console.print(f"❌ Issue not found: {issue_id}", style="bold red")
            raise click.Abort()

        # Build update dict
        updates = {}
        if title:
            updates["title"] = title
        if priority:
            updates["priority"] = Priority(priority)
        if status:
            updates["status"] = status
        if assignee:
            updates["assignee"] = assignee
        if milestone:
            updates["milestone"] = milestone
        if description:
            updates["description"] = description

        if not updates:
            console.print("❌ No updates specified", style="bold red")
            raise click.Abort()

        # Update the issue
        updated_issue = core.update_issue(issue_id, **updates)
        
        console.print(f"✅ Updated issue: {updated_issue.title}", style="bold green")
        console.print(f"   ID: {updated_issue.id}", style="cyan")
        
        if reason:
            console.print(f"   Reason: {reason}", style="dim")
            
    except click.Abort:
        raise
    except Exception as e:
        console.print(f"❌ Failed to update issue: {e}", style="bold red")
        raise click.Abort()

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
        raise click.Abort()

    try:
        # Check if issue exists
        issue = core.get_issue(issue_id)
        if not issue:
            console.print(f"❌ Issue not found: {issue_id}", style="bold red")
            raise click.Abort()

        # Update status to done
        updated_issue = core.update_issue(issue_id, status="done")
        
        console.print(f"✅ Marked issue as done: {updated_issue.title}", style="bold green")
        console.print(f"   ID: {updated_issue.id}", style="cyan")
        
        if reason:
            console.print(f"   Reason: {reason}", style="dim")
            
    except click.Abort:
        raise
    except Exception as e:
        console.print(f"❌ Failed to mark issue as done: {e}", style="bold red")
        raise click.Abort()

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
        raise click.Abort()

    try:
        # Check if issue exists
        issue = core.get_issue(issue_id)
        if not issue:
            console.print(f"❌ Issue not found: {issue_id}", style="bold red")
            raise click.Abort()

        # Update status to blocked
        updated_issue = core.update_issue(issue_id, status="blocked")
        
        console.print(f"🚫 Marked issue as blocked: {updated_issue.title}", style="bold red")
        console.print(f"   ID: {updated_issue.id}", style="cyan")
        
        if reason:
            console.print(f"   Reason: {reason}", style="dim")
            
    except click.Abort:
        raise
    except Exception as e:
        console.print(f"❌ Failed to block issue: {e}", style="bold red")
        raise click.Abort()

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
        raise click.Abort()

    try:
        # Check if issue exists
        issue = core.get_issue(issue_id)
        if not issue:
            console.print(f"❌ Issue not found: {issue_id}", style="bold red")
            raise click.Abort()

        # Confirm deletion if not using --yes flag
        if not yes:
            if not click.confirm(f"Are you sure you want to delete issue '{issue.title}'?"):
                console.print("❌ Issue deletion cancelled.", style="yellow")
                return

        # Delete the issue
        core.delete_issue(issue_id)
        
        console.print(f"✅ Deleted issue: {issue.title}", style="bold green")
        console.print(f"   ID: {issue_id}", style="cyan")
            
    except click.Abort:
        raise
    except Exception as e:
        console.print(f"❌ Failed to delete issue: {e}", style="bold red")
        raise click.Abort()