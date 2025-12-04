"""
Core CLI commands: init and status.
These are the fundamental commands needed to get started with Roadmap.
"""

import getpass
import os
import subprocess
from datetime import datetime
from pathlib import Path

import click
from rich.progress import BarColumn, Progress, TextColumn
from rich.table import Table
from rich.text import Text

from roadmap.application.core import RoadmapCore
from roadmap.application.health import HealthCheck, HealthStatus
from roadmap.cli.github_setup import (
    GitHubConfigManager,
    GitHubSetupValidator,
    GitHubTokenResolver,
    show_github_setup_instructions,
)
from roadmap.cli.init_workflow import (
    InitializationLock,
    InitializationManifest,
    InitializationValidator,
    InitializationWorkflow,
    show_dry_run_info,
)
from roadmap.domain import Status
from roadmap.presentation.cli.logging_decorators import verbose_output
from roadmap.shared.console import get_console
from roadmap.shared.logging import get_logger

console = get_console()
logger = get_logger(__name__)
# Import GitHub client and credential manager at module level so they can be patched in tests
try:
    from roadmap.infrastructure.github import GitHubClient
    from roadmap.infrastructure.security.credentials import CredentialManager
except Exception:
    GitHubClient = None
    CredentialManager = None


@click.command()
@click.option(
    "--name",
    "-n",
    default=".roadmap",
    help="Name of the roadmap directory (default: .roadmap)",
)
@click.option(
    "--project-name",
    help="Name of the main project (auto-detected if not provided)",
)
@click.option(
    "--description",
    help="Project description",
)
@click.option(
    "--github-repo",
    help="GitHub repository in owner/repo format",
)
@click.option(
    "--skip-github",
    is_flag=True,
    help="Skip GitHub integration setup",
)
@click.option(
    "--skip-project",
    is_flag=True,
    help="Skip automatic project creation",
)
@click.option(
    "--interactive/--non-interactive",
    default=True,
    help="Run in interactive mode with prompts (default: interactive)",
)
@click.option(
    "--template",
    type=click.Choice(["basic", "software", "research", "team"]),
    default="basic",
    help="Use project template",
)
@click.option(
    "--template-path",
    type=click.Path(exists=False),
    help="Path to a custom project template file (markdown).",
)
@click.option(
    "--github-token",
    help="Provide a GitHub personal access token to configure integration non-interactively",
)
@click.option(
    "--dry-run", is_flag=True, help="Show what would be created without making changes"
)
@click.option(
    "--yes", "-y", is_flag=True, help="Automatic yes to prompts (assume defaults)"
)
@click.option(
    "--force", is_flag=True, help="Force re-initialization when roadmap already exists"
)
@click.pass_context
def init(
    ctx: click.Context,
    name: str,
    project_name: str | None,
    description: str | None,
    github_repo: str | None,
    skip_github: bool,
    skip_project: bool,
    interactive: bool,
    dry_run: bool,
    yes: bool,
    force: bool,
    template: str,
    template_path: str | None,
    github_token: str | None,
) -> None:
    """Initialize a new roadmap with automatic project setup and credential flow.

    Examples:
        roadmap init                              # Interactive setup with auto-detection
        roadmap init --project-name "My Project" # Specify project name
        roadmap init --skip-github               # Skip GitHub integration
        roadmap init --github-repo owner/repo    # Specify GitHub repository
        roadmap init --template software         # Use software project template
    """
    log = logger.bind(
        operation="init",
        name=name,
        skip_github=skip_github,
        interactive=interactive,
        dry_run=dry_run,
        force=force,
    )
    log.info("starting_init")

    # Create a new core instance with the custom directory name
    roadmap_dir = Path.cwd() / name
    custom_core = RoadmapCore(roadmap_dir_name=name)

    # Handle dry-run mode
    if dry_run:
        config_file = roadmap_dir / "config.yaml"
        is_initialized = roadmap_dir.exists() and config_file.exists()
        log.info("dry_run_mode", is_initialized=is_initialized)
        show_dry_run_info(name, is_initialized, force, skip_project, skip_github)
        return

    # Validate initialization prerequisites
    lock_path = Path.cwd() / ".roadmap_init.lock"
    is_valid, error_msg = InitializationValidator.validate_lockfile(lock_path)
    if not is_valid:
        console.print(f"❌ {error_msg}", style="bold red")
        return

    is_valid, error_msg = InitializationValidator.check_existing_roadmap(
        custom_core, force
    )
    if not is_valid:
        console.print(f"❌ {error_msg}", style="bold red")
        console.print(
            "Tip: use --force to reinitialize or --dry-run to preview.", style="yellow"
        )
        return

    # Acquire initialization lock
    lock = InitializationLock(lock_path)
    if not lock.acquire():
        console.print(
            "❌ Initialization already in progress. Try again later.", style="bold red"
        )
        return

    # Initialize workflow
    workflow = InitializationWorkflow(custom_core)
    manifest = InitializationManifest(custom_core.roadmap_dir / ".init_manifest.json")

    console.print("🚀 Roadmap CLI Initialization", style="bold cyan")
    console.print()

    try:
        # Handle force re-initialization
        if custom_core.is_initialized() and force:
            console.print(
                f"⚠️  --force specified: removing existing {name}/", style="yellow"
            )
            if not workflow.cleanup_existing():
                return

        # Step 1: Detect context
        detected_info = _detect_project_context()
        _show_detected_context(detected_info, interactive)

        # Step 2: Create roadmap structure
        with console.status(
            f"🗂️  Creating roadmap structure in {name}/...", spinner="dots"
        ):
            workflow.create_structure()
            workflow.record_created_paths(manifest)

        ctx.obj["core"] = custom_core

        # Step 3: Create main project (unless skipped)
        project_info = None
        if not skip_project:
            project_info = _create_main_project(
                custom_core,
                manifest,
                project_name,
                description,
                detected_info,
                interactive,
                template,
                yes,
                template_path,
            )
            if project_info:
                console.print(
                    f"✅ Created main project: {project_info['name']} (ID: {project_info['id'][:8]})"
                )

        # Step 4: Configure GitHub integration (unless skipped)
        github_configured = _configure_github(
            custom_core,
            skip_github,
            github_repo,
            detected_info,
            interactive,
            yes,
            github_token,
        )

        # Step 5: Validate and show summary
        validation_ok = InitializationValidator.post_init_validate(
            custom_core, name, project_info
        )
        if not validation_ok:
            console.print(
                "⚠️  Initialization completed with warnings; see above.", style="yellow"
            )

        _show_success_summary(name, github_configured, project_info, detected_info)

    except Exception as e:
        log.error("init_failed", error=str(e))
        console.print(f"❌ Failed to initialize roadmap: {e}", style="bold red")
        manifest.rollback()
        workflow.rollback_on_error()
    finally:
        lock.release()


