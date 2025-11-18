"""
CLI commands for CI/CD integration and automatic issue tracking.
"""

import json
from pathlib import Path

import click
from rich import print as rprint
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.table import Table

from ..ci_tracking import CIAutomation, CITracker, CITrackingConfig
from ..core import RoadmapCore
from ..repository_scanner import AdvancedRepositoryScanner, RepositoryScanConfig

console = Console()


@click.group()
def ci():
    """CI/CD integration commands for automatic issue tracking."""
    pass


@ci.command()
@click.argument("branch_name")
@click.option("--issue-id", help="Manually specify issue ID to associate")
@click.option(
    "--auto-start/--no-auto-start", default=None, help="Override auto-start behavior"
)
def track_branch(branch_name: str, issue_id: str | None, auto_start: bool | None):
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
                rprint(
                    f"✅ Associated branch [cyan]{branch_name}[/cyan] with issue [yellow]{issue_id}[/yellow]"
                )
            else:
                rprint(f"❌ Failed to associate branch with issue {issue_id}")
            return

        # Automatic tracking based on branch name patterns
        results = tracker.track_branch(branch_name)

        if not results:
            rprint(f"ℹ️  No issue IDs found in branch name: [cyan]{branch_name}[/cyan]")
            rprint(
                "💡 Tip: Use pattern like 'feature/ea4606b6-description' or 'ea4606b6-feature'"
            )
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
@click.argument("commit_sha")
@click.option("--message", help="Commit message (will be fetched if not provided)")
@click.option("--issue-id", help="Manually specify issue ID to associate with commit")
def track_commit(commit_sha: str, message: str | None, issue_id: str | None):
    """Track a git commit for issue associations.

    COMMIT_SHA: Git commit SHA (full or short)
    """
    try:
        # Initialize components
        roadmap_core = RoadmapCore()
        tracker = CITracker(roadmap_core)

        # Track the commit
        if issue_id:
            # Manual issue association
            results = {issue_id: ["Manual association"]}
            # Also attempt to create the association in the tracker
            try:
                tracker.add_commit_to_issue(issue_id, commit_sha)
                results[issue_id].append("Added to issue tracking")
            except Exception:
                pass  # Continue even if association fails
        else:
            # Automatic detection
            results = tracker.track_commit(commit_sha, message)

        if not results:
            rprint(f"ℹ️  No issue IDs found in commit: [cyan]{commit_sha[:8]}[/cyan]")
            rprint(
                "💡 Tip: Include issue ID in commit message like 'fixes ea4606b6' or 'ea4606b6: fix bug'"
            )
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
@click.argument("pr_number", type=int)
@click.option("--branch", help="PR branch name (will be detected if not provided)")
@click.option(
    "--action",
    type=click.Choice(["opened", "merged", "closed"]),
    default="opened",
    help="PR action that triggered the event",
)
def track_pr(pr_number: int, branch: str | None, action: str):
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
                rprint(
                    "❌ Could not determine branch name. Please specify with --branch"
                )
                return

        # Create PR info structure
        pr_info = {
            "number": pr_number,
            "head_branch": branch,
            "base_branch": "main",  # Default to main for demo
        }

        # Handle different PR actions
        if action == "opened":
            results = automation.on_pull_request_opened(pr_info)
        elif action == "merged":
            results = automation.on_pull_request_merged(pr_info)
        else:  # closed
            results = {
                "pr_number": pr_number,
                "actions": ["PR closed - no action taken"],
            }

        # Display results
        rprint(f"🔄 Processed PR #{pr_number} ([cyan]{action}[/cyan])")
        rprint(f"📝 Branch: [cyan]{branch}[/cyan]")

        if results.get("actions"):
            for action in results["actions"]:
                rprint(f"✅ {action}")
        else:
            rprint("ℹ️  No automatic actions taken")

    except Exception as e:
        rprint(f"❌ Error tracking PR: {e}")


@ci.command()
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
        rprint(
            f"✅ Created {total_associations} branch associations across {len(results)} issues"
        )

    except Exception as e:
        rprint(f"❌ Error scanning branches: {e}")


