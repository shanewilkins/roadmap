"""
Modular CLI architecture for the Roadmap tool.

This module provides the main CLI entry point and lazy-loads command groups
to improve performance and maintainability.
"""

import click
from typing import Optional
import os

# Initialize console for rich output
from roadmap.cli.utils import get_console
console = get_console()

# Import core classes for backward compatibility with tests
from roadmap.core import RoadmapCore
from roadmap.sync import SyncManager

# Import functions that tests expect to be available
# These are imported for backward compatibility and should be considered deprecated
@click.command()
@click.option("--include-backlog", is_flag=True, help="Include backlog items as orphaned")
@click.option("--min-age", default=0, help="Minimum age in days for items to be considered")
@click.option("--max-age", default=None, help="Maximum age in days for items to be considered")
@click.option("--export", help="Export report to file (JSON, CSV, or Markdown)")
@click.option("--format", default="json", help="Export format (json, csv, markdown)")
@click.option("--interactive", is_flag=True, help="Interactive mode for guided curation")
def curate_orphaned(include_backlog: bool, min_age: int, max_age, export, format: str, interactive: bool):
    """Scan for and display orphaned items (issues and milestones)."""
    try:
        # Use module-level RoadmapCore so tests that patch roadmap.cli.RoadmapCore
        # are effective. Import the curator from the curation module at runtime
        # so tests patching roadmap.curation.RoadmapCurator still work.
        from roadmap.curation import RoadmapCurator
        from rich.console import Console

        console = Console()
        core = RoadmapCore()

        if not core.is_initialized():
            console.print("❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red")
            return

        curator = RoadmapCurator(core)

        with console.status("[bold green]Analyzing orphaned items..."):
            report = curator.analyze_orphaned_items(
                include_backlog=include_backlog,
                min_age_days=min_age,
                max_age_days=max_age,
            )

        # Display summary. Support both object attributes and dict-style reports
        # (tests may provide MagicMock instances or simple dicts).
        try:
            orphaned_issues = getattr(report, "orphaned_issues", None)
            if orphaned_issues is None:
                orphaned_issues = report.get("orphaned_issues", [])
        except Exception:
            orphaned_issues = []

        try:
            orphaned_milestones = getattr(report, "orphaned_milestones", None)
            if orphaned_milestones is None:
                orphaned_milestones = report.get("orphaned_milestones", [])
        except Exception:
            orphaned_milestones = []

        console.print(f"📊 Found {len(orphaned_issues)} orphaned issues")
        console.print(f"📊 Found {len(orphaned_milestones)} orphaned milestones")
        
        # Export if requested
        if export:
            from pathlib import Path
            output_path = Path(export)
            curator.export_curation_report(report, output_path, format)
            console.print(f"✅ Report exported to {output_path}", style="bold green")
        
        # Interactive mode
        if interactive:
            console.print("🔧 Interactive curation mode not yet implemented", style="yellow")
            
    except Exception as e:
        from rich.console import Console
        console = Console()
        console.print(f"❌ Failed to analyze orphaned items: {e}", style="bold red")


def register_git_commands():
    """Register git commands for backward compatibility."""
    
    @main.command("git-status")
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

    @main.command("git-branch")
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

            # Create the branch using a compatibility wrapper
            def _safe_create_branch(git, issue, checkout=True):
                try:
                    return git.create_branch_for_issue(issue, checkout=checkout)
                except TypeError:
                    try:
                        return git.create_branch_for_issue(issue)
                    except Exception:
                        return False

            success = _safe_create_branch(core.git, issue, checkout=checkout)

            if success:
                console.print(f"🌿 Created branch: {branch_name}", style="bold green")
                if checkout:
                    console.print(f"✅ Checked out branch: {branch_name}", style="green")
                console.print(f"🔗 Linked to issue: {issue.title}", style="cyan")

                # Update issue status to in-progress if it's todo
                if issue.status == "todo":
                    core.update_issue(issue_id, status="in-progress")
                    console.print("📊 Updated issue status to: in-progress", style="yellow")
            else:
                # Fallback: try direct git checkout -b
                fallback = core.git._run_git_command(["checkout", "-b", branch_name])
                if fallback is not None:
                    console.print(f"🌿 Created branch: {branch_name}", style="bold green")
                    if checkout:
                        console.print(f"✅ Checked out branch: {branch_name}", style="green")
                    console.print(f"🔗 Linked to issue: {issue.title}", style="cyan")
                    if issue.status == "todo":
                        core.update_issue(issue_id, status="in-progress")
                        console.print("📊 Updated issue status to: in-progress", style="yellow")
                else:
                    console.print(f"❌ Failed to create branch", style="bold red")

        except Exception as e:
            console.print(f"❌ Failed to create Git branch: {e}", style="bold red")

    @main.command("git-link")
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
            issue = core.get_issue(issue_id)
            if not issue:
                console.print(f"❌ Issue not found: {issue_id}", style="bold red")
                return

            current_branch = core.git.get_current_branch()
            if not current_branch:
                console.print("❌ Could not determine current branch", style="bold red")
                return

            # Link the issue to the current branch
            success = core.link_issue_to_current_branch(issue_id)

            if success:
                console.print(f"🔗 Linked issue to branch: {current_branch.name}", style="bold green")
                console.print(f"📋 Issue: {issue.title}", style="cyan")
                console.print(f"🆔 ID: {issue_id}", style="dim")
            else:
                console.print(f"❌ Failed to link issue to branch", style="bold red")

        except Exception as e:
            console.print(f"❌ Failed to link issue to Git branch: {e}", style="bold red")


