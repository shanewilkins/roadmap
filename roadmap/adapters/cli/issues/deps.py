"""Dependencies command group."""

import click

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
def add_dependency(ctx: click.Context, issue_id: str, dependency_id: str):
    """Add a dependency to an issue."""
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return

    try:
        # Get the issue
        issue = core.issues.get(issue_id)
        if not issue:
            console.print(f"❌ Issue not found: {issue_id}", style="bold red")
            return

        # Check if dependency issue exists
        dependency_issue = core.issues.get(dependency_id)
        if not dependency_issue:
            console.print(
                f"❌ Dependency issue not found: {dependency_id}", style="bold red"
            )
            return

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