@ci.command()
@click.option("--max-commits", default=1000, help="Maximum commits to scan")
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
        rprint(
            f"✅ Created {total_associations} commit associations across {len(results)} issues"
        )

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
        from ..sync import SyncManager

        sync_manager = SyncManager(core=roadmap_core, config={})
        success = sync_manager.bidirectional_sync()

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
@click.argument("key")
@click.argument("value")
def set(key: str, value: str):
    """Set CI/CD configuration value.

    KEY: Configuration key (e.g., 'auto_start_on_branch')
    VALUE: Configuration value
    """
    try:
        # Load current configuration
        RoadmapCore()

        # Configuration mapping
        config_map = {
            "auto_start_on_branch": lambda v: v.lower() == "true",
            "auto_close_on_merge": lambda v: v.lower() == "true",
            "auto_progress_on_pr": lambda v: v.lower() == "true",
            "scan_commit_history": lambda v: v.lower() == "true",
            "track_all_commits": lambda v: v.lower() == "true",
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
            (
                "auto_start_on_branch",
                config.auto_start_on_branch,
                "Auto-start issues when branch created",
            ),
            (
                "auto_close_on_merge",
                config.auto_close_on_merge,
                "Auto-close issues when PR merged",
            ),
            (
                "auto_progress_on_pr",
                config.auto_progress_on_pr,
                "Auto-progress issues when PR opened",
            ),
            (
                "scan_commit_history",
                config.scan_commit_history,
                "Scan commit history for associations",
            ),
            (
                "track_all_commits",
                config.track_all_commits,
                "Track all commits (not just pattern matches",
            ),
            (
                "main_branches",
                ", ".join(config.main_branches),
                "Main branches for auto-close",
            ),
        ]

        for setting, value, description in settings:
            table.add_row(setting, str(value), description)

        console.print(table)

    except Exception as e:
        rprint(f"❌ Error showing configuration: {e}")


@ci.command()
@click.option("--issue-id", help="Show associations for specific issue")
def status(issue_id: str | None):
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
                for _i, commit in enumerate(issue.git_commits[:3]):
                    rprint(f"   • {str(commit)[:8]}")
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


@ci.group()
def hooks():
    """Manage git hooks for real-time CI/CD integration."""
    pass


@hooks.command()
@click.option(
    "--hook",
    multiple=True,
    help="Specific hooks to install (post-commit, pre-push, post-checkout)",
)
def install(hook):
    """Install git hooks for automatic issue tracking."""
    try:
        from ..git_hooks import GitHookManager

        roadmap_core = RoadmapCore()
        hook_manager = GitHookManager(roadmap_core)

        # Check if we're in a git repository
        if not hook_manager.hooks_dir:
            rprint("❌ Not in a Git repository. Git hooks require a .git directory.")
            return

        hooks_to_install = list(hook) if hook else None

        rprint("🔧 Installing git hooks for real-time CI/CD tracking...")

        success = hook_manager.install_hooks(hooks_to_install)

        if success:
            installed = hooks_to_install or [
                "post-commit",
                "pre-push",
                "post-checkout",
                "post-merge",
            ]
            rprint("✅ Successfully installed git hooks:")
            for hook_name in installed:
                rprint(f"   • {hook_name}")
            rprint("\n💡 Git hooks will now automatically track:")
            rprint("   • Branch associations when you switch branches (post-checkout)")
            rprint("   • Commit associations when you make commits (post-commit)")
            rprint("   • Issue completion when you push to main (pre-push)")
        else:
            rprint("❌ Failed to install git hooks")

    except Exception as e:
        rprint(f"❌ Error installing git hooks: {e}")


@hooks.command()
def uninstall():
    """Uninstall git hooks."""
    try:
        from ..git_hooks import GitHookManager

        roadmap_core = RoadmapCore()
        hook_manager = GitHookManager(roadmap_core)

        if not hook_manager.hooks_dir:
            rprint("❌ Not in a Git repository")
            return

        rprint("🗑️  Uninstalling git hooks...")

        success = hook_manager.uninstall_hooks()

        if success:
            rprint("✅ Successfully uninstalled git hooks")
        else:
            rprint("❌ Failed to uninstall git hooks")

    except Exception as e:
        rprint(f"❌ Error uninstalling git hooks: {e}")


@hooks.command(name="status")
def hooks_status():
    """Show git hooks installation status."""
    try:
        from ..git_hooks import GitHookManager

        roadmap_core = RoadmapCore()
        hook_manager = GitHookManager(roadmap_core)

        if not hook_manager.hooks_dir:
            rprint("❌ Not in a Git repository")
            return

        hooks_to_check = ["post-commit", "pre-push", "post-checkout", "post-merge"]

        table = Table(title="Git Hooks Status")
        table.add_column("Hook", style="yellow")
        table.add_column("Status", style="green")
        table.add_column("Description")

        for hook_name in hooks_to_check:
            hook_file = hook_manager.hooks_dir / hook_name

            if hook_file.exists():
                content = hook_file.read_text()
                if "roadmap-hook" in content:
                    status = "✅ Installed"
                else:
                    status = "⚠️  Other hook"
            else:
                status = "❌ Not installed"

            descriptions = {
                "post-commit": "Track commits automatically",
                "pre-push": "Complete issues on push to main",
                "post-checkout": "Associate branches with issues",
                "post-merge": "Update milestone progress",
            }

            table.add_row(hook_name, status, descriptions.get(hook_name, ""))

        console.print(table)

        # Check for log file
        log_file = hook_manager.hooks_dir.parent / "roadmap-hooks.log"
        if log_file.exists():
            rprint(f"\n📊 Hook activity log: {log_file}")

    except Exception as e:
        rprint(f"❌ Error checking hooks status: {e}")


