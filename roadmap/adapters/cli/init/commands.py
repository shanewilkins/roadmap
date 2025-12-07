"""Initialize a new roadmap directory structure."""

from pathlib import Path

import click
from structlog import get_logger

from roadmap.adapters.cli.github_setup import GitHubInitializationService
from roadmap.adapters.cli.init_utils import InitializationLock, InitializationManifest
from roadmap.adapters.cli.init_validator import InitializationValidator
from roadmap.adapters.cli.init_workflow import InitializationWorkflow
from roadmap.adapters.cli.presentation.core_initialization_presenter import (
    CoreInitializationPresenter,
)
from roadmap.adapters.cli.services.project_initialization_service import (
    ProjectContextDetectionService,
    ProjectCreationService,
    ProjectDetectionService,
)
from roadmap.infrastructure.core import RoadmapCore

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
    log = logger.bind(
        operation="init",
        roadmap_name=name,
        skip_github=skip_github,
        interactive=interactive,
        dry_run=dry_run,
        force=force,
    )
    log.info("starting_init")

    custom_core = RoadmapCore(roadmap_dir_name=name)

    # Handle dry-run mode
    if dry_run:
        roadmap_dir = Path.cwd() / name
        config_file = roadmap_dir / "config.yaml"
        is_initialized = roadmap_dir.exists() and config_file.exists()
        log.info("dry_run_mode", is_initialized=is_initialized)
        show_dry_run_info(name, is_initialized, force, skip_project, skip_github)
        return

    # Validate prerequisites
    lock_path = Path.cwd() / ".roadmap_init.lock"
    is_valid, error_msg = InitializationValidator.validate_lockfile(lock_path)
    if not is_valid:
        presenter.present_error(error_msg or "Unknown error")
        presenter.present_initialization_tip()
        return

    is_valid, error_msg = InitializationValidator.check_existing_roadmap(
        custom_core, force
    )
    if not is_valid:
        presenter.present_error(error_msg or "Unknown error")
        presenter.present_initialization_tip()
        return

    # Acquire lock
    lock = InitializationLock(lock_path)
    if not lock.acquire():
        presenter.present_already_in_progress_error()
        return

    manifest = InitializationManifest(custom_core.roadmap_dir / ".init_manifest.json")
    workflow = InitializationWorkflow(custom_core)

    presenter.present_initialization_header()

    try:
        # Handle force re-initialization
        if custom_core.is_initialized() and force:
            presenter.present_force_reinitialize_warning(name)
            if not workflow.cleanup_existing():
                return
        elif custom_core.is_initialized():
            presenter.present_already_initialized_info(name)

        # Detect context
        detected_info = ProjectContextDetectionService.detect_project_context()

        # Create structure
        presenter.present_creating_structure(name)
        if not workflow.create_structure_preserve_data():
            return
        workflow.generate_config_file()
        workflow.record_created_paths(manifest)
        workflow.ensure_gitignore_entry()

        ctx.obj["core"] = custom_core

        # Detect or create project
        project_info = None
        if not skip_project:
            existing_projects = ProjectDetectionService.detect_existing_projects(
                custom_core.projects_dir
            )

            if existing_projects:
                project_info = {
                    "name": existing_projects[0]["name"],
                    "id": existing_projects[0]["id"],
                    "action": "joined",
                }
                if len(existing_projects) > 1 and interactive:
                    presenter.present_existing_projects_found(len(existing_projects))
            else:
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

        # Configure GitHub
        github_service = GitHubInitializationService(custom_core)
        github_service.setup(
            skip_github,
            github_repo,
            detected_info,
            interactive,
            yes,
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
        manifest.rollback()
        workflow.rollback_on_error()
    finally:
        lock.release()
