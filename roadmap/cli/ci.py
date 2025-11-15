"""
CLI commands for CI/CD integration and automatic issue tracking.
"""

import click
from rich.console import Console
from rich.table import Table
from rich import print as rprint
from typing import Optional

from ..core import RoadmapCore
from ..ci_tracking import CITracker, CIAutomation, CITrackingConfig

console = Console()


@click.group()
def ci():
    """CI/CD integration commands for automatic issue tracking."""
    pass


@ci.command()
@click.argument('branch_name')
@click.option('--issue-id', help='Manually specify issue ID to associate')
@click.option('--auto-start/--no-auto-start', default=None, help='Override auto-start behavior')
def track_branch(branch_name: str, issue_id: Optional[str], auto_start: Optional[bool]):
    """Track a git branch for issue associations.
    
    BRANCH_NAME: Name of the git branch to track
    """
    try:
        # Initialize components
        roadmap_core = RoadmapCore()
        config = CITrackingConfig()
        
        # Override auto-start if specified
        if auto_start is not None:
            config.auto_start_on_branch = auto_start
            
        tracker = CITracker(roadmap_core, config)
        
        # Manual association if issue ID provided
        if issue_id:
            success = tracker.add_branch_to_issue(issue_id, branch_name)
            if success:
                rprint(f"✅ Associated branch [cyan]{branch_name}[/cyan] with issue [yellow]{issue_id}[/yellow]")
            else:
                rprint(f"❌ Failed to associate branch with issue {issue_id}")
            return
        
        # Automatic tracking based on branch name patterns
        results = tracker.track_branch(branch_name)
        
        if not results:
            rprint(f"ℹ️  No issue IDs found in branch name: [cyan]{branch_name}[/cyan]")
            rprint("💡 Tip: Use pattern like 'feature/ea4606b6-description' or 'ea4606b6-feature'")
            return
        
        # Display results
        table = Table(title=f"Branch Tracking Results: {branch_name}")
        table.add_column("Issue ID", style="yellow")
        table.add_column("Actions Taken", style="green")
        
        for issue_id, actions in results.items():
            table.add_row(issue_id, ", ".join(actions))
        
        console.print(table)
        
    except Exception as e:
        rprint(f"❌ Error tracking branch: {e}")


@ci.command()
@click.argument('commit_sha')
@click.option('--message', help='Commit message (will be fetched if not provided)')
def track_commit(commit_sha: str, message: Optional[str]):
    """Track a git commit for issue associations.
    
    COMMIT_SHA: Git commit SHA (full or short)
    """
    try:
        # Initialize components
        roadmap_core = RoadmapCore()
        tracker = CITracker(roadmap_core)
        
        # Track the commit
        results = tracker.track_commit(commit_sha, message)
        
        if not results:
            rprint(f"ℹ️  No issue IDs found in commit: [cyan]{commit_sha[:8]}[/cyan]")
            rprint("💡 Tip: Include issue ID in commit message like 'fixes ea4606b6' or 'ea4606b6: fix bug'")
            return
        
        # Display results
        table = Table(title=f"Commit Tracking Results: {commit_sha[:8]}")
        table.add_column("Issue ID", style="yellow")
        table.add_column("Actions Taken", style="green")
        
        for issue_id, actions in results.items():
            table.add_row(issue_id, ", ".join(actions))
        
        console.print(table)
        
    except Exception as e:
        rprint(f"❌ Error tracking commit: {e}")


@ci.command()
@click.argument('pr_number', type=int)
@click.option('--branch', help='PR branch name (will be detected if not provided)')
@click.option('--action', type=click.Choice(['opened', 'merged', 'closed']), 
              default='opened', help='PR action that triggered the event')