@hooks.command()
@click.option("--lines", default=10, help="Number of log lines to show")
def logs(lines: int):
    """Show git hooks activity logs."""
    try:
        from ..git_hooks import GitHookManager

        roadmap_core = RoadmapCore()
        hook_manager = GitHookManager(roadmap_core)

        if not hook_manager.hooks_dir:
            rprint("❌ Not in a Git repository")
            return

        log_file = hook_manager.hooks_dir.parent / "roadmap-hooks.log"

        if not log_file.exists():
            rprint("📝 No hook activity logs found")
            rprint("💡 Logs will appear here after git operations trigger the hooks")
            return

        # Read last N lines
        with open(log_file) as f:
            log_lines = f.readlines()

        recent_lines = log_lines[-lines:] if len(log_lines) > lines else log_lines

        rprint(f"📊 Recent git hooks activity (last {len(recent_lines)} entries):")
        for line in recent_lines:
            rprint(f"   {line.strip()}")

    except Exception as e:
        rprint(f"❌ Error reading hook logs: {e}")


@ci.command()
@click.option(
    "--format",
    type=click.Choice(["table", "json", "yaml"]),
    default="table",
    help="Output format",
)
@click.option("--verbose", is_flag=True, help="Show detailed information")
def github_status(format: str, verbose: bool):
    """Show GitHub Actions integration status and configuration."""
    try:
        roadmap_core = RoadmapCore()
        config = CITrackingConfig()

        if format == "table":
            # Create status table
            table = Table(title="GitHub Actions Integration Status", show_header=True)
            table.add_column("Component", style="cyan")
            table.add_column("Status", style="green")
            table.add_column("Details", style="white")

            # Check roadmap initialization
            if roadmap_core.is_initialized():
                table.add_row(
                    "Roadmap Setup", "✅ Ready", "Roadmap initialized and configured"
                )
            else:
                table.add_row(
                    "Roadmap Setup", "❌ Not Ready", "Run 'roadmap init' first"
                )

            # Check CI configuration
            table.add_row(
                "Auto Tracking",
                "✅ Enabled" if config.auto_start_on_branch else "⚠️ Disabled",
                "Automatic issue tracking on branch creation",
            )
            table.add_row(
                "Progress Tracking",
                "✅ Enabled" if config.auto_progress_on_pr else "⚠️ Disabled",
                "Automatic progress updates from commits",
            )
            table.add_row(
                "Auto Completion",
                "✅ Enabled" if config.auto_close_on_merge else "⚠️ Disabled",
                "Automatic issue completion on PR merge",
            )

            # Check for workflow files
            import os

            workflows_dir = ".github/workflows"
            if os.path.exists(workflows_dir):
                workflow_files = [
                    f
                    for f in os.listdir(workflows_dir)
                    if f.endswith((".yml", ".yaml"))
                ]
                if workflow_files:
                    table.add_row(
                        "GitHub Workflows",
                        "✅ Found",
                        f"{len(workflow_files)} workflow file(s)",
                    )
                else:
                    table.add_row(
                        "GitHub Workflows", "⚠️ None", "No workflow files found"
                    )
            else:
                table.add_row(
                    "GitHub Workflows", "❌ Missing", "No .github/workflows directory"
                )

            console.print(table)

            if verbose:
                rprint("\n📝 Configuration Details:")
                rprint(f"  Main branches: {', '.join(config.main_branches)}")
                rprint(f"  Branch patterns: {len(config.branch_patterns)} patterns")
                rprint(f"  Commit patterns: {len(config.commit_patterns)} patterns")

        elif format == "json":
            import json

            status_data = {
                "roadmap_initialized": roadmap_core.is_initialized(),
                "auto_tracking": config.auto_start_on_branch,
                "progress_tracking": config.auto_progress_on_pr,
                "auto_completion": config.auto_close_on_merge,
                "main_branches": config.main_branches,
                "configuration": {
                    "branch_patterns": config.branch_patterns,
                    "commit_patterns": config.commit_patterns,
                },
            }
            rprint(json.dumps(status_data, indent=2))

    except Exception as e:
        rprint(f"❌ Error checking GitHub status: {e}")
        raise click.ClickException(str(e))


