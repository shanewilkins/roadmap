"""Top-level sync command - backend-agnostic interface to sync operations.

This command provides a unified interface for syncing with any backend
(GitHub, Git, etc.) without requiring the user to specify which backend.
The backend is automatically detected from configuration.
"""

import sys

import click
from structlog import get_logger

from roadmap.adapters.cli.cli_command_helpers import require_initialized
from roadmap.common.console import get_console

logger = get_logger(__name__)


def _show_baseline(core, backend, verbose, console_inst) -> bool:
    """Handle the `--base` flag: show or create baseline state."""
    from roadmap.adapters.cli.sync_handlers import show_baseline

    return show_baseline(core, backend, verbose, console_inst)


def _reset_baseline(core, backend, verbose, console_inst) -> bool:
    """Handle the `--reset-baseline` flag: force recalculation of baseline."""

    from roadmap.adapters.cli.services.sync_service import get_sync_backend
    from roadmap.adapters.cli.sync_context import (
        _clear_baseline_db,
        _create_and_save_baseline,
        _resolve_backend_and_init,
    )

    console_inst.print(
        "⚠️  WARNING: Resetting baseline will:",
        style="bold yellow",
    )
    console_inst.print("  • Clear all sync history")
    console_inst.print("  • Treat all current issues as the new baseline")
    console_inst.print("  • Next sync will see them as baseline (no changes)")
    console_inst.print()

    if not click.confirm("Continue with baseline reset?"):
        console_inst.print("Cancelled.", style="dim")
        return True

    # Determine backend
    backend_type, sync_backend = _resolve_backend_and_init(
        core, backend, get_sync_backend
    )
    if not sync_backend:
        console_inst.print("❌ Failed to initialize backend", style="bold red")
        sys.exit(1)

    # Clear existing baseline from database
    _clear_baseline_db(core, console_inst)

    # Create fresh baseline from current local state and save
    success = _create_and_save_baseline(
        core, sync_backend, backend_type, console_inst, verbose
    )
    if not success:
        sys.exit(1)

    return True


def _init_sync_context(core, backend, baseline_option, dry_run, verbose, console_inst):
    """Initialize backend, orchestrator, and required services for sync command.

    Returns tuple: (backend_type, sync_backend, orchestrator, pre_sync_baseline, pre_sync_issue_count, state_comparator, conflict_resolver)
    """
    from roadmap.adapters.cli.sync_context import _init_sync_context as _ctx

    return _ctx(core, backend, baseline_option, dry_run, verbose, console_inst)


def _resolve_backend_and_init(core, backend, get_sync_backend_callable):
    """Resolve backend_type and initialize the sync backend instance.

    Returns tuple `(backend_type, sync_backend)` where `sync_backend` may
    be None if initialization failed.
    """
    from roadmap.adapters.cli.sync_context import _resolve_backend_and_init as _ctx

    return _ctx(core, backend, get_sync_backend_callable)


def _clear_baseline_db(core, console_inst):
    """Clear baseline entries from the SQLite DB if present.

    Logs warnings but does not raise on failure.
    """
    from roadmap.adapters.cli.sync_context import _clear_baseline_db as _ctx

    return _ctx(core, console_inst)


def _create_and_save_baseline(
    core, sync_backend, backend_type, console_inst, verbose
) -> bool:
    """Create an initial baseline from local issues and save it to DB.

    Returns True on success, False otherwise.
    """
    from roadmap.adapters.cli.sync_context import _create_and_save_baseline as _ctx

    return _ctx(core, sync_backend, backend_type, console_inst, verbose)


def _capture_and_save_post_sync_baseline(
    core, console_inst, pre_sync_issue_count, verbose
):
    """Capture local issues and save them as the post-sync baseline."""
    from roadmap.adapters.cli.sync_handlers import capture_and_save_post_sync_baseline

    return capture_and_save_post_sync_baseline(
        core, console_inst, pre_sync_issue_count, verbose
    )


def _perform_apply_phase(
    core,
    orchestrator,
    console_inst,
    analysis_report,
    force_local,
    force_remote,
    push,
    pull,
    verbose,
):
    """Run the actual apply phase: perform sync and display summary."""
    from roadmap.adapters.cli.sync_handlers import perform_apply_phase

    return perform_apply_phase(
        core,
        orchestrator,
        console_inst,
        analysis_report,
        force_local,
        force_remote,
        push,
        pull,
        verbose,
    )


def _present_apply_intent(analysis_report, console_inst) -> bool:
    """Present whether there are changes to apply and return True if apply is needed."""
    from roadmap.adapters.cli.sync_handlers import present_apply_intent

    return present_apply_intent(analysis_report, console_inst)