def _show_detected_context(detected_info: dict, interactive: bool) -> None:
    """Display detected project context."""
    console.print("🔍 Detected Context:", style="bold blue")
    if detected_info.get("git_repo"):
        console.print(f"  Git repository: {detected_info['git_repo']}")
    else:
        console.print("  Git repository: Not detected", style="dim")
        if interactive:
            console.print(
                "    💡 Consider running 'git init' to enable advanced features",
                style="yellow",
            )
    if detected_info.get("project_name"):
        console.print(f"  Project name: {detected_info['project_name']}")
    console.print(f"  Directory: {Path.cwd()}")
    console.print()


def _create_main_project(
    custom_core: RoadmapCore,
    manifest: "InitializationManifest",
    project_name: str | None,
    description: str | None,
    detected_info: dict,
    interactive: bool,
    template: str,
    yes: bool,
    template_path: str | None,
) -> dict | None:
    """Create the main project with status output."""
    with console.status("📋 Creating main project...", spinner="dots"):
        project_info = _setup_main_project(
            custom_core,
            project_name,
            description,
            detected_info,
            interactive,
            template,
            yes,
            template_path,
        )

    # Add project file to manifest
    if project_info and "filename" in project_info:
        project_file = custom_core.roadmap_dir / "projects" / project_info["filename"]
        manifest.add_path(project_file)

    return project_info