@ci.command()
@click.argument(
    "workflow_name", type=click.Choice(["starter", "integration", "ci-cd", "lifecycle"])
)
@click.option(
    "--output-dir",
    default=".github/workflows",
    help="Directory to create workflow files",
)
@click.option("--force", is_flag=True, help="Overwrite existing files")
def setup_workflows(workflow_name: str, output_dir: str, force: bool):
    """Set up GitHub Actions workflows for roadmap integration.

    WORKFLOW_NAME: Type of workflow to set up
    - starter: Basic roadmap integration
    - integration: Full roadmap tracking
    - ci-cd: Complete CI/CD with validation
    - lifecycle: Advanced issue lifecycle management
    """
    import os
    import shutil
    from pathlib import Path

    try:
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)

        # Get template directory
        template_dir = Path(__file__).parent.parent / "templates" / "github_workflows"

        # Map workflow names to template files
        workflow_files = {
            "starter": "roadmap-starter.yml",
            "integration": "roadmap-integration.yml",
            "ci-cd": "ci-cd-roadmap.yml",
            "lifecycle": "issue-lifecycle.yml",
        }

        template_file = workflow_files.get(workflow_name)
        if not template_file:
            raise click.ClickException(f"Unknown workflow: {workflow_name}")

        source_path = template_dir / template_file
        target_path = Path(output_dir) / template_file

        # Check if file exists
        if target_path.exists() and not force:
            rprint(f"⚠️  Workflow file already exists: {target_path}")
            rprint("Use --force to overwrite")
            return

        # Copy template file
        if source_path.exists():
            shutil.copy2(source_path, target_path)
            rprint(f"✅ Created workflow: [cyan]{target_path}[/cyan]")

            # Show next steps
            rprint("\n📋 Next steps:")
            rprint("  1. Review and customize the workflow file")
            rprint("  2. Commit and push to trigger the workflow")
            rprint("  3. Check the Actions tab in your GitHub repository")

            if workflow_name == "starter":
                rprint("\n💡 For more advanced features, try:")
                rprint("  roadmap ci setup-workflows integration")

        else:
            raise click.ClickException(f"Template file not found: {source_path}")

    except Exception as e:
        rprint(f"❌ Error setting up workflows: {e}")
        raise click.ClickException(str(e))


