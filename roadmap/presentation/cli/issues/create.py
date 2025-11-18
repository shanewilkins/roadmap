"""Create issue command."""

import os
import subprocess

import click

from roadmap.cli.utils import get_console
from roadmap.shared.errors import ErrorHandler, ValidationError
from roadmap.domain import IssueType, Priority

console = get_console()


def _safe_create_branch(git, issue, checkout=True, force=False):
    """Call create_branch_for_issue with best-effort compatibility for older signatures.

    Tries the newest signature (checkout, force) first, falls back to older ones.
    """
    try:
        return git.create_branch_for_issue(issue, checkout=checkout, force=force)
    except TypeError:
        # Try without force
        try:
            return git.create_branch_for_issue(issue, checkout=checkout)
        except TypeError:
            # Try fully positional (issue only)
            try:
                return git.create_branch_for_issue(issue)
            except Exception:
                return False


@click.command("create")
@click.argument("title")
@click.option(
    "--priority",
    "-p",
    type=click.Choice(["critical", "high", "medium", "low"]),
    default="medium",
    help="Issue priority",
)
@click.option(
    "--type",
    "-t",
    "issue_type",
    type=click.Choice(["feature", "bug", "other"]),
    default="other",
    help="Issue type",
)
@click.option("--milestone", "-m", help="Assign to milestone")
@click.option("--assignee", "-a", help="Assign to team member")
@click.option("--labels", "-l", multiple=True, help="Add labels")
@click.option(
    "--estimate", "-e", type=float, help="Estimated time to complete (in hours)"
)
@click.option("--depends-on", multiple=True, help="Issue IDs this depends on")
@click.option("--blocks", multiple=True, help="Issue IDs this blocks")
@click.option("--git-branch", is_flag=True, help="Create a Git branch for this issue")
@click.option(
    "--checkout/--no-checkout",
    default=True,
    help="Checkout the branch after creation (with --git-branch)",
)
@click.option("--branch-name", default=None, help="Override suggested branch name")
@click.option(
    "--force", is_flag=True, help="Force branch creation even if working tree is dirty"
)
@click.pass_context
def create_issue(
    ctx: click.Context,
    title: str,
    priority: str,
    issue_type: str,
    milestone: str,
    assignee: str,
    labels: tuple,
    estimate: float,
    depends_on: tuple,
    blocks: tuple,
    git_branch: bool,
    checkout: bool,
    branch_name: str,
    force: bool,
):
    """Create a new issue."""
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return

    try:
        # Auto-detect assignee from Git if not provided
        if not assignee:
            git_user = core.get_current_user_from_git()
            if git_user:
                assignee = git_user
                console.print(
                    f"🔍 Auto-detected assignee from Git: {assignee}", style="dim"
                )

        # Validate assignee if provided
        canonical_assignee = assignee
        if assignee:
            is_valid, result = core.validate_assignee(assignee)
            if not is_valid:
                console.print(f"❌ Invalid assignee: {result}", style="bold red")
                raise click.Abort()
            elif result and "Warning:" in result:
                console.print(f"⚠️  {result}", style="bold yellow")
                canonical_assignee = assignee  # Keep original if warning
            else:
                canonical_assignee = core.get_canonical_assignee(assignee)
                if canonical_assignee != assignee:
                    console.print(
                        f"🔄 Resolved '{assignee}' to '{canonical_assignee}'",
                        style="dim",
                    )

        issue = core.create_issue(
            title=title,
            priority=Priority(priority),
            issue_type=IssueType(issue_type),
            milestone=milestone,
            assignee=canonical_assignee,
            labels=list(labels),
            estimated_hours=estimate,
            depends_on=list(depends_on),
            blocks=list(blocks),
        )
        console.print(f"✅ Created issue: {issue.title}", style="bold green")
        console.print(f"   ID: {issue.id}", style="cyan")
        console.print(f"   Type: {issue.issue_type.value.title()}", style="blue")
        console.print(f"   Priority: {issue.priority.value}", style="yellow")
        if milestone:
            console.print(f"   Milestone: {milestone}", style="blue")
        if assignee:
            console.print(f"   Assignee: {assignee}", style="magenta")
        if estimate:
            console.print(
                f"   Estimated: {issue.estimated_time_display}", style="green"
            )
        if depends_on:
            console.print(f"   Depends on: {', '.join(depends_on)}", style="orange1")
        if blocks:
            console.print(f"   Blocks: {', '.join(blocks)}", style="red1")

        # Create Git branch if requested
        if git_branch:
            if hasattr(core, "git") and core.git.is_git_repository():
                # Determine resolved branch name early so fallbacks use the same name
                resolved_branch_name = branch_name or core.git.suggest_branch_name(
                    issue
                )
                branch_success = _safe_create_branch(
                    core.git, issue, checkout=checkout, force=force
                )
                if branch_success:
                    console.print(
                        f"🌿 Created Git branch: {resolved_branch_name}", style="green"
                    )
                    if checkout:
                        console.print(
                            f"✅ Checked out branch: {resolved_branch_name}",
                            style="green",
                        )
                else:
                    # Determine likely reason for failure
                    status_output = (
                        core.git._run_git_command(["status", "--porcelain"]) or ""
                    )
                    if status_output.strip():
                        console.print(
                            "⚠️  Working tree has uncommitted changes — branch creation skipped. Use --force to override.",
                            style="yellow",
                        )
                    else:
                        # Try fallback direct git command
                        fallback = core.git._run_git_command(
                            ["checkout", "-b", resolved_branch_name]
                        )
                        if fallback is not None:
                            console.print(
                                f"🌿 Created Git branch: {resolved_branch_name}",
                                style="green",
                            )
                            if checkout:
                                console.print(
                                    f"✅ Checked out branch: {resolved_branch_name}",
                                    style="green",
                                )
                        else:
                            # Final check: maybe branch exists already; verify via rev-parse
                            exists = None
                            try:
                                if hasattr(core, "git"):
                                    exists = core.git._run_git_command(
                                        ["rev-parse", "--verify", resolved_branch_name]
                                    )
                            except Exception:
                                exists = None

                            if exists:
                                console.print(
                                    f"🌿 Created Git branch: {resolved_branch_name}",
                                    style="green",
                                )
                                if checkout:
                                    console.print(
                                        f"✅ Checked out branch: {resolved_branch_name}",
                                        style="green",
                                    )
                            else:
                                # As a last resort try running git directly in the repo root
                                try:
                                    subprocess.run(
                                        [
                                            "git",
                                            "checkout",
                                            "-b",
                                            resolved_branch_name,
                                        ],
                                        cwd=getattr(core, "root_path", None)
                                        or os.getcwd(),
                                        check=True,
                                        capture_output=True,
                                        text=True,
                                    )
                                    console.print(
                                        f"🌿 Created Git branch: {resolved_branch_name}",
                                        style="green",
                                    )
                                    if checkout:
                                        console.print(
                                            f"✅ Checked out branch: {resolved_branch_name}",
                                            style="green",
                                        )
                                except Exception:
                                    console.print(
                                        "⚠️  Failed to create or checkout branch. See git for details.",
                                        style="yellow",
                                    )
            else:
                console.print(
                    "⚠️  Not in a Git repository, skipping branch creation",
                    style="yellow",
                )

        console.print(f"   File: .roadmap/issues/{issue.filename}", style="dim")
    except click.Abort:
        # Re-raise click.Abort to maintain proper exit code
        raise
    except Exception as e:
        error_handler = ErrorHandler()
        error_handler.handle_error(
            ValidationError(
                "Failed to create issue",
                context={"command": "create", "title": title},
                cause=e,
            ),
            exit_on_critical=False,
        )