def _configure_github(
    custom_core: RoadmapCore,
    skip_github: bool,
    github_repo: str | None,
    detected_info: dict,
    interactive: bool,
    yes: bool,
    github_token: str | None,
) -> bool:
    """Configure GitHub integration if not skipped."""
    if skip_github:
        return False

    repo_name = github_repo or detected_info.get("git_repo")
    if not repo_name:
        return False

    with console.status("🔗 Configuring GitHub integration...", spinner="dots"):
        return _setup_github_integration(
            custom_core,
            repo_name,
            interactive,
            yes,
            token=github_token,
        )


@click.command()
@click.pass_context
def status(ctx: click.Context) -> None:
    """Show the current status of the roadmap."""
    log = logger.bind(operation="status")
    log.info("starting_status")

    core = ctx.obj["core"]

    if not core.is_initialized():
        log.warning("roadmap_not_initialized")
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return

    try:
        console.print("📊 Roadmap Status", style="bold blue")

        # Get all issues and milestones from files (more reliable than database)
        issues = core.list_issues()
        milestones = core.list_milestones()

        log.info(
            "status_data_retrieved",
            issue_count=len(issues),
            milestone_count=len(milestones),
        )

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
                progress = core.db.get_milestone_progress(ms.name)
                console.print(f"\n  {ms.name}")

                if progress["total"] > 0:
                    with Progress(
                        TextColumn("[progress.description]{task.description}"),
                        BarColumn(),
                        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                        console=console,
                        transient=True,
                    ) as progress_bar:
                        progress_bar.add_task(
                            f"    Progress ({progress['completed']}/{progress['total']})",
                            total=progress["total"],
                            completed=progress["completed"],
                        )
                else:
                    console.print("    No issues assigned", style="dim")

        # Show issues by status
        console.print("\n📋 Issues by Status:", style="bold cyan")

        # Count issues by status from the issues list
        from collections import Counter

        status_counts = Counter(issue.status for issue in issues)

        if status_counts:
            status_table = Table(show_header=False, box=None)
            status_table.add_column("Status", style="white", width=15)
            status_table.add_column("Count", style="cyan", width=10)

            for status in Status:
                count = status_counts.get(status, 0)
                if count > 0:  # Only show statuses that have issues
                    status_style = {
                        Status.TODO: "white",
                        Status.IN_PROGRESS: "yellow",
                        Status.BLOCKED: "red",
                        Status.REVIEW: "blue",
                        Status.CLOSED: "green",
                    }.get(status, "white")

                    status_table.add_row(
                        Text(f"  {status.value}", style=status_style), str(count)
                    )

            console.print(status_table)
        else:
            console.print("  No issues found", style="dim")

    except Exception as e:
        console.print(f"❌ Failed to show status: {e}", style="bold red")