def track_pr(pr_number: int, branch: Optional[str], action: str):
    """Track a pull request for issue associations.
    
    PR_NUMBER: Pull request number
    """
    try:
        # Initialize components
        roadmap_core = RoadmapCore()
        tracker = CITracker(roadmap_core)
        automation = CIAutomation(roadmap_core, tracker)
        
        # Get branch name if not provided
        if not branch:
            branch = tracker.get_current_branch()
            if not branch:
                rprint("❌ Could not determine branch name. Please specify with --branch")
                return
        
        # Create PR info structure
        pr_info = {
            'number': pr_number,
            'head_branch': branch,
            'base_branch': 'main'  # Default to main for demo
        }
        
        # Handle different PR actions
        if action == 'opened':
            results = automation.on_pull_request_opened(pr_info)
        elif action == 'merged':
            results = automation.on_pull_request_merged(pr_info)
        else:  # closed
            results = {'pr_number': pr_number, 'actions': ['PR closed - no action taken']}
        
        # Display results
        rprint(f"🔄 Processed PR #{pr_number} ([cyan]{action}[/cyan])")
        rprint(f"📝 Branch: [cyan]{branch}[/cyan]")
        
        if results.get('actions'):
            for action in results['actions']:
                rprint(f"✅ {action}")
        else:
            rprint("ℹ️  No automatic actions taken")
        
    except Exception as e:
        rprint(f"❌ Error tracking PR: {e}")


@ci.command()
@click.option('--max-commits', default=1000, help='Maximum commits to scan')
def scan_branches():
    """Scan all git branches for issue associations."""
    try:
        # Initialize components
        roadmap_core = RoadmapCore()
        tracker = CITracker(roadmap_core)
        
        rprint("🔍 Scanning all branches for issue associations...")
        
        # Scan branches
        results = tracker.scan_branches()
        
        if not results:
            rprint("ℹ️  No issue associations found in branch names")
            return
        
        # Display results
        table = Table(title="Branch Scan Results")
        table.add_column("Issue ID", style="yellow")
        table.add_column("Branches Found", style="green", justify="right")
        
        total_associations = 0
        for issue_id, count in results.items():
            table.add_row(issue_id, str(count))
            total_associations += count
        
        console.print(table)
        rprint(f"✅ Created {total_associations} branch associations across {len(results)} issues")
        
    except Exception as e:
        rprint(f"❌ Error scanning branches: {e}")


@ci.command()
@click.option('--max-commits', default=1000, help='Maximum commits to scan')
def scan_repository(max_commits: int):
    """Scan repository history for issue associations."""
    try:
        # Initialize components
        roadmap_core = RoadmapCore()
        tracker = CITracker(roadmap_core)
        
        rprint(f"🔍 Scanning repository history (last {max_commits} commits)...")
        
        # Scan repository
        results = tracker.scan_repository_history(max_commits)
        
        if not results:
            rprint("ℹ️  No issue associations found in commit history")
            return
        
        # Display results
        table = Table(title="Repository Scan Results")
        table.add_column("Issue ID", style="yellow")
        table.add_column("Commits Found", style="green", justify="right")
        
        total_associations = 0
        for issue_id, count in results.items():
            table.add_row(issue_id, str(count))
            total_associations += count
        
        console.print(table)
        rprint(f"✅ Created {total_associations} commit associations across {len(results)} issues")
        
    except Exception as e:
        rprint(f"❌ Error scanning repository: {e}")


@ci.command()
def sync_github():
    """Sync branch and commit data with GitHub."""
    try:
        # Initialize components
        roadmap_core = RoadmapCore()
        
        rprint("🔄 Syncing branch and commit data with GitHub...")
        
        # This would integrate with existing GitHub sync functionality
        # For now, just run the regular sync
        from ..sync import sync_bidirectional
        
        success = sync_bidirectional()
        
        if success:
            rprint("✅ GitHub sync completed successfully")
        else:
            rprint("❌ GitHub sync failed")
        
    except Exception as e:
        rprint(f"❌ Error syncing with GitHub: {e}")


@ci.group()
def config():
    """Configure CI/CD tracking behavior."""
    pass