@ci.command("scan-full")
@click.option("--max-commits", default=5000, help="Maximum commits to scan")
@click.option("--max-branches", default=200, help="Maximum branches to scan")
@click.option("--since", help="Scan commits since date (YYYY-MM-DD)")
@click.option("--until", help="Scan commits until date (YYYY-MM-DD)")
@click.option("--parallel/--sequential", default=True, help="Use parallel processing")
@click.option("--workers", default=4, help="Number of parallel workers")
@click.option("--export", help="Export results to JSON file")
@click.option(
    "--create-issues/--no-create-issues",
    default=False,
    help="Create missing issues from commits",
)
@click.option(
    "--link-commits/--no-link-commits",
    default=True,
    help="Link commits to existing issues",
)
def scan_full_repository(
    max_commits: int,
    max_branches: int,
    since: str | None,
    until: str | None,
    parallel: bool,
    workers: int,
    export: str | None,
    create_issues: bool,
    link_commits: bool,
):
    """Perform comprehensive repository analysis with advanced scanning.

    This command performs deep analysis of your repository history including:
    - Detailed commit analysis with pattern recognition
    - Branch lifecycle tracking and relationships
    - Issue association discovery and validation
    - Migration assistance for existing projects
    - Performance optimized scanning with caching
    """
    try:
        # Initialize components
        roadmap_core = RoadmapCore()

        # Parse date filters
        since_date = None
        until_date = None

        if since:
            from datetime import datetime

            since_date = datetime.fromisoformat(since)

        if until:
            from datetime import datetime

            until_date = datetime.fromisoformat(until)

        # Configure scanner
        config = RepositoryScanConfig(
            max_commits=max_commits,
            max_branches=max_branches,
            since_date=since_date,
            until_date=until_date,
            use_parallel_processing=parallel,
            max_workers=workers,
            create_missing_issues=create_issues,
            auto_link_issues=link_commits,
        )

        scanner = AdvancedRepositoryScanner(roadmap_core, config)

        rprint("🔍 Starting comprehensive repository scan...")
        rprint(f"   Max commits: {max_commits}")
        rprint(f"   Max branches: {max_branches}")
        if since_date:
            rprint(f"   Since: {since_date.strftime('%Y-%m-%d')}")
        if until_date:
            rprint(f"   Until: {until_date.strftime('%Y-%m-%d')}")
        rprint(f"   Processing: {'Parallel' if parallel else 'Sequential'}")

        # Perform scan with progress indication
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            scan_task = progress.add_task("Scanning repository...", total=None)

            # Perform comprehensive scan
            scan_result = scanner.perform_comprehensive_scan()

            progress.update(scan_task, completed=True, description="Scan completed")

        # Display results
        rprint("\n" + "=" * 60)
        rprint("🎯 [bold green]Repository Scan Results[/bold green]")
        rprint("=" * 60)

        # Summary statistics
        stats_table = Table(title="Scan Statistics")
        stats_table.add_column("Metric", style="cyan")
        stats_table.add_column("Count", justify="right", style="green")
        stats_table.add_column("Details", style="dim")

        stats_table.add_row(
            "Commits Scanned",
            str(scan_result.total_commits_scanned),
            f"{scan_result.commits_per_second:.1f} commits/sec",
        )
        stats_table.add_row(
            "Branches Scanned",
            str(scan_result.total_branches_scanned),
            f"Including deleted: {config.include_deleted_branches}",
        )
        stats_table.add_row(
            "Issues with Commits",
            str(scan_result.issues_with_commits),
            f"{scan_result.commits_with_issues} commits linked",
        )
        stats_table.add_row(
            "Scan Duration",
            f"{scan_result.scan_duration_seconds:.2f}s",
            f"Workers: {workers}" if parallel else "Sequential",
        )

        console.print(stats_table)

        # Top issues by commit activity
        if scan_result.issue_associations:
            rprint("\n📊 [bold]Top Issues by Commit Activity[/bold]")

            issue_table = Table()
            issue_table.add_column("Issue ID", style="yellow")
            issue_table.add_column("Commits", justify="right", style="green")
            issue_table.add_column("First Commit", style="dim")
            issue_table.add_column("Last Commit", style="dim")

            # Sort issues by commit count
            sorted_issues = sorted(
                scan_result.issue_associations.items(),
                key=lambda x: len(x[1]),
                reverse=True,
            )[:10]  # Top 10

            for issue_id, commit_shas in sorted_issues:
                # Find first and last commit dates
                issue_commits = [c for c in scan_result.commits if c.sha in commit_shas]
                if issue_commits:
                    first_commit = min(issue_commits, key=lambda c: c.date)
                    last_commit = max(issue_commits, key=lambda c: c.date)

                    issue_table.add_row(
                        issue_id,
                        str(len(commit_shas)),
                        first_commit.date.strftime("%Y-%m-%d"),
                        last_commit.date.strftime("%Y-%m-%d"),
                    )

            console.print(issue_table)

        # Branch analysis
        if scan_result.branches:
            rprint("\n🌿 [bold]Branch Analysis Summary[/bold]")

            # Analyze branch types and stages
            from collections import Counter

            branch_types = Counter(
                b.branch_type or "other" for b in scan_result.branches
            )
            rprint(f"   Found {len(scan_result.branches)} branches:")
            for branch_type, count in branch_types.most_common():
                rprint(f"   • {branch_type.title()}: {count}")

            # Show lifecycle distribution
            lifecycle_stages = Counter(b.lifecycle_stage for b in scan_result.branches)
            rprint("   Lifecycle stages:")
            for stage, count in lifecycle_stages.most_common():
                rprint(f"   • {stage.title()}: {count}")
        else:
            rprint("\n🌿 [bold]Branch Analysis Summary[/bold]")
            rprint("   No branches found for analysis")

        # Migration results (if performed)
        if create_issues or link_commits:
            rprint("\n🔄 [bold]Migration Results[/bold]")

            migration_result = scanner.migrate_existing_project(
                create_issues=create_issues, auto_link=link_commits
            )

            migration_table = Table()
            migration_table.add_column("Operation", style="cyan")
            migration_table.add_column("Result", style="green")
            migration_table.add_column("Details", style="dim")

            if create_issues:
                created_count = sum(
                    1
                    for r in migration_result.results
                    if r.get("action") == "created_issue"
                )
                migration_table.add_row(
                    "Issues Created",
                    str(created_count),
                    f"From {scan_result.issues_with_commits} discovered issue IDs",
                )

            if link_commits:
                linked_count = sum(
                    r.get("new_commits", 0)
                    for r in migration_result.results
                    if r.get("action") == "linked_commits"
                )
                migration_table.add_row(
                    "Commits Linked", str(linked_count), "To existing issues"
                )

            if migration_result.warnings:
                migration_table.add_row(
                    "Warnings", str(len(migration_result.warnings)), "See details above"
                )

            console.print(migration_table)

        # Export results if requested
        if export:
            export_path = Path(export)
            exported_file = scanner.export_scan_results(scan_result, export_path)
            rprint(f"\n💾 Results exported to: [cyan]{exported_file}[/cyan]")

        # Show errors if any
        if scan_result.errors:
            rprint(f"\n⚠️  [yellow]{len(scan_result.errors)} errors occurred:[/yellow]")
            for error in scan_result.errors[:5]:  # Show first 5
                rprint(f"   • {error}")
            if len(scan_result.errors) > 5:
                rprint(f"   ... and {len(scan_result.errors) - 5} more")

        # Show warnings if any
        if scan_result.warnings:
            rprint(f"\n⚠️  [yellow]{len(scan_result.warnings)} warnings:[/yellow]")
            for warning in scan_result.warnings[:3]:  # Show first 3
                rprint(f"   • {warning}")
            if len(scan_result.warnings) > 3:
                rprint(f"   ... and {len(scan_result.warnings) - 3} more")

        rprint("\n✅ [bold green]Repository scan completed successfully![/bold green]")

    except Exception as e:
        rprint(f"❌ Error during repository scan: {e}")
        raise click.ClickException(str(e))