def _confirm_and_apply(
    core,
    orchestrator,
    console_inst,
    analysis_report,
    force_local,
    force_remote,
    push,
    pull,
    verbose,
):
    """Ask for confirmation and run the apply phase if confirmed."""
    from roadmap.adapters.cli.sync_handlers import confirm_and_apply

    return confirm_and_apply(
        core,
        orchestrator,
        console_inst,
        analysis_report,
        force_local,
        force_remote,
        push,
        pull,
        verbose,
    )


def _finalize_sync(core, console_inst, report, pre_sync_issue_count, verbose):
    """Finalize sync run: capture post-sync baseline and print completion messages."""
    from roadmap.adapters.cli.sync_handlers import finalize_sync

    finalize_sync(core, console_inst, report, pre_sync_issue_count, verbose)


def _run_analysis_phase(orchestrator, push, pull, dry_run, verbose, console_inst):
    """Run analysis phase using orchestrator and present results.

    Returns: tuple(plan, analysis_report)
    """
    from roadmap.adapters.cli.sync_handlers import run_analysis_phase

    return run_analysis_phase(orchestrator, push, pull, dry_run, verbose, console_inst)


def _clear_baseline(core, backend, console_inst) -> bool:
    """Handle the `--clear-baseline` flag to clear baseline without syncing."""
    from roadmap.adapters.cli.sync_handlers import clear_baseline

    return clear_baseline(core, backend, console_inst)


def _show_conflicts(core, backend, verbose, console_inst) -> bool:
    """Handle the `--conflicts` flag to analyze and present conflicts."""
    from roadmap.adapters.cli.sync_handlers import show_conflicts

    return show_conflicts(core, backend, verbose, console_inst)


def _handle_link_unlink(core, backend, link, unlink, issue_id, console_inst) -> bool:
    """Handle `--link`/`--unlink` operations for manual remote ID management."""
    from roadmap.adapters.cli.sync_handlers import handle_link_unlink

    return handle_link_unlink(core, backend, link, unlink, issue_id, console_inst)


def _handle_pre_sync_actions(
    core,
    backend,
    base: bool,
    reset_baseline: bool,
    clear_baseline: bool,
    conflicts: bool,
    link: str | None,
    unlink: bool,
    issue_id: str | None,
    verbose: bool,
    console_inst,
) -> bool:
    """Handle pre-sync CLI actions that may short-circuit the main sync flow."""
    from roadmap.adapters.cli.sync_handlers import handle_pre_sync_actions

    return handle_pre_sync_actions(
        core,
        backend,
        base,
        reset_baseline,
        clear_baseline,
        conflicts,
        link,
        unlink,
        issue_id,
        verbose,
        console_inst,
    )