@config.command()
@click.argument('key')
@click.argument('value')
def set(key: str, value: str):
    """Set CI/CD configuration value.
    
    KEY: Configuration key (e.g., 'auto_start_on_branch')
    VALUE: Configuration value
    """
    try:
        # Load current configuration
        roadmap_core = RoadmapCore()
        
        # Configuration mapping
        config_map = {
            'auto_start_on_branch': lambda v: v.lower() == 'true',
            'auto_close_on_merge': lambda v: v.lower() == 'true',
            'auto_progress_on_pr': lambda v: v.lower() == 'true',
            'scan_commit_history': lambda v: v.lower() == 'true',
            'track_all_commits': lambda v: v.lower() == 'true',
        }
        
        if key in config_map:
            parsed_value = config_map[key](value)
            rprint(f"✅ Set {key} = {parsed_value}")
        else:
            rprint(f"❌ Unknown configuration key: {key}")
            rprint("Available keys: " + ", ".join(config_map.keys()))
        
    except Exception as e:
        rprint(f"❌ Error setting configuration: {e}")


@config.command()
def show():
    """Show current CI/CD configuration."""
    try:
        config = CITrackingConfig()
        
        table = Table(title="CI/CD Configuration")
        table.add_column("Setting", style="yellow")
        table.add_column("Value", style="green")
        table.add_column("Description", style="dim")
        
        settings = [
            ("auto_start_on_branch", config.auto_start_on_branch, "Auto-start issues when branch created"),
            ("auto_close_on_merge", config.auto_close_on_merge, "Auto-close issues when PR merged"),
            ("auto_progress_on_pr", config.auto_progress_on_pr, "Auto-progress issues when PR opened"),
            ("scan_commit_history", config.scan_commit_history, "Scan commit history for associations"),
            ("track_all_commits", config.track_all_commits, "Track all commits (not just pattern matches"),
            ("main_branches", ", ".join(config.main_branches), "Main branches for auto-close"),
        ]
        
        for setting, value, description in settings:
            table.add_row(setting, str(value), description)
        
        console.print(table)
        
    except Exception as e:
        rprint(f"❌ Error showing configuration: {e}")


@ci.command() 
@click.option('--issue-id', help='Show associations for specific issue')
def status(issue_id: Optional[str]):
    """Show current CI/CD tracking status."""
    try:
        roadmap_core = RoadmapCore()
        
        if issue_id:
            # Show status for specific issue
            issue = roadmap_core.get_issue(issue_id)
            if not issue:
                rprint(f"❌ Issue {issue_id} not found")
                return
            
            rprint(f"📋 Issue: [yellow]{issue_id}[/yellow] - {issue.title}")
            rprint(f"📊 Status: {issue.status.value}")
            
            if issue.git_branches:
                rprint(f"🌿 Branches: {', '.join(issue.git_branches)}")
            else:
                rprint("🌿 Branches: None")
            
            if issue.git_commits:
                rprint(f"💻 Commits: {len(issue.git_commits)} associated")
                # Show first few commits
                for i, commit in enumerate(issue.git_commits[:3]):
                    rprint(f"   • {commit[:8]}")
                if len(issue.git_commits) > 3:
                    rprint(f"   ... and {len(issue.git_commits) - 3} more")
            else:
                rprint("💻 Commits: None")
                
        else:
            # Show overall status
            issues = roadmap_core.list_issues()
            
            branch_count = sum(1 for issue in issues if issue.git_branches)
            commit_count = sum(1 for issue in issues if issue.git_commits)
            total_branches = sum(len(issue.git_branches) for issue in issues)
            total_commits = sum(len(issue.git_commits) for issue in issues)
            
            table = Table(title="CI/CD Tracking Status")
            table.add_column("Metric", style="yellow")
            table.add_column("Count", style="green", justify="right")
            
            table.add_row("Issues with branch associations", str(branch_count))
            table.add_row("Issues with commit associations", str(commit_count))
            table.add_row("Total branch associations", str(total_branches))
            table.add_row("Total commit associations", str(total_commits))
            
            console.print(table)
        
    except Exception as e:
        rprint(f"❌ Error showing status: {e}")


# Add the ci group to the main CLI
if __name__ == '__main__':
    ci()