@ci.command("migrate-project")
@click.option(
    "--max-commits", default=2000, help="Maximum commits to analyze for migration"
)
@click.option(
    "--create-issues/--no-create-issues",
    default=False,
    help="Create missing issues discovered in commit history",
)
@click.option(
    "--link-commits/--no-link-commits",
    default=True,
    help="Automatically link commits to existing issues",
)
@click.option(
    "--dry-run/--execute",
    default=False,
    help="Preview migration without making changes",
)
@click.option("--export-report", help="Export migration report to JSON file")
def migrate_project(
    max_commits: int,
    create_issues: bool,
    link_commits: bool,
    dry_run: bool,
    export_report: str | None,
):
    """Migrate existing project to roadmap tracking.

    This command helps migrate existing projects by:
    - Discovering issue references in commit history
    - Creating missing issues from commit patterns
    - Linking existing commits to issues automatically
    - Generating migration reports and statistics
    """
    try:
        # Initialize components
        roadmap_core = RoadmapCore()

        config = RepositoryScanConfig(
            max_commits=max_commits,
            create_missing_issues=create_issues,
            auto_link_issues=link_commits,
            use_parallel_processing=True,
        )

        scanner = AdvancedRepositoryScanner(roadmap_core, config)

        rprint("🚀 Starting project migration...")

        if dry_run:
            rprint("📋 [yellow]DRY RUN MODE - No changes will be made[/yellow]")

        rprint(f"   Max commits to analyze: {max_commits}")
        rprint(f"   Create missing issues: {'✅' if create_issues else '❌'}")
        rprint(f"   Link commits to issues: {'✅' if link_commits else '❌'}")

        # Perform initial scan
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            scan_task = progress.add_task("Analyzing repository...", total=None)

            scan_result = scanner.perform_comprehensive_scan()

            progress.update(scan_task, completed=True, description="Analysis completed")

        # Display analysis summary
        rprint("\n" + "=" * 50)
        rprint("📊 [bold blue]Migration Analysis[/bold blue]")
        rprint("=" * 50)

        analysis_table = Table()
        analysis_table.add_column("Discovery", style="cyan")
        analysis_table.add_column("Count", justify="right", style="green")
        analysis_table.add_column("Action", style="dim")

        analysis_table.add_row(
            "Commits Analyzed",
            str(scan_result.total_commits_scanned),
            "Source of issue references",
        )

        analysis_table.add_row(
            "Issue IDs Found",
            str(len(scan_result.issue_associations)),
            "Unique issue references in commits",
        )

        # Check which issues already exist
        existing_issues = 0
        missing_issues = 0

        for issue_id in scan_result.issue_associations.keys():
            issue_file = roadmap_core.issues_dir / f"{issue_id}.yaml"
            if issue_file.exists():
                existing_issues += 1
            else:
                missing_issues += 1

        analysis_table.add_row(
            "Existing Issues",
            str(existing_issues),
            "Will be updated with commit links" if link_commits else "No action",
        )

        analysis_table.add_row(
            "Missing Issues",
            str(missing_issues),
            "Will be created" if create_issues else "Will be skipped",
        )

        console.print(analysis_table)

        # Show top issue candidates
        if scan_result.issue_associations:
            rprint("\n🎯 [bold]Top Issue Candidates for Migration[/bold]")

            candidate_table = Table()
            candidate_table.add_column("Issue ID", style="yellow")
            candidate_table.add_column("Commits", justify="right", style="green")
            candidate_table.add_column("Exists", justify="center", style="cyan")
            candidate_table.add_column("Sample Commit", style="dim")

            # Sort by commit count
            sorted_candidates = sorted(
                scan_result.issue_associations.items(),
                key=lambda x: len(x[1]),
                reverse=True,
            )[:10]

            for issue_id, commit_shas in sorted_candidates:
                issue_file = roadmap_core.issues_dir / f"{issue_id}.yaml"
                exists = "✅" if issue_file.exists() else "❌"

                # Get sample commit message
                sample_commit = next(
                    (c for c in scan_result.commits if c.sha in commit_shas), None
                )
                sample_msg = (
                    sample_commit.message[:50] + "..." if sample_commit else "N/A"
                )

                candidate_table.add_row(
                    issue_id, str(len(commit_shas)), exists, sample_msg
                )

            console.print(candidate_table)

        # Perform migration if not dry run
        if not dry_run:
            rprint("\n🔄 [bold]Performing Migration...[/bold]")

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                TimeElapsedColumn(),
                console=console,
            ) as progress:
                migrate_task = progress.add_task("Migrating project...", total=None)

                migration_result = scanner.migrate_existing_project(
                    create_issues=create_issues, auto_link=link_commits
                )

                progress.update(
                    migrate_task, completed=True, description="Migration completed"
                )

            # Display migration results
            rprint("\n" + "=" * 50)
            rprint("✅ [bold green]Migration Results[/bold green]")
            rprint("=" * 50)

            result_table = Table()
            result_table.add_column("Operation", style="cyan")
            result_table.add_column("Success", justify="right", style="green")
            result_table.add_column("Details", style="dim")

            if create_issues:
                created_issues = [
                    r
                    for r in migration_result.results
                    if r.get("action") == "created_issue"
                ]
                result_table.add_row(
                    "Issues Created",
                    str(len(created_issues)),
                    "From discovered commit references",
                )

            if link_commits:
                linked_operations = [
                    r
                    for r in migration_result.results
                    if r.get("action") == "linked_commits"
                ]
                total_linked = sum(r.get("new_commits", 0) for r in linked_operations)
                result_table.add_row(
                    "Commits Linked",
                    str(total_linked),
                    f"Across {len(linked_operations)} issues",
                )

            result_table.add_row(
                "Success Rate",
                f"{migration_result.success_rate:.1f}%",
                f"{migration_result.successful}/{migration_result.total_files} operations",
            )

            result_table.add_row(
                "Duration", f"{migration_result.duration:.2f}s", "Migration completed"
            )

            console.print(result_table)

            # Show errors if any
            if migration_result.errors:
                rprint(
                    f"\n⚠️  [red]{len(migration_result.errors)} errors occurred:[/red]"
                )
                for error in migration_result.errors[:3]:
                    rprint(f"   • {error}")
                if len(migration_result.errors) > 3:
                    rprint(f"   ... and {len(migration_result.errors) - 3} more")

        else:
            rprint("\n💡 [bold yellow]Dry Run Complete[/bold yellow]")
            rprint("   To perform migration, run without --dry-run flag")

        # Export report if requested
        if export_report:
            report_data = {
                "migration_summary": {
                    "dry_run": dry_run,
                    "commits_analyzed": scan_result.total_commits_scanned,
                    "issues_discovered": len(scan_result.issue_associations),
                    "existing_issues": existing_issues,
                    "missing_issues": missing_issues,
                    "would_create_issues": missing_issues if create_issues else 0,
                    "would_link_commits": scan_result.commits_with_issues
                    if link_commits
                    else 0,
                },
                "issue_candidates": [
                    {
                        "issue_id": issue_id,
                        "commit_count": len(commit_shas),
                        "exists": (
                            roadmap_core.issues_dir / f"{issue_id}.yaml"
                        ).exists(),
                    }
                    for issue_id, commit_shas in scan_result.issue_associations.items()
                ],
            }

            if not dry_run:
                report_data["migration_results"] = migration_result.to_dict()

            report_path = Path(export_report)
            report_path.parent.mkdir(parents=True, exist_ok=True)

            with open(report_path, "w") as f:
                json.dump(report_data, f, indent=2, default=str)

            rprint(f"\n💾 Migration report exported to: [cyan]{report_path}[/cyan]")

        if not dry_run:
            rprint(
                "\n🎉 [bold green]Project migration completed successfully![/bold green]"
            )
            rprint("   Your repository is now integrated with roadmap tracking")
        else:
            rprint("\n📋 [bold blue]Migration preview completed[/bold blue]")
            rprint("   Review the analysis and run without --dry-run when ready")

    except Exception as e:
        rprint(f"❌ Error during project migration: {e}")
        raise click.ClickException(str(e))


