"""
Core CLI commands: init and status.
These are the fundamental commands needed to get started with Roadmap.
"""

from pathlib import Path

import click

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
from roadmap.presentation.cli.logging_decorators import verbose_output
from roadmap.presentation.cli.presentation.project_initialization_presenter import (
    ProjectInitializationPresenter,
)
from roadmap.presentation.cli.services.project_initialization_service import (
    ProjectContextDetectionService,
    ProjectCreationService,
    ProjectDetectionService,
)
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
@click.option("--verbose", "-v", is_flag=True, help="Show verbose output")
@click.pass_context
@verbose_output
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
    verbose: bool,
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
        roadmap_name=name,
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
        elif custom_core.is_initialized():
            console.print(
                f"ℹ️  Roadmap already initialized in {name}/",
                style="cyan",
            )
            console.print(
                "    Updating configuration while preserving existing data.",
                style="dim",
            )
            console.print()

        # Step 1: Detect context
        detected_info = ProjectContextDetectionService.detect_project_context()
        ProjectInitializationPresenter.show_detected_context(detected_info, interactive)

        # Step 2: Create roadmap structure (preserving existing data)
        with console.status(
            f"🗂️  Creating roadmap structure in {name}/...", spinner="dots"
        ):
            # Use preserve-data version to avoid destroying existing issues/milestones
            if not workflow.create_structure_preserve_data():
                return
            workflow.generate_config_file()
            workflow.record_created_paths(manifest)
            workflow.ensure_gitignore_entry()

        ctx.obj["core"] = custom_core

        # Step 3: Detect or create main project (unless skipped)
        project_info = None
        if not skip_project:
            # Check for existing projects
            existing_projects = ProjectDetectionService.detect_existing_projects(
                custom_core.projects_dir
            )

            if existing_projects:
                # Join existing project(s)
                ProjectInitializationPresenter.show_existing_projects(existing_projects)

                # Use the first project as the primary project info
                if existing_projects:
                    project_info = {
                        "name": existing_projects[0]["name"],
                        "id": existing_projects[0]["id"],
                        "action": "joined",
                    }

                    if len(existing_projects) > 1 and interactive:
                        console.print(
                            f"\n  💡 {len(existing_projects)} projects found. All will be available.",
                            style="dim",
                        )
            else:
                # Create new project
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
                    project_info["action"] = "created"
                    ProjectInitializationPresenter.show_project_created(project_info)

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

        ProjectInitializationPresenter.show_success_summary(
            name, github_configured, project_info, detected_info
        )

    except Exception as e:
        log.error("init_failed", error=str(e))
        console.print(f"❌ Failed to initialize roadmap: {e}", style="bold red")
        manifest.rollback()
        workflow.rollback_on_error()
    finally:
        lock.release()


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
    """Create the main project with user prompts and status output."""
    # Determine project name
    if not project_name:
        suggested_name = detected_info.get("project_name", Path.cwd().name)
        project_name = ProjectInitializationPresenter.prompt_project_name(
            suggested_name, interactive, yes
        )

    if not project_name:
        project_name = detected_info.get("project_name", Path.cwd().name)

    # Ensure project_name is never None
    assert project_name is not None
    final_project_name: str = project_name

    # Determine description
    if not description:
        default_desc = "A project managed with Roadmap CLI"
        if detected_info.get("git_repo"):
            default_desc = f"Project repository: {detected_info['git_repo']}"
        description = ProjectInitializationPresenter.prompt_project_description(
            default_desc, interactive, yes
        )

    if not description:
        description = "A project managed with Roadmap CLI"

    # Ensure description is never None
    assert description is not None
    final_description: str = description

    # Create the project
    with console.status("📋 Creating main project...", spinner="dots"):
        project_info = ProjectCreationService.create_project(
            custom_core,
            final_project_name,
            final_description,
            detected_info,
            template,
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
@click.option("--verbose", "-v", is_flag=True, help="Show verbose output")
@click.pass_context
@verbose_output
def status(ctx: click.Context, verbose: bool) -> None:
    """Show the current status of the roadmap."""
    from roadmap.presentation.cli.presentation.project_status_presenter import (
        IssueStatusPresenter,
        MilestoneProgressPresenter,
        RoadmapStatusPresenter,
    )
    from roadmap.presentation.cli.services.project_status_service import (
        IssueStatisticsService,
        MilestoneProgressService,
        StatusDataService,
    )

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
        RoadmapStatusPresenter.show_status_header()

        # Gather status data
        status_data = StatusDataService.gather_status_data(core)
        log.info(
            "status_data_retrieved",
            issue_count=status_data["issue_count"],
            milestone_count=status_data["milestone_count"],
        )

        if not status_data["has_data"]:
            RoadmapStatusPresenter.show_empty_state()
            return

        # Compute milestone progress
        milestone_progress = MilestoneProgressService.get_all_milestones_progress(
            core, status_data["milestones"]
        )
        status_data["milestone_progress"] = milestone_progress

        # Compute issue statistics
        issue_counts = IssueStatisticsService.get_all_status_counts(
            status_data["issues"]
        )
        status_data["issue_counts"] = issue_counts

        # Show milestone progress
        if status_data["milestones"]:
            MilestoneProgressPresenter.show_all_milestones(
                status_data["milestones"],
                status_data["milestone_progress"],
            )

        # Show issues by status
        IssueStatusPresenter.show_all_issue_statuses(status_data["issue_counts"])

    except Exception as e:
        log.exception("status_error", error=str(e))
        RoadmapStatusPresenter.show_error(str(e))


@click.command()
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Show detailed debug information and all health check logs",
)
@click.pass_context
@verbose_output
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
    """Deprecated: Use ProjectContextDetectionService instead."""
    return ProjectContextDetectionService.detect_project_context()


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
        repo_success, _ = validator.validate_repository_access(github_repo)
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
