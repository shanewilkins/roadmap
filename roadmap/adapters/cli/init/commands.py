"""Initialize a new roadmap directory structure."""

from pathlib import Path

import click
from structlog import get_logger

from roadmap.adapters.cli.presentation.core_initialization_presenter import (
    CoreInitializationPresenter,
)
from roadmap.adapters.cli.services.project_initialization_service import (
    ProjectContextDetectionService,
    ProjectCreationService,
    ProjectDetectionService,
)
from roadmap.core.services.initialization import (
    InitializationLock,
    InitializationManifest,
    InitializationValidator,
    InitializationWorkflow,
)
from roadmap.infrastructure.core import RoadmapCore
from roadmap.infrastructure.github import GitHubInitializationService

logger = get_logger()
presenter = CoreInitializationPresenter()


def show_dry_run_info(
    name: str, is_initialized: bool, force: bool, skip_project: bool, skip_github: bool
) -> None:
    """Display dry-run information without making changes."""
    click.secho("🚀 Roadmap CLI Initialization", fg="cyan", bold=True)
    click.echo()
    click.secho("ℹ️  Dry run mode enabled - no changes will be made.", fg="yellow")

    if is_initialized and force:
        click.secho(f"🟡 Would remove existing {name}/ and reinitialize", fg="yellow")
    elif is_initialized:
        click.secho(
            f"❌ Roadmap already initialized in {name}/ directory", fg="red", bold=True
        )
        click.secho("Tip: use --force to reinitialize", fg="yellow")
    else:
        actions = [
            f"Create roadmap directory: {name}/",
            "Create default templates and config",
        ]
        if not skip_project:
            actions.append("Create main project")
        if not skip_github:
            actions.append("Optionally configure GitHub")

        click.echo("Planned actions:")
        for action in actions:
            click.echo(f" - {action}")


def _validate_initialization(custom_core, lock_path, force):
    """Validate initialization prerequisites."""
    is_valid, error_msg = InitializationValidator.validate_lockfile(lock_path)
    if not is_valid:
        presenter.present_error(error_msg or "Unknown error")
        presenter.present_initialization_tip()
        return False

    is_valid, error_msg = InitializationValidator.check_existing_roadmap(
        custom_core, force
    )
    if not is_valid:
        presenter.present_error(error_msg or "Unknown error")
        presenter.present_initialization_tip()
        return False

    return True


def _setup_project(
    custom_core,
    skip_project,
    detected_info,
    project_name,
    description,
    template,
    template_path,
    interactive,
):
    """Setup project if not skipped."""
    if skip_project:
        return None

    existing_projects = ProjectDetectionService.detect_existing_projects(
        custom_core.projects_dir
    )

    if existing_projects:
        if len(existing_projects) > 1 and interactive:
            presenter.present_existing_projects_found(len(existing_projects))
        return {
            "name": existing_projects[0]["name"],
            "id": existing_projects[0]["id"],
            "action": "joined",
        }

    project_info = ProjectCreationService.create_project(
        custom_core,
        project_name or detected_info.get("project_name", Path.cwd().name),
        description or "A project managed with Roadmap CLI",
        detected_info,
        template or "basic",
        template_path,
    )
    if project_info:
        project_info["action"] = "created"

    return project_info


def _create_roadmap_structure(workflow, manifest, name):
    """Create roadmap directory structure."""
    presenter.present_creating_structure(name)
    if not workflow.create_structure_preserve_data():
        return False
    workflow.generate_config_file()
    workflow.record_created_paths(manifest)
    workflow.ensure_gitignore_entry()
    return True


def _handle_force_reinitialization(custom_core, workflow, name):
    """Handle force re-initialization of existing roadmap."""
    if custom_core.is_initialized():
        presenter.present_force_reinitialize_warning(name)
        if not workflow.cleanup_existing():
            return False
    return True


def _handle_init_dry_run(
    name: str, force: bool, skip_project: bool, skip_github: bool, log
) -> bool:
    """Handle dry-run mode for init.

    Args:
        name: Roadmap name
        force: Force flag
        skip_project: Skip project setup
        skip_github: Skip GitHub setup
        log: Logger instance

    Returns:
        True if should continue (not dry-run), False if dry-run was handled
    """
    roadmap_dir = Path.cwd() / name
    config_file = roadmap_dir / "config.yaml"
    is_initialized = roadmap_dir.exists() and config_file.exists()
    log.info("dry_run_mode", is_initialized=is_initialized)
    show_dry_run_info(name, is_initialized, force, skip_project, skip_github)
    return False


def _setup_init_environment(custom_core, name: str, force: bool, log):
    """Setup lock and manifest for initialization.

    Args:
        custom_core: RoadmapCore instance
        name: Roadmap name
        force: Force flag
        log: Logger instance

    Returns:
        Tuple of (lock, manifest, workflow) or (None, None, None) on error
    """
    lock_path = Path.cwd() / ".roadmap_init.lock"
    if not _validate_initialization(custom_core, lock_path, force):
        return None, None, None

    lock = InitializationLock(lock_path)
    if not lock.acquire():
        presenter.present_already_in_progress_error()
        return None, None, None

    manifest = InitializationManifest(custom_core.roadmap_dir / ".init_manifest.json")
    workflow = InitializationWorkflow(custom_core)

    return lock, manifest, workflow