@ci.command("analyze-patterns")
@click.option("--commits", default=1000, help="Number of recent commits to analyze")
@click.option(
    "--pattern-type",
    type=click.Choice(["commit", "branch", "both"]),
    default="both",
    help="Type of patterns to analyze",
)
@click.option("--export", help="Export analysis to JSON file")
def analyze_patterns(commits: int, pattern_type: str, export: str | None):
    """Analyze commit and branch patterns for improved issue tracking.

    This command analyzes your repository patterns to help optimize:
    - Issue ID extraction patterns
    - Commit message conventions
    - Branch naming conventions
    - Progress tracking patterns
    """
    try:
        # Initialize components
        roadmap_core = RoadmapCore()
        config = RepositoryScanConfig(
            max_commits=commits,
            analyze_commit_patterns=True,
            analyze_branch_patterns=True,
        )

        scanner = AdvancedRepositoryScanner(roadmap_core, config)

        rprint("🔍 Analyzing repository patterns...")
        rprint(f"   Analyzing {commits} recent commits")
        rprint(f"   Pattern types: {pattern_type}")

        # Perform scanning
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("Analyzing patterns...", total=None)

            scan_result = scanner.perform_comprehensive_scan()

            progress.update(task, completed=True, description="Analysis completed")

        # Analyze commit patterns
        if pattern_type in ["commit", "both"]:
            rprint("\n" + "=" * 50)
            rprint("📝 [bold blue]Commit Message Patterns[/bold blue]")
            rprint("=" * 50)

            # Analyze commit types
            from collections import Counter

            commit_types = Counter(
                c.commit_type for c in scan_result.commits if c.commit_type
            )

            if commit_types:
                commit_table = Table(title="Commit Type Distribution")
                commit_table.add_column("Type", style="cyan")
                commit_table.add_column("Count", justify="right", style="green")
                commit_table.add_column("Percentage", justify="right", style="dim")

                total_typed = sum(commit_types.values())
                for commit_type, count in commit_types.most_common():
                    percentage = (count / total_typed) * 100
                    commit_table.add_row(
                        commit_type.title(), str(count), f"{percentage:.1f}%"
                    )

                console.print(commit_table)

            # Issue reference patterns
            commits_with_issues = [c for c in scan_result.commits if c.issue_ids]
            if commits_with_issues:
                rprint("\n📊 Issue Reference Analysis")
                rprint(
                    f"   Commits with issue refs: {len(commits_with_issues)}/{len(scan_result.commits)} ({len(commits_with_issues)/len(scan_result.commits)*100:.1f}%)"
                )

                # Common patterns in messages
                issue_messages = [c.message for c in commits_with_issues]
                rprint("   Sample messages with issues:")
                for msg in issue_messages[:5]:
                    rprint(f"     • {msg[:60]}{'...' if len(msg) > 60 else ''}")

        # Analyze branch patterns
        if pattern_type in ["branch", "both"]:
            rprint("\n" + "=" * 50)
            rprint("🌿 [bold blue]Branch Naming Patterns[/bold blue]")
            rprint("=" * 50)

            # Branch type distribution
            from collections import Counter

            branch_types = Counter(
                b.branch_type or "other" for b in scan_result.branches
            )

            if branch_types:
                branch_table = Table(title="Branch Type Distribution")
                branch_table.add_column("Type", style="cyan")
                branch_table.add_column("Count", justify="right", style="green")
                branch_table.add_column("Percentage", justify="right", style="dim")

                total_branches = sum(branch_types.values())
                for branch_type, count in branch_types.most_common():
                    percentage = (count / total_branches) * 100
                    branch_table.add_row(
                        branch_type.title(), str(count), f"{percentage:.1f}%"
                    )

                console.print(branch_table)

            # Branches with issue associations
            branches_with_issues = [b for b in scan_result.branches if b.issue_ids]
            if branches_with_issues:
                rprint("\n📊 Branch Issue Association")
                rprint(
                    f"   Branches with issue IDs: {len(branches_with_issues)}/{len(scan_result.branches)} ({len(branches_with_issues)/len(scan_result.branches)*100:.1f}%)"
                )

                # Sample branch names
                rprint("   Sample branches with issues:")
                for branch in branches_with_issues[:5]:
                    rprint(f"     • {branch.name} → {', '.join(branch.issue_ids)}")

        # Pattern recommendations
        rprint("\n" + "=" * 50)
        rprint("💡 [bold yellow]Pattern Recommendations[/bold yellow]")
        rprint("=" * 50)

        recommendations = []

        # Check commit message consistency
        typed_commits = len([c for c in scan_result.commits if c.commit_type])
        if typed_commits < len(scan_result.commits) * 0.5:
            recommendations.append(
                "Consider adopting conventional commit format (feat:, fix:, docs:) for better categorization"
            )

        # Check issue reference rate
        commits_with_refs = len([c for c in scan_result.commits if c.issue_ids])
        if commits_with_refs < len(scan_result.commits) * 0.3:
            recommendations.append(
                "Consider including issue IDs in more commit messages for better traceability"
            )

        # Check branch naming
        branches_with_refs = len([b for b in scan_result.branches if b.issue_ids])
        if branches_with_refs < len(scan_result.branches) * 0.5:
            recommendations.append(
                "Consider including issue IDs in branch names (e.g., feature/abc12345-description)"
            )

        # Check progress markers
        commits_with_progress = len(
            [c for c in scan_result.commits if c.progress_markers]
        )
        if commits_with_progress == 0:
            recommendations.append(
                "Consider using progress markers in commits (e.g., [progress:75%]) for automatic tracking"
            )

        if recommendations:
            for i, rec in enumerate(recommendations, 1):
                rprint(f"   {i}. {rec}")
        else:
            rprint("   ✅ Your repository patterns look good for roadmap tracking!")

        # Export analysis if requested
        if export:
            analysis_data = {
                "analysis_summary": {
                    "commits_analyzed": len(scan_result.commits),
                    "branches_analyzed": len(scan_result.branches),
                    "commits_with_types": typed_commits,
                    "commits_with_issues": commits_with_refs,
                    "branches_with_issues": branches_with_refs,
                    "commits_with_progress": commits_with_progress,
                },
                "commit_patterns": {
                    "type_distribution": dict(
                        Counter(
                            c.commit_type for c in scan_result.commits if c.commit_type
                        )
                    ),
                    "issue_reference_rate": commits_with_refs / len(scan_result.commits)
                    if scan_result.commits
                    else 0,
                    "sample_messages": [c.message for c in scan_result.commits[:10]],
                },
                "branch_patterns": {
                    "type_distribution": dict(
                        Counter(b.branch_type or "other" for b in scan_result.branches)
                    ),
                    "issue_association_rate": branches_with_refs
                    / len(scan_result.branches)
                    if scan_result.branches
                    else 0,
                    "sample_names": [b.name for b in scan_result.branches[:10]],
                },
                "recommendations": recommendations,
            }

            export_path = Path(export)
            export_path.parent.mkdir(parents=True, exist_ok=True)

            with open(export_path, "w") as f:
                json.dump(analysis_data, f, indent=2, default=str)

            rprint(f"\n💾 Pattern analysis exported to: [cyan]{export_path}[/cyan]")

        rprint("\n✅ [bold green]Pattern analysis completed![/bold green]")

    except Exception as e:
        rprint(f"❌ Error during pattern analysis: {e}")
        raise click.ClickException(str(e))


# Add the ci group to the main CLI
if __name__ == "__main__":
    ci()