@click.command(name="sync")
@click.option(
    "--dry-run",
    is_flag=True,
    help="Preview changes without applying them",
)
@click.option(
    "--verbose",
    is_flag=True,
    help="Show detailed sync information",
)
@click.option(
    "--force-local",
    is_flag=True,
    help="Resolve all conflicts by keeping local changes",
)
@click.option(
    "--force-remote",
    is_flag=True,
    help="Resolve all conflicts by keeping remote changes",
)
@click.option(
    "--backend",
    type=click.Choice(["github", "git"], case_sensitive=False),
    default=None,
    help="Sync backend to use (auto-detected from config if not specified)",
)
@click.option(
    "--base",
    is_flag=True,
    help="Show the baseline state from the database (create if missing)",
)
@click.option(
    "--reset-baseline",
    is_flag=True,
    help="Force recalculate baseline from current state (WARNING: resets sync history)",
)
@click.option(
    "--clear-baseline",
    is_flag=True,
    help="Clear the baseline without syncing (clears sync_base_state table)",
)
@click.option(
    "--conflicts",
    is_flag=True,
    help="Show detailed conflict information between local, remote, and baseline",
)
@click.option(
    "--push",
    is_flag=True,
    help="Push local changes to remote only (no pull)",
)
@click.option(
    "--pull",
    is_flag=True,
    help="Pull remote changes and merge locally only (no push)",
)
@click.option(
    "--link",
    type=str,
    metavar="REMOTE_ID",
    help="Link local issue to remote ID (requires --issue-id)",
)
@click.option(
    "--unlink",
    is_flag=True,
    help="Unlink local issue from remote (requires --issue-id)",
)
@click.option(
    "--issue-id",
    type=str,
    help="Local issue ID for link/unlink operations",
)
@click.option(
    "--baseline",
    type=click.Choice(["local", "remote", "interactive"], case_sensitive=False),
    default=None,
    help="Strategy for first sync baseline (local=local is source, remote=remote is source, interactive=choose per-issue)",
)
@click.pass_context
@require_initialized
def sync(
    ctx: click.Context,
    dry_run: bool,
    verbose: bool,
    force_local: bool,
    force_remote: bool,
    backend: str | None,
    base: bool,
    reset_baseline: bool,
    clear_baseline: bool,
    conflicts: bool,
    push: bool,
    pull: bool,
    link: str | None,
    unlink: bool,
    issue_id: str | None,
    baseline: str | None,
) -> None:
    """Sync roadmap with remote repository.

    This command provides intelligent two-way sync with automatic conflict
    resolution using three-way merge. It supports multiple backends:

    - **github**: Sync with GitHub issues API (requires GitHub configuration)
    - **git**: Sync with Git repository (works with any Git hosting)

    If no backend is specified, the command auto-detects from your config
    (set during `roadmap init`).

    **Sync Process:**
    1. Pull remote changes → merge with local using three-way merge
    2. Resolve conflicts automatically (when possible)
    3. Flag unresolvable conflicts for manual review
    4. Push local changes to remote
    5. User must manually run: git add, git commit, git push

    **Conflict Resolution:**
    - Critical fields (status, assignee, milestone) → flagged for review
    - Non-critical fields (labels, description) → automatically merged
    - Metadata (timestamps) → remote wins (remote is authoritative)

    **Examples:**
        # Sync with GitHub API
        roadmap sync

        # Preview changes (dry-run, no modifications)
        roadmap sync --dry-run

        # Sync with verbose output (shows all pulls and pushes)
        roadmap sync --verbose

        # First sync with local as baseline (local is source of truth)
        roadmap sync --baseline=local

        # First sync with remote as baseline (remote is source of truth)
        roadmap sync --baseline=remote

        # First sync with interactive baseline (choose per-issue)
        roadmap sync --baseline=interactive

        # Resolve all conflicts locally (keep your changes)
        roadmap sync --force-local

        # Override backend selection
        roadmap sync --backend=github
    """

    core = ctx.obj["core"]
    console_inst = get_console()

    # Validate mutually exclusive flags
    if push and pull:
        console_inst.print(
            "❌ Cannot use both --push and --pull together. Choose one direction.",
            style="bold red",
        )
        sys.exit(1)
    # Handle early pre-sync actions (baseline display/reset/clear, conflicts, link/unlink)
    if _handle_pre_sync_actions(
        core,
        backend,
        base,
        reset_baseline,
        clear_baseline,
        conflicts,
        link,
        unlink,
        issue_id,
        verbose,
        console_inst,
    ):
        return

    try:
        (
            backend_type,
            sync_backend,
            orchestrator,
            pre_sync_baseline,
            pre_sync_issue_count,
            state_comparator,
            conflict_resolver,
        ) = _init_sync_context(core, backend, baseline, dry_run, verbose, console_inst)

        # ANALYSIS PHASE: Run sync analyzer and present results

        plan, analysis_report = _run_analysis_phase(
            orchestrator, push, pull, dry_run, verbose, console_inst
        )

        # If dry-run, stop here and show what would be applied
        if dry_run:
            console_inst.print(
                "\n[bold yellow]⚠️  Dry-run mode - Preview only[/bold yellow]"
            )
            return

        # Determine whether there is anything to apply
        if not _present_apply_intent(analysis_report, console_inst):
            return

        # Confirm and run apply phase
        report = _confirm_and_apply(
            core,
            orchestrator,
            console_inst,
            analysis_report,
            force_local,
            force_remote,
            push,
            pull,
            verbose,
        )

        # User cancelled
        if report is None:
            return

        # If dry-run flag, note that no changes were applied
        if dry_run:
            console_inst.print(
                "[bold yellow]⚠️  Dry-run mode: No changes applied[/bold yellow]"
            )
            # Show BEFORE state for dry-run
            if verbose and pre_sync_baseline:
                console_inst.print(
                    "\n[bold]BEFORE STATE (for reference):[/bold]",
                    style="dim",
                )
                console_inst.print(
                    f"   Baseline issues: {pre_sync_issue_count}",
                    style="dim",
                )
            return

        # Finalize the real sync
        _finalize_sync(core, console_inst, report, pre_sync_issue_count, verbose)

    except Exception as exc:
        logger.error(
            "sync_command_failed",
            operation="sync",
            error_type=type(exc).__name__,
            error=str(exc),
            error_classification="cli_error",
            suggested_action="check_logs_for_details",
        )
        console_inst.print(
            f"❌ Unexpected error during sync: {exc}",
            style="bold red",
        )
        if verbose:
            raise
        sys.exit(1)
