"""Dependencies command group."""

import click

from roadmap.adapters.cli.helpers import ensure_entity_exists, require_initialized
from roadmap.common.console import get_console

console = get_console()


@click.group("deps")
def deps():
    """Manage issue dependencies."""
    pass


@deps.command("add")
@click.argument("issue_id")
@click.argument("dependency_id")
@click.pass_context
@require_initialized
def add_dependency(ctx: click.Context, issue_id: str, dependency_id: str):
    """Add a dependency to an issue."""
    core = ctx.obj["core"]

    try:
        # Get the issue
        issue = ensure_entity_exists(core, "issue", issue_id)

        # Check if dependency issue exists
        dependency_issue = ensure_entity_exists(core, "issue", dependency_id)

        # Add dependency
        current_deps = issue.depends_on or []
        if dependency_id not in current_deps:
            current_deps.append(dependency_id)
            core.issues.update(issue_id, depends_on=current_deps)
            console.print(
                f"✅ Added dependency: {dependency_issue.title}", style="bold green"
            )
            console.print(
                f"   {issue.title} now depends on {dependency_issue.title}", style="dim"
            )
        else:
            console.print("⚠️ Dependency already exists", style="yellow")

    except Exception as e:
        console.print(f"❌ Failed to add dependency: {e}", style="bold red")
