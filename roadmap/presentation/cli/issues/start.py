"""Start issue command."""

from datetime import datetime

import click

from roadmap.cli.utils import get_console
from roadmap.domain import Status

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


@click.command("start")
@click.argument("issue_id")
@click.option("--date", help="Start date (YYYY-MM-DD HH:MM, defaults to now)")
@click.option(
    "--git-branch/--no-git-branch",
    default=False,
    help="Create a Git branch for this issue when starting",
)
@click.option(
    "--checkout/--no-checkout",
    default=True,
    help="Checkout the created branch (when --git-branch is used)",
)
@click.option("--branch-name", default=None, help="Override suggested branch name")
@click.option(
    "--force", is_flag=True, help="Force branch creation even if working tree is dirty"
)
@click.pass_context
def start_issue(
    ctx: click.Context,
    issue_id: str,
    date: str,
    git_branch: bool,
    checkout: bool,
    branch_name: str,
    force: bool,
):
    """Start work on an issue by recording the actual start date."""
    core = ctx.obj["core"]

    if not core.is_initialized():
        console.print(
            "❌ Roadmap not initialized. Run 'roadmap init' first.", style="bold red"
        )
        return

    try:
        # Parse start date
        if date:
            try:
                start_date = datetime.strptime(date, "%Y-%m-%d %H:%M")
            except ValueError:
                try:
                    start_date = datetime.strptime(date, "%Y-%m-%d")
                except ValueError:
                    console.print(
                        "❌ Invalid date format. Use YYYY-MM-DD or YYYY-MM-DD HH:MM",
                        style="bold red",
                    )
                    return
        else:
            start_date = datetime.now()

        # Get the issue
        issue = core.get_issue(issue_id)
        if not issue:
            console.print(f"❌ Issue not found: {issue_id}", style="bold red")
            return

        # Update issue with start date and status
        success = core.update_issue(
            issue_id,
            actual_start_date=start_date,
            status=Status.IN_PROGRESS,
            progress_percentage=0.0,
        )

        if success:
            console.print(f"🚀 Started work on: {issue.title}", style="bold green")
            console.print(
                f"   Started: {start_date.strftime('%Y-%m-%d %H:%M')}", style="cyan"
            )
            console.print("   Status: In Progress", style="yellow")
            # Determine git-branch behavior: CLI flag overrides, otherwise check config
            try:
                from roadmap.domain import RoadmapConfig

                cfg = (
                    RoadmapConfig.load_from_file(core.config_file)
                    if core.config_file.exists()
                    else RoadmapConfig()
                )
                config_auto_branch = bool(cfg.defaults.get("auto_branch", False))
            except Exception:
                config_auto_branch = False

            if not git_branch and config_auto_branch:
                git_branch = True

            # Optionally create a git branch for the issue
            try:
                if git_branch:
                    if hasattr(core, "git") and core.git.is_git_repository():
                        resolved_branch_name = (
                            branch_name or core.git.suggest_branch_name(issue)
                        )
                        branch_success = _safe_create_branch(
                            core.git, issue, checkout=checkout, force=force
                        )
                        if branch_success:
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
                            status_output = (
                                core.git._run_git_command(["status", "--porcelain"])
                                or ""
                            )
                            if status_output.strip():
                                console.print(
                                    "⚠️  Working tree has uncommitted changes — branch creation skipped. Use --force to override.",
                                    style="yellow",
                                )
                            else:
                                console.print(
                                    "⚠️  Failed to create or checkout branch. See git for details.",
                                    style="yellow",
                                )
                    else:
                        console.print(
                            "⚠️  Not in a Git repository, skipping branch creation",
                            style="yellow",
                        )
            except Exception as e:
                console.print(
                    f"⚠️  Git branch creation skipped due to error: {e}", style="yellow"
                )
        else:
            console.print(f"❌ Failed to start issue: {issue_id}", style="bold red")

    except Exception as e:
        console.print(f"❌ Failed to start issue: {e}", style="bold red")