@click.command()
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Show detailed debug information and all health check logs",
)
@verbose_output
@click.pass_context
def health(ctx: click.Context, verbose: bool) -> None:
    """Check system health and component status.

    By default, shows a summary of health checks with status indicators
    and suppresses debug logging output for a clean display.

    Use --verbose to see all debug logs and detailed check information.
    """
    log = logger.bind(operation="health")
    log.info("starting_health_check", verbose=verbose)

    console.print("🏥 System Health Check", style="bold blue")

    # Get core from context
    core = ctx.obj["core"]

    # Run all health checks
    checks = HealthCheck.run_all_checks(core)
    overall_status = HealthCheck.get_overall_status(checks)

    # Display results
    console.print()
    for check_name, (status, message) in checks.items():
        # Format check name
        display_name = check_name.replace("_", " ").title()

        # Choose emoji and style based on status
        if status == HealthStatus.HEALTHY:
            emoji = "✅"
            style = "green"
        elif status == HealthStatus.DEGRADED:
            emoji = "⚠️"
            style = "yellow"
        else:  # UNHEALTHY
            emoji = "❌"
            style = "red"

        console.print(f"{emoji} {display_name}: {message}", style=style)

    # Display overall status
    console.print()
    if overall_status == HealthStatus.HEALTHY:
        console.print("✨ Overall Status: HEALTHY", style="bold green")
        log.info("health_check_completed", status="healthy")
    elif overall_status == HealthStatus.DEGRADED:
        console.print("⚠️  Overall Status: DEGRADED", style="bold yellow")
        console.print(
            "   Some components have issues but system is functional", style="dim"
        )
        log.warning("health_check_completed", status="degraded")
    else:  # UNHEALTHY
        console.print("❌ Overall Status: UNHEALTHY", style="bold red")
        console.print(
            "   Critical issues detected - system may not function properly",
            style="dim",
        )
        log.error("health_check_completed", status="unhealthy")


# Helper functions for init command