def _handle_already_initialized(
    custom_core, force: bool, workflow, name: str
) -> tuple[bool, bool]:
    """Handle case where roadmap is already initialized.

    Args:
        custom_core: RoadmapCore instance
        force: Force re-initialization flag
        workflow: InitializationWorkflow instance
        name: Roadmap name

    Returns:
        Tuple of (should_continue, should_create_structure)
        - should_continue: Whether to proceed with initialization
        - should_create_structure: Whether to call _create_roadmap_structure
    """
    if force:
        success = _handle_force_reinitialization(custom_core, workflow, name)
        # If force succeeded, we need to create structure (roadmap was cleaned)
        return success, success
    elif custom_core.is_initialized():
        # Show info message but continue - allow team members to join existing projects
        # Do NOT create structure since roadmap already exists
        presenter.present_already_initialized_info(name)
        return True, False
    # Roadmap doesn't exist, so we need to create structure
    return True, True


@click.command()
@click.option(
    "--name",
    "-n",
    default=".roadmap",
    help="Name of the roadmap directory (default: .roadmap)",
)
@click.option(
    "--project-name",
    "-p",
    default=None,
    help="Name for the initial project",
)
@click.option(
    "--description",
    "-d",
    default=None,
    help="Description for the initial project",
)
@click.option(
    "--skip-project",
    is_flag=True,
    help="Skip project creation",
)
@click.option(
    "--skip-github",
    is_flag=True,
    help="Skip GitHub integration setup",
)
@click.option(
    "--github-repo",
    default=None,
    help="GitHub repository (owner/repo)",
)
@click.option(
    "--github-token",
    default=None,
    help="GitHub personal access token",
)
@click.option(
    "--interactive/--non-interactive",
    default=True,
    help="Run in interactive mode with prompts (default: interactive)",
)
@click.option(
    "--yes",
    "-y",
    is_flag=True,
    help="Answer yes to all prompts",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be initialized without making changes",
)
@click.option(
    "--force",
    "-f",
    is_flag=True,
    help="Force reinitialize existing roadmap",
)
@click.option(
    "--template",
    "-t",
    default=None,
    help="Template to use for project initialization",
)
@click.option(
    "--template-path",
    default=None,
    help="Path to custom template file",
)
@click.pass_context
def init(
    ctx: click.Context,
    name: str,
    project_name: str | None,
    description: str | None,
    skip_project: bool,
    skip_github: bool,
    github_repo: str | None,
    github_token: str | None,
    interactive: bool,
    yes: bool,
    dry_run: bool,
    force: bool,
    template: str | None,
    template_path: str | None,
) -> None:
    """Initialize a new roadmap structure."""
    from roadmap.common.cli_models import InitParams

    # Create structured parameter object
    params = InitParams(
        name=name,
        project_name=project_name,
        description=description,
        skip_project=skip_project,
        skip_github=skip_github,
        github_repo=github_repo,
        github_token=github_token,
        interactive=interactive,
        yes=yes,
        dry_run=dry_run,
        force=force,
        template=template,
        template_path=template_path,
    )

    log = logger.bind(
        operation="init",
        roadmap_name=params.name,
        skip_github=params.skip_github,
        interactive=params.interactive,
        dry_run=params.dry_run,
        force=params.force,
    )
    log.info("starting_init")

    custom_core = RoadmapCore(roadmap_dir_name=params.name)

    # Handle dry-run mode
    if params.dry_run:
        _handle_init_dry_run(
            params.name, params.force, params.skip_project, params.skip_github, log
        )
        return

    # Setup environment
    lock, manifest, workflow = _setup_init_environment(
        custom_core, params.name, params.force, log
    )
    if not lock:
        return

    presenter.present_initialization_header()

    try:
        # Handle already initialized or force re-init
        should_continue, should_create_structure = _handle_already_initialized(
            custom_core, params.force, workflow, params.name
        )
        if not should_continue:
            return

        # Detect context (needed for project setup regardless)
        detected_info = ProjectContextDetectionService.detect_project_context()

        # Create structure only if needed (not already initialized or was force-cleaned)
        if should_create_structure:
            if not _create_roadmap_structure(workflow, manifest, params.name):
                return

        # Initialize ctx.obj if not already done (can happen in tests)
        if ctx.obj is None:
            ctx.obj = {}

        ctx.obj["core"] = custom_core

        # Setup project
        project_info = _setup_project(
            custom_core,
            params.skip_project,
            detected_info,
            params.project_name,
            params.description,
            params.template,
            params.template_path,
            params.interactive,
        )

        # Save default project ID if created
        if project_info and project_info.get("action") == "created":
            from roadmap.common.config_manager import ConfigManager

            config_manager = ConfigManager(custom_core.config_file)
            config = config_manager.load()
            config.behavior.default_project_id = project_info.get("id")
            config_manager.save(config)
            log.info("default_project_set", project_id=project_info.get("id"))

        # Show project summary
        if project_info:
            if project_info.get("action") == "created":
                presenter.present_project_created(
                    project_info.get("name", "Main Project")
                )
            elif project_info.get("action") == "joined":
                count = project_info.get("count", 1)
                if count > 1:
                    presenter.present_projects_joined(
                        project_info.get("name", ""), count
                    )
                else:
                    presenter.present_project_joined(project_info.get("name", ""))

        # Configure GitHub
        github_service = GitHubInitializationService(custom_core)
        github_service.setup(
            params.skip_github,
            params.github_repo,
            detected_info,
            params.interactive,
            params.yes,
            github_token,
            presenter,
        )

        # Validate and show summary
        validation_ok = InitializationValidator.post_init_validate(
            custom_core, name, project_info
        )
        if not validation_ok:
            presenter.present_initialization_warning("Some validation checks failed")

    except Exception as e:
        log.error("init_failed", error=str(e))
        presenter.present_initialization_failed(str(e))
        if manifest:
            manifest.rollback()
        if workflow:
            workflow.rollback_on_error()
    finally:
        lock.release()
