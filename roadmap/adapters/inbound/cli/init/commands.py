"""Initialize a canonical local Roadmap workspace."""

from pathlib import Path

import click

from roadmap.application.contracts import WorkspaceInitializationRequest
from roadmap.domain.types import Name


def _directory_name(value: str) -> str:
    path = Path(value)
    if path.is_absolute() or len(path.parts) != 1 or value in {"", ".", ".."}:
        raise click.BadParameter(
            "name must be one local directory name", param_hint="--name"
        )
    return value


def _report_dry_run(
    name: str, result, skip_project: bool, project_name: str | None, default_name: str
) -> None:
    action = "create" if result.created_workspace else "verify"
    click.echo(f"Would {action} canonical workspace: {name}/")
    if not skip_project:
        click.echo(f"Would ensure project: {project_name or default_name}")


def _report_result(name: str, result) -> None:
    click.echo(
        f"Initialized canonical workspace: {name}/"
        if result.created_workspace
        else f"Canonical workspace already initialized: {name}/"
    )
    if result.created_project is not None:
        click.echo(f"Created project: {result.created_project.name}")


@click.command()
@click.option(
    "--name", "-n", default=".roadmap", callback=lambda _c, _p, v: _directory_name(v)
)
@click.option("--project-name", "-p")
@click.option("--description", "-d")
@click.option("--skip-project", is_flag=True)
@click.option("--interactive/--non-interactive", default=True)
@click.option("--yes", "-y", is_flag=True)
@click.option("--dry-run", is_flag=True)
@click.option("--force", "-f", is_flag=True)
@click.option("--template", "-t")
@click.option("--template-path")
@click.pass_context
def init(
    ctx: click.Context,
    name: str,
    project_name: str | None,
    description: str | None,
    skip_project: bool,
    interactive: bool,
    yes: bool,
    dry_run: bool,
    force: bool,
    template: str | None,
    template_path: str | None,
) -> None:
    """Create the local layout and, unless skipped, its first project."""
    del interactive, yes, template, template_path
    factory = ctx.find_root().obj.get("initialization_factory")
    if factory is None:
        raise click.ClickException("Roadmap CLI must be constructed by Bootstrap")
    default_name = Path.cwd().name or "Roadmap"
    result = factory(name).execute(
        WorkspaceInitializationRequest(
            project_name=None if skip_project else Name(project_name or default_name),
            description=description or "A project managed with Roadmap CLI",
            skip_project=skip_project,
            dry_run=dry_run,
            force=force,
        )
    )
    if result.dry_run:
        _report_dry_run(name, result, skip_project, project_name, default_name)
        return
    _report_result(name, result)