def _detect_project_context() -> dict:
    """Detect project context from git repository and directory structure."""
    context = {
        "git_repo": None,
        "project_name": None,
        "git_user": None,
        "has_git": False,
    }

    try:
        # Check if we're in a git repository
        git_check = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        context["has_git"] = git_check.returncode == 0

        if context["has_git"]:
            # Try to get git repository info
            result = subprocess.run(
                ["git", "remote", "get-url", "origin"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                origin_url = result.stdout.strip()
                # Parse GitHub repository from URL
                if "github.com" in origin_url:
                    # Handle both SSH and HTTPS URLs
                    if origin_url.startswith("git@github.com:"):
                        repo_part = origin_url.replace("git@github.com:", "").replace(
                            ".git", ""
                        )
                    elif "github.com/" in origin_url:
                        repo_part = origin_url.split("github.com/")[1].replace(
                            ".git", ""
                        )
                    else:
                        repo_part = None

                    if repo_part and "/" in repo_part:
                        context["git_repo"] = repo_part
                        context["project_name"] = repo_part.split("/")[1]

            # Get git user info
            try:
                user_result = subprocess.run(
                    ["git", "config", "user.name"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if user_result.returncode == 0:
                    context["git_user"] = user_result.stdout.strip()
            except Exception:
                pass

    except (
        subprocess.TimeoutExpired,
        subprocess.CalledProcessError,
        FileNotFoundError,
    ):
        pass

    # Fallback to directory name if no git repo detected
    if not context["project_name"]:
        context["project_name"] = Path.cwd().name

    # Try to detect from package files
    if not context["project_name"] or context["project_name"] == ".":
        for config_file in ["pyproject.toml", "package.json", "Cargo.toml"]:
            if Path(config_file).exists():
                try:
                    content = Path(config_file).read_text()
                    if config_file == "pyproject.toml":
                        import re

                        match = re.search(r'name\s*=\s*["\']([^"\']+)["\']', content)
                        if match:
                            context["project_name"] = match.group(1)
                            break
                    elif config_file == "package.json":
                        import json

                        data = json.loads(content)
                        if "name" in data:
                            context["project_name"] = data["name"]
                            break
                except Exception:
                    pass

    return context


def _setup_main_project(
    core: RoadmapCore,
    project_name: str | None,
    description: str | None,
    detected_info: dict,
    interactive: bool,
    template: str,
    yes: bool = False,
    template_path: str | None = None,
) -> dict:
    """Set up the main project document."""

    # Determine project name
    if not project_name:
        if interactive and not yes:
            suggested_name = detected_info.get("project_name", Path.cwd().name)
            project_name = click.prompt(
                "Project name", default=suggested_name, show_default=True
            )
        else:
            project_name = detected_info.get("project_name", Path.cwd().name)

    # Ensure project_name is never None
    assert project_name is not None

    # Determine description
    if not description and interactive and not yes:
        default_desc = "A project managed with Roadmap CLI"
        if detected_info.get("git_repo"):
            default_desc = f"Project repository: {detected_info['git_repo']}"
        description = click.prompt(
            "Project description", default=default_desc, show_default=True
        )
    elif not description:
        description = "A project managed with Roadmap CLI"

    # Ensure description is never None
    assert description is not None

    # Create project using core functionality
    console.print("📋 Creating main project...", style="bold blue")

    # Generate project content based on template
    # If a custom template path was provided and is valid, use its contents
    if template_path:
        try:
            tpl_path = Path(template_path)
            if tpl_path.exists() and tpl_path.is_file():
                project_content = tpl_path.read_text()
            else:
                console.print(
                    f"⚠️  Custom template not found at {template_path}; falling back to builtin template",
                    style="yellow",
                )
                project_content = _generate_project_template(
                    project_name, description, template, detected_info
                )
        except Exception as e:
            console.print(
                f"⚠️  Could not read custom template: {e}; using builtin template",
                style="yellow",
            )
            project_content = _generate_project_template(
                project_name, description, template, detected_info
            )
    else:
        project_content = _generate_project_template(
            project_name, description, template, detected_info
        )

    # Save project file
    project_id = core._generate_id()[:8]
    project_filename = f"{project_id}-{core._normalize_filename(project_name)}.md"
    project_file = core.roadmap_dir / "projects" / project_filename

    # Ensure projects directory exists
    (core.roadmap_dir / "projects").mkdir(exist_ok=True)

    project_file.write_text(project_content)

    return {"id": project_id, "name": project_name, "filename": project_filename}


def _generate_project_template(
    project_name: str, description: str, template: str, detected_info: dict
) -> str:
    """Generate project content based on template."""

    current_date = datetime.now().isoformat()
    owner = detected_info.get("git_user", getpass.getuser())

    # Base project content
    content = f"""---
name: {project_name}
description: {description}
owner: {owner}
priority: high
status: active
created: {current_date}
updated: {current_date}
"""

    if detected_info.get("git_repo"):
        content += f"github_repo: {detected_info['git_repo']}\n"

    content += (
        """timeline:
  start_date: """
        + current_date
        + """
  target_end_date: null
tags: []
---

# """
        + project_name
        + """

## Overview

"""
        + description
        + """

## Project Goals

"""
    )

    # Template-specific content
    if template == "software":
        content += """
- [ ] Develop core functionality
- [ ] Implement user interface
- [ ] Write comprehensive tests
- [ ] Deploy to production
- [ ] Document API and usage

## Technical Stack

- **Language**: Python
- **Framework**: TBD
- **Database**: TBD
- **Deployment**: TBD

## Development Phases

### Phase 1: Foundation
- Project setup and architecture
- Core functionality implementation
- Basic testing framework

### Phase 2: Features
- Feature development
- User interface implementation
- Integration testing

### Phase 3: Polish
- Performance optimization
- Documentation
- Production deployment
"""

    elif template == "research":
        content += """
- [ ] Literature review
- [ ] Hypothesis formation
- [ ] Methodology design
- [ ] Data collection
- [ ] Analysis and findings
- [ ] Publication preparation

## Research Questions

1. [Primary research question]
2. [Secondary research questions]

## Methodology

[Research methodology and approach]

## Timeline

- **Phase 1**: Literature review (4 weeks)
- **Phase 2**: Data collection (8 weeks)
- **Phase 3**: Analysis (4 weeks)
- **Phase 4**: Writing (4 weeks)
"""

    elif template == "team":
        content += """
- [ ] Team onboarding
- [ ] Process documentation
- [ ] Workflow optimization
- [ ] Knowledge sharing
- [ ] Regular retrospectives

## Team Structure

- **Project Lead**: [Name]
- **Development Team**: [Names]
- **Stakeholders**: [Names]

## Communication

- **Daily Standups**: [Time/Location]
- **Sprint Planning**: [Schedule]
- **Retrospectives**: [Schedule]

## Processes

### Development Workflow
1. Issue creation and planning
2. Feature branch development
3. Code review process
4. Testing and validation
5. Deployment and monitoring
"""

    else:  # basic template
        content += """
- [ ] Define project scope
- [ ] Create initial roadmap
- [ ] Begin implementation
- [ ] Regular progress reviews
- [ ] Project completion

## Milestones

### Milestone 1: Setup
- Initial project structure
- Team alignment on goals

### Milestone 2: Development
- Core functionality implementation
- Regular progress tracking

### Milestone 3: Completion
- Final deliverables
- Project retrospective
"""

    content += """

## Resources

- [Link to documentation]
- [Link to repository]
- [Link to project tools]

## Notes

[Additional project notes and context]
"""

    return content


def _setup_github_integration(
    core: RoadmapCore,
    github_repo: str,
    interactive: bool,
    yes: bool = False,
    token: str | None = None,
) -> bool:
    """Set up GitHub integration with credential flow."""
    try:
        # Import GitHub modules
        if CredentialManager is None or GitHubClient is None:
            raise ImportError("GitHub integration dependencies not available")

        # Show setup instructions and get confirmation
        if interactive and not yes:
            if not show_github_setup_instructions(github_repo, yes):
                return False

        # Initialize managers
        cred_manager = CredentialManager()
        token_resolver = GitHubTokenResolver(cred_manager)

        # Get existing token
        existing_token = token_resolver.get_existing_token()

        # Resolve which token to use
        use_token, should_continue = token_resolver.resolve_token(
            token, interactive, yes, existing_token
        )
        if not should_continue or not use_token:
            return False

        # Test the connection
        console.print("🔍 Testing GitHub connection...", style="yellow")
        github_client = GitHubClient(use_token)
        validator = GitHubSetupValidator(github_client)

        # Validate authentication
        auth_success, username = validator.validate_authentication()
        if not auth_success:
            if interactive and click.confirm(
                "Continue without GitHub integration? (recommended to skip until token is fixed)"
            ):
                return False
            raise RuntimeError(f"Authentication failed: {username}")

        # Validate repository access
        repo_success, repo_info = validator.validate_repository_access(github_repo)
        if not repo_success:
            if interactive and not yes:
                if not click.confirm("Continue with GitHub integration anyway?"):
                    return False

        # Store credentials if new/different
        if use_token != existing_token:
            cred_manager.store_token(use_token)
            console.print("🔒 Credentials stored securely")

        # Save configuration
        config_manager = GitHubConfigManager(core)
        config_manager.save_github_config(github_repo)

        # Test API access
        validator.test_api_access(github_repo)

        return True

    except ImportError as e:
        console.print(
            f"⚠️  GitHub integration not available: Missing dependencies ({e})",
            style="yellow",
        )
        console.print("Install with: pip install requests keyring", style="dim")
        return False
    except Exception as e:
        console.print(f"❌ GitHub setup failed: {e}", style="red")
        if interactive and click.confirm("Continue without GitHub integration?"):
            return False
        raise


def _show_success_summary(
    name: str, github_configured: bool, project_info: dict | None, detected_info: dict
) -> None:
    """Show success summary and next steps."""

    console.print()
    console.print("✅ Setup Complete!", style="bold green")
    console.print()

    # Show what was created
    console.print("📁 Created:", style="bold cyan")
    console.print(f"  ✓ Roadmap structure: {name}/")
    console.print("    ├── issues/       (issue tracking)")
    console.print("    ├── milestones/   (milestone management)")
    console.print("    ├── projects/     (project documents)")
    console.print("    ├── templates/    (document templates)")
    console.print("    ├── artifacts/    (generated content)")
    console.print("    └── config.yaml   (configuration)")

    if project_info:
        console.print(
            f"  ✓ Main project: {project_info['name']} (ID: {project_info['id']})"
        )
    if github_configured:
        console.print("  ✓ GitHub integration: Connected and configured")
        console.print("    • Bidirectional sync enabled")
        console.print("    • Automatic issue linking")
        console.print("    • Webhook support ready")
    console.print("  ✓ Security: Secure file permissions and credential storage")

    console.print()
    console.print("🚀 Next Steps:", style="bold yellow")

    if project_info:
        console.print(f"  → roadmap project show {project_info['id'][:8]}")
    console.print('  → roadmap issue create "Your first issue"')
    if github_configured:
        console.print("  → roadmap sync bidirectional        # Sync with GitHub")
        console.print("  → roadmap git setup                 # Configure git hooks")
    console.print("  → roadmap user show-dashboard        # View your dashboard")

    console.print()
    console.print("📚 Learn More:", style="bold cyan")
    console.print("  → roadmap --help                    # All available commands")
    console.print("  → roadmap issue --help               # Issue management")
    if github_configured:
        console.print("  → roadmap sync --help                # GitHub synchronization")
        console.print("  → roadmap git --help                 # Git integration")
    console.print("  → roadmap project --help             # Project management")
    console.print("  → roadmap milestone --help           # Milestone tracking")

    console.print()
    console.print("💡 Pro Tips:", style="bold magenta")
    console.print("  • Use 'roadmap user show-dashboard' for daily task overview")

    if detected_info.get("has_git"):
        console.print(
            "  • Set up git hooks with 'roadmap git setup' for automatic updates"
        )
        if github_configured:
            console.print(
                "  • Try 'roadmap sync bidirectional' to sync existing GitHub issues"
            )
    else:
        console.print("  • Initialize git with 'git init' to enable advanced features:")
        console.print("    - Automatic issue updates from commit messages")
        console.print("    - Git hooks for seamless integration")
        console.print("    - GitHub synchronization capabilities")

    console.print(
        "  • Create templates in .roadmap/templates/ for consistent formatting"
    )


def _post_init_validate(
    core: RoadmapCore, name: str, project_info: dict | None
) -> bool:
    """Validate the init result: config exists, project file created, and permissions look sane.

    Returns True if validation passes, False if there are warnings or errors.
    """
    ok = True
    roadmap_dir = core.roadmap_dir

    # Check config file
    config_file = roadmap_dir / "config.yaml"
    if not config_file.exists():
        console.print(f"⚠️  Missing configuration file: {config_file}", style="yellow")
        ok = False

    # Check projects directory and at least one project file
    projects_dir = roadmap_dir / "projects"
    try:
        has_projects = projects_dir.exists() and any(projects_dir.iterdir())
    except Exception:
        has_projects = False

    if not has_projects:
        console.print(f"⚠️  No project files found in {projects_dir}", style="yellow")
        ok = False

    # Basic permission checks: readable and writable
    try:
        if not os.access(roadmap_dir, os.R_OK | os.W_OK | os.X_OK):
            console.print(
                f"⚠️  Permission issue: cannot read/write/execute {roadmap_dir}",
                style="yellow",
            )
            ok = False
    except Exception:
        # Non-fatal
        pass

    # If a project_info was returned, ensure file exists
    if project_info and "filename" in project_info:
        proj_file = roadmap_dir / "projects" / project_info["filename"]
        if not proj_file.exists():
            console.print(
                f"⚠️  Expected project file missing: {proj_file}", style="yellow"
            )
            ok = False

    return ok