# Import utility functions that tests need
import os
try:
    import git
except ImportError:
    git = None

def _get_current_user():
    """Get current user from git config."""
    if git is None:
        return os.environ.get('USER') or os.environ.get('USERNAME')
        
    try:
        repo = git.Repo(search_parent_directories=True)
        try:
            name = repo.config_reader().get_value("user", "name")
            return name
        except Exception:
            pass
    except Exception:
        pass
    
    # Fallback to environment variables
    return os.environ.get('USER') or os.environ.get('USERNAME')


def _detect_project_context():
    """Detect project context from current directory."""
    import pathlib
    
    current_dir = pathlib.Path.cwd()
    
    # Look for common project indicators
    indicators = [
        '.git',
        'package.json',
        'pyproject.toml',
        'Cargo.toml',
        'pom.xml',
        'build.gradle',
        'composer.json'
    ]
    
    for indicator in indicators:
        if (current_dir / indicator).exists():
            return {
                'project_name': current_dir.name,
                'has_git': (current_dir / '.git').exists(),
                'type': indicator,
                'path': str(current_dir),
                'name': current_dir.name
            }
    
    # Return default context if no project indicators found
    return {
        'project_name': current_dir.name,
        'has_git': (current_dir / '.git').exists(),
        'type': 'unknown',
        'path': str(current_dir),
        'name': current_dir.name
    }

@click.group(invoke_without_command=True)
@click.version_option()
@click.pass_context
def main(ctx: click.Context):
    """Roadmap CLI - A command line tool for creating and managing roadmaps."""
    # Ensure that ctx.obj exists and is a dict (in case `cli()` is called
    # by means other than the `if` block below)
    ctx.ensure_object(dict)
    
    # Initialize core with default roadmap directory
    ctx.obj["core"] = RoadmapCore()
    
    # If no subcommand was provided, show help
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


def register_commands():
    """
    Lazy load and register all command groups.
    This improves startup performance by only importing modules when needed.
    """
    # Register standalone commands
    from .core import init, status
    main.add_command(init)
    main.add_command(status)
    
    # Register command groups with lazy loading
    from .team import team
    from .user import user
    from .data import data
    from .project import project
    from .issue import issue
    from .milestone import milestone
    from .sync import sync
    from .git_integration import git
    from .analytics import analytics
    from .comment import comment
    from .release import release_group
    from .deprecated import register_deprecated_commands
    
    # Register activity and utility commands
    from .activity import (
        activity, broadcast, handoff, dashboard, notifications, export_data,
        handoff_context, handoff_list, workload_analysis, smart_assign, capacity_forecast
    )
    main.add_command(activity)
    main.add_command(broadcast) 
    main.add_command(handoff)
    main.add_command(dashboard)
    main.add_command(notifications)
    main.add_command(export_data)
    main.add_command(handoff_context)
    main.add_command(handoff_list)
    main.add_command(workload_analysis)
    main.add_command(smart_assign)
    main.add_command(capacity_forecast)
    
    main.add_command(team)
    main.add_command(user)
    main.add_command(data)
    main.add_command(project)
    main.add_command(issue)
    main.add_command(milestone)
    main.add_command(sync)
    main.add_command(git)
    main.add_command(analytics)
    main.add_command(comment)
    main.add_command(release_group)
    
    # Register progress and CI commands
    from .progress import recalculate_progress, progress_reports
    from .ci import ci
    main.add_command(recalculate_progress)
    main.add_command(progress_reports)
    main.add_command(ci)
    
    # Register git commands for backward compatibility
    register_git_commands()
    
    # Register deprecated commands for backward compatibility
    register_deprecated_commands(main)


# Register all commands when module is imported
register_commands()


if __name__ == "__main__":
    main()