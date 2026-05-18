"""Dependencies command group."""

import click

from roadmap.adapters.cli.cli_command_helpers import (
    ensure_entity_exists,
    require_initialized,
)
from roadmap.adapters.cli.cli_error_handlers import handle_cli_error
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
        handle_cli_error(
            error=e,
            operation="add_dependency",
            entity_type="issue",
            entity_id=issue_id,
            context={"dependency_id": dependency_id},
            fatal=True,
        )
        console.print(f"❌ Failed to add dependency: {e}", style="bold red")


@deps.command("remove")
@click.argument("issue_id")
@click.argument("dependency_id")
@click.pass_context
@require_initialized
def remove_dependency(ctx: click.Context, issue_id: str, dependency_id: str):
    """Remove a dependency from an issue."""
    core = ctx.obj["core"]

    try:
        issue = ensure_entity_exists(core, "issue", issue_id)

        current_deps = list(issue.depends_on or [])
        if dependency_id not in current_deps:
            console.print(
                f"⚠️ Dependency '{dependency_id}' not found on issue {issue_id}",
                style="yellow",
            )
            return

        updated_deps = [dep for dep in current_deps if dep != dependency_id]
        core.issues.update(issue_id, depends_on=updated_deps)

        console.print(
            f"✅ Removed dependency: {dependency_id}",
            style="bold green",
        )
        console.print(
            f"   {issue.title} no longer depends on {dependency_id}", style="dim"
        )

    except Exception as e:
        handle_cli_error(
            error=e,
            operation="remove_dependency",
            entity_type="issue",
            entity_id=issue_id,
            context={"dependency_id": dependency_id},
            fatal=True,
        )
        console.print(f"❌ Failed to remove dependency: {e}", style="bold red")


@deps.command("update")
@click.argument("issue_id")
@click.argument("old_dependency_id")
@click.argument("new_dependency_id")
@click.pass_context
@require_initialized
def update_dependency(
    ctx: click.Context,
    issue_id: str,
    old_dependency_id: str,
    new_dependency_id: str,
):
    """Replace one dependency with another on an issue."""
    core = ctx.obj["core"]

    try:
        issue = ensure_entity_exists(core, "issue", issue_id)
        ensure_entity_exists(core, "issue", new_dependency_id)

        current_deps = list(issue.depends_on or [])
        if old_dependency_id not in current_deps:
            console.print(
                (f"⚠️ Dependency '{old_dependency_id}' not found on issue {issue_id}"),
                style="yellow",
            )
            return

        if new_dependency_id in current_deps and new_dependency_id != old_dependency_id:
            updated_deps = [dep for dep in current_deps if dep != old_dependency_id]
        else:
            updated_deps = [
                (new_dependency_id if dep == old_dependency_id else dep)
                for dep in current_deps
            ]

        core.issues.update(issue_id, depends_on=updated_deps)

        console.print(
            f"✅ Updated dependency: {old_dependency_id} → {new_dependency_id}",
            style="bold green",
        )
        console.print(f"   {issue.title} dependency updated successfully", style="dim")

    except Exception as e:
        handle_cli_error(
            error=e,
            operation="update_dependency",
            entity_type="issue",
            entity_id=issue_id,
            context={
                "old_dependency_id": old_dependency_id,
                "new_dependency_id": new_dependency_id,
            },
            fatal=True,
        )
        console.print(f"❌ Failed to update dependency: {e}", style="bold red")
