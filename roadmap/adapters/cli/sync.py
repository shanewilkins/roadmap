"""Top-level sync command - backend-agnostic interface to sync operations.

This command provides a unified interface for syncing with any backend
(GitHub, Git, etc.) without requiring the user to specify which backend.
The backend is automatically detected from configuration.
"""

import sys

import click
from structlog import get_logger

from roadmap.adapters.cli.cli_command_helpers import require_initialized
from roadmap.adapters.cli.sync_metrics_command import sync_metrics
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


def _init_sync_context(
    core,
    backend,
    baseline_option,
    dry_run,
    verbose,
    console_inst,
    enable_duplicate_detection=True,
    title_threshold=0.90,
    content_threshold=0.85,
    auto_resolve_threshold=0.95,
):
    """Initialize backend, orchestrator, and required services for sync command.

    Returns tuple: (backend_type, sync_backend, orchestrator, pre_sync_baseline, pre_sync_issue_count, state_comparator, conflict_resolver)
    """
    from roadmap.adapters.cli.sync_context import _init_sync_context as _ctx

    return _ctx(
        core,
        backend,
        baseline_option,
        dry_run,
        verbose,
        console_inst,
        enable_duplicate_detection,
        title_threshold,
        content_threshold,
        auto_resolve_threshold,
    )


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
    interactive,
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
        interactive,
    )


def _finalize_sync(
    core,
    console_inst,
    report,
    pre_sync_issue_count,
    verbose,
    backend_type: str | None,
):
    """Finalize sync run: capture post-sync baseline and print completion messages."""
    from roadmap.adapters.cli.sync_handlers import finalize_sync

    finalize_sync(
        core,
        console_inst,
        report,
        pre_sync_issue_count,
        verbose,
        backend_type,
    )


def _run_analysis_phase(
    orchestrator,
    push,
    pull,
    dry_run,
    verbose,
    console_inst,
    interactive_duplicates=False,
):
    """Run analysis phase using orchestrator and present results.

    Returns: tuple(plan, analysis_report)
    """
    from roadmap.adapters.cli.sync_handlers import run_analysis_phase

    return run_analysis_phase(
        orchestrator, push, pull, dry_run, verbose, console_inst, interactive_duplicates
    )


def _build_local_status_breakdown(local_only_issues):
    """Build status breakdown string for local-only issues."""
    from collections import Counter

    statuses = [c.local_state.status for c in local_only_issues if c.local_state]
    status_counts = Counter(statuses)
    return ", ".join(f"{s}: {count}" for s, count in sorted(status_counts.items()))


def _build_remote_status_breakdown(remote_only_issues):
    """Build status breakdown string for remote-only issues."""
    from collections import Counter

    statuses = [
        c.remote_state.get("status") for c in remote_only_issues if c.remote_state
    ]
    status_counts = Counter(statuses)
    return ", ".join(f"{s}: {count}" for s, count in sorted(status_counts.items()))


def _display_local_only_issues(local_only_issues, console_inst):
    """Display local-only issues in a formatted table."""
    from rich.table import Table

    console_inst.print(
        "\n[bold cyan]📝 Local-Only Issues[/bold cyan] (exist locally but not remotely)"
    )

    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Local ID", style="dim", width=10)
    table.add_column("Title", width=50)
    table.add_column("Status", style="yellow", width=12)

    for change in sorted(local_only_issues, key=lambda c: c.title):
        status = change.local_state.status if change.local_state else "unknown"
        table.add_row(change.issue_id[:8], change.title, status)

    console_inst.print(table)

    # Show status breakdown
    breakdown = _build_local_status_breakdown(local_only_issues)
    console_inst.print(
        f"[dim]Total: {len(local_only_issues)} issues ({breakdown})[/dim]"
    )


def _display_remote_only_issues(remote_only_issues, console_inst):
    """Display remote-only issues in a formatted table with link status."""
    from rich.table import Table

    console_inst.print(
        "\n[bold cyan]🔄 Remote-Only Issues[/bold cyan] (exist remotely but not locally)"
    )

    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Local ID", style="dim", width=10)
    table.add_column("Remote ID", style="cyan", width=12)
    table.add_column("Title", width=40)
    table.add_column("Status", style="yellow", width=10)
    table.add_column("Linked", width=8)

    # Count linked vs orphaned
    linked_count = 0
    orphaned_count = 0

    for change in sorted(remote_only_issues, key=lambda c: c.title):
        status = change.remote_state.get("status") if change.remote_state else "unknown"
        # Extract remote ID (backend_id) from remote_state
        remote_id = (
            change.remote_state.get("backend_id") if change.remote_state else "?"
        )

        # Determine if linked (has a local ID that's not "_remote_")
        is_linked = change.issue_id and not change.issue_id.startswith("_remote_")
        if is_linked:
            linked_icon = "[green]✓[/green]"
            linked_count += 1
        else:
            linked_icon = "[dim red]✗[/dim red]"
            orphaned_count += 1

        table.add_row(
            change.issue_id[:8] if is_linked else "_remote_",
            str(remote_id),
            change.title,
            status,
            linked_icon,
        )

    console_inst.print(table)

    # Show status breakdown and link status
    breakdown = _build_remote_status_breakdown(remote_only_issues)
    console_inst.print(
        f"[dim]Total: {len(remote_only_issues)} issues ({breakdown})[/dim]"
    )
    console_inst.print(
        f"[green]Linked to local: {linked_count}[/green] | [dim red]Orphaned (no local match): {orphaned_count}[/dim red]"
    )


def _display_issue_lists(core, analysis_report, local_only, remote_only, console_inst):
    """Display lists of local-only or remote-only issues."""
    if not hasattr(analysis_report, "changes") or not analysis_report.changes:
        console_inst.print("[dim]No issues found[/dim]")
        return

    # Get all issues by type
    local_only_issues = [c for c in analysis_report.changes if c.is_local_only_change()]
    remote_only_issues = [
        c for c in analysis_report.changes if c.is_remote_only_change()
    ]

    if local_only and local_only_issues:
        _display_local_only_issues(local_only_issues, console_inst)

    if remote_only and remote_only_issues:
        _display_remote_only_issues(remote_only_issues, console_inst)

    if not (local_only or remote_only):
        console_inst.print(
            "[dim]Use --local-only or --remote-only to see issue lists[/dim]"
        )


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


@click.group(invoke_without_command=True)
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
@click.option(
    "--local-only",
    is_flag=True,
    help="Show issues that exist locally but not remotely",
)
@click.option(
    "--remote-only",
    is_flag=True,
    help="Show issues that exist remotely but not locally",
)
@click.option(
    "--milestone",
    "-m",
    multiple=True,
    help="Filter sync to specific milestones (can specify multiple)",
)
@click.option(
    "--milestone-state",
    type=click.Choice(["open", "closed", "all"], case_sensitive=False),
    default="all",
    help="Filter milestones by state (default: all)",
)
@click.option(
    "--since",
    type=str,
    help="Only sync milestones updated since date (ISO format: YYYY-MM-DD)",
)
@click.option(
    "--until",
    type=str,
    help="Only sync milestones updated until date (ISO format: YYYY-MM-DD)",
)
@click.option(
    "--interactive",
    "-i",
    is_flag=True,
    help="Interactively resolve conflicts with visual diffs and prompts",
)
@click.option(
    "--resume",
    is_flag=True,
    help="Resume from last checkpoint after a failed sync",
)
@click.option(
    "--detect-duplicates/--no-detect-duplicates",
    default=True,
    help="Enable/disable duplicate detection during sync (default: enabled)",
)
@click.option(
    "--interactive-duplicates",
    is_flag=True,
    help="Interactively resolve detected duplicate issues with prompts",
)
@click.option(
    "--duplicate-title-threshold",
    type=float,
    default=None,
    help="Minimum similarity for title duplicates (0.0-1.0, default from config)",
)
@click.option(
    "--duplicate-content-threshold",
    type=float,
    default=None,
    help="Minimum similarity for content duplicates (0.0-1.0, default from config)",
)
@click.option(
    "--duplicate-auto-resolve-threshold",
    type=float,
    default=None,
    help="Minimum confidence for auto-resolving duplicates (0.0-1.0, default from config)",
)
@click.option(
    "--show-metrics",
    is_flag=True,
    help="Display sync metrics after completion",
)
@click.option(
    "--dedup-only",
    is_flag=True,
    help="Run only the deduplication phase (detect and delete duplicates, skip sync)",
)
@click.option(
    "--fuzzy",
    is_flag=True,
    help="Enable fuzzy matching for duplicate detection (slower but more thorough)",
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
    local_only: bool,
    remote_only: bool,
    milestone: tuple[str, ...],
    milestone_state: str,
    since: str | None,
    until: str | None,
    interactive: bool,
    resume: bool,
    detect_duplicates: bool,
    interactive_duplicates: bool,
    duplicate_title_threshold: float | None,
    duplicate_content_threshold: float | None,
    duplicate_auto_resolve_threshold: float | None,
    show_metrics: bool,
    dedup_only: bool,
    fuzzy: bool,
) -> None:
    """Sync roadmap with remote repository.

    This command provides intelligent two-way sync with automatic conflict
    resolution using three-way merge. It supports multiple backends:

    - **github**: Sync with GitHub issues API (requires GitHub configuration)
    - **git**: Sync with Git repository (works with any Git hosting)

    If no backend is specified, the command auto-detects from your config
    (set during `roadmap init`). GitHub owner/repo can be auto-detected from
    your git remote origin URL.

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

    **Milestone Filtering:**
    - Filter sync to specific milestones by name: --milestone "v1.0"
    - Filter by state: --milestone-state open|closed|all
    - Filter by date range: --since 2024-01-01 --until 2024-12-31
    - Combine filters: --milestone "v1.0" --milestone "v2.0" --milestone-state open

    **Examples:**
        # Sync with GitHub API
        roadmap sync

        # Preview changes (dry-run, detailed preview)
        roadmap sync --dry-run --verbose

        # Sync specific milestones only
        roadmap sync --milestone "v1.0" --milestone "v2.0"

        # Sync only open milestones
        roadmap sync --milestone-state open

        # Sync milestones updated since a date
        roadmap sync --since 2024-01-01

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

    # If a subcommand is being invoked, handle it
    if ctx.invoked_subcommand is not None:
        return

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

    # Handle dedup-only mode
    if dedup_only:
        _execute_dedup_only(
            core,
            console_inst,
            verbose,
            detect_duplicates,
            duplicate_title_threshold,
            duplicate_content_threshold,
            duplicate_auto_resolve_threshold,
            interactive_duplicates,
            fuzzy,
            dry_run,
        )
        return

    # Handle checkpoint resume if requested
    if resume:
        if not _handle_resume(console_inst, core):
            return

    try:
        _execute_sync_workflow(
            core,
            console_inst,
            backend,
            baseline,
            dry_run,
            verbose,
            detect_duplicates,
            duplicate_title_threshold,
            duplicate_content_threshold,
            duplicate_auto_resolve_threshold,
            push,
            pull,
            force_local,
            force_remote,
            local_only,
            remote_only,
            milestone,
            milestone_state,
            since,
            until,
            interactive,
            show_metrics,
        )
    except Exception as exc:
        logger.error(
            "sync_command_failed",
            operation="sync",
            error_type=type(exc).__name__,
            error=str(exc),
            severity="operational",
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


def _handle_resume(console_inst, core) -> bool:
    """Handle checkpoint resume logic.

    Returns True to continue, False to exit.
    """
    from roadmap.core.services.sync.sync_checkpoint import SyncCheckpointManager

    checkpoint_manager = SyncCheckpointManager(core)
    can_resume, checkpoint = checkpoint_manager.can_resume()

    if can_resume and checkpoint:
        console_inst.print("\n[bold cyan]📍 Resuming from checkpoint[/bold cyan]")
        console_inst.print(f"[dim]Checkpoint ID: {checkpoint.checkpoint_id}[/dim]")
        console_inst.print(f"[dim]Phase: {checkpoint.phase}[/dim]")
        console_inst.print(f"[dim]Timestamp: {checkpoint.timestamp}[/dim]")

        if not click.confirm("\nContinue with resume?", default=True):
            console_inst.print("[yellow]Resume cancelled[/yellow]")
            return False
        return True
    else:
        console_inst.print(
            "[yellow]⚠️  No resumable checkpoint found or checkpoint too old[/yellow]"
        )
        if checkpoint:
            console_inst.print(
                f"[dim]Last checkpoint was in phase '{checkpoint.phase}' at {checkpoint.timestamp}[/dim]"
            )
        return False


def _execute_dedup_only(
    core,
    console_inst,
    verbose,
    detect_duplicates,
    duplicate_title_threshold,
    duplicate_content_threshold,
    duplicate_auto_resolve_threshold,
    interactive_duplicates,
    fuzzy: bool = False,
    dry_run: bool = False,
) -> None:
    """Execute deduplication phase only (no sync).

    Fetches local and remote issues, detects duplicates in both,
    and deletes duplicates (both local and remote via GraphQL).

    Args:
        core: RoadmapCore instance
        console_inst: Console instance for output
        verbose: If True, show detailed output
        detect_duplicates: If True, enable duplicate detection
        duplicate_title_threshold: Title similarity threshold override
        duplicate_content_threshold: Content similarity threshold override
        duplicate_auto_resolve_threshold: Auto-resolve confidence threshold
        interactive_duplicates: If True, prompt for duplicate resolution
        fuzzy: If True, enable fuzzy matching (slower but catches more duplicates)
        dry_run: If True, preview duplicates without actually deleting
    """
    import time

    from roadmap.adapters.cli.services.sync_service import get_sync_backend
    from roadmap.adapters.cli.sync_context import _resolve_backend_and_init
    from roadmap.application.services.deduplicate_service import DeduplicateService
    from roadmap.core.services.sync.duplicate_detector import DuplicateDetector

    if not detect_duplicates:
        console_inst.print(
            "[yellow]⚠️  Duplicate detection is disabled (--no-detect-duplicates)[/yellow]"
        )
        return

    console_inst.print("[bold cyan]🔍 Deduplication Only Mode[/bold cyan]")
    if fuzzy:
        console_inst.print("[yellow]⚠️  Fuzzy matching ENABLED (slower)[/yellow]")
    console_inst.print("[dim]Fetching issues and detecting duplicates...[/dim]\n")

    start_time = time.time()

    # Fetch local issues
    try:
        local_issues = core.issue_service.list_all_including_archived() or []
        console_inst.print(f"   📋 Loaded {len(local_issues)} local issues")
    except Exception as e:
        console_inst.print(f"❌ Failed to load local issues: {e}", style="bold red")
        return

    # Initialize backend for remote issue fetching
    sync_backend = None
    remote_issues = {}
    try:
        _, sync_backend = _resolve_backend_and_init(core, None, get_sync_backend)
        if sync_backend:
            # Authenticate with backend
            auth_result = sync_backend.authenticate()
            if not auth_result.is_ok():
                console_inst.print(
                    "[yellow]⚠️  Backend authentication failed, skipping remote deduplication[/yellow]"
                )
                sync_backend = None
            else:
                # Fetch remote issues
                issues_result = sync_backend.get_issues()
                if issues_result.is_ok():
                    remote_issues = issues_result.unwrap() or {}
                    console_inst.print(
                        f"   📋 Loaded {len(remote_issues)} remote issues"
                    )
                    # Note: Remote deletion uses small batches (5 per call) with delays
                    # to respect GitHub's rate limits (2,000 points/minute on GraphQL)
                    if len(remote_issues) > 1000:
                        console_inst.print(
                            "[dim]ℹ️  Large dataset detected - remote deletion will be slow (respecting GitHub rate limits)[/dim]"
                        )
                else:
                    console_inst.print(
                        "[yellow]⚠️  Failed to fetch remote issues, skipping remote deduplication[/yellow]"
                    )
    except Exception as e:
        console_inst.print(f"[yellow]⚠️  Could not initialize backend: {e}[/yellow]")
        if verbose:
            logger.exception("backend_init_failed")

    # Create duplicate detector with configured thresholds
    detector = DuplicateDetector(
        title_similarity_threshold=duplicate_title_threshold or 0.90,
        content_similarity_threshold=duplicate_content_threshold or 0.85,
        auto_resolve_threshold=duplicate_auto_resolve_threshold or 0.95,
        enable_fuzzy_matching=fuzzy,
    )

    # Run deduplication with backend for remote deletion
    try:
        dedup_service = DeduplicateService(
            issue_repo=core.issue_service.repository,
            duplicate_detector=detector,
            backend=sync_backend,  # Include backend for remote deletion via GraphQL
        )

        response = dedup_service.execute(
            local_issues=local_issues,
            remote_issues=remote_issues,  # Include remote issues for deduplication
            dry_run=dry_run,  # Use passed parameter
        )

        elapsed = time.time() - start_time

        # Display results
        console_inst.print()
        console_inst.print("[bold cyan]✨ Deduplication Results[/bold cyan]")
        console_inst.print(f"   🗑️  Deleted: {response.duplicates_removed} duplicates")
        local_remaining = len(response.local_issues)
        remote_remaining = len(response.remote_issues)
        console_inst.print(
            f"   📊 Remaining: {local_remaining} local + {remote_remaining} remote"
        )
        if len(local_issues) + len(remote_issues) > 0:
            total_before = len(local_issues) + len(remote_issues)
            total_after = local_remaining + remote_remaining
            reduction_pct = ((total_before - total_after) / total_before) * 100
            console_inst.print(f"   📉 Reduction: {reduction_pct:.1f}%")
        console_inst.print(f"   ⏱️  Time: {elapsed:.2f}s")
        console_inst.print()
        console_inst.print("[green]✅ Deduplication complete[/green]")

    except Exception as e:
        console_inst.print(f"❌ Deduplication failed: {e}", style="bold red")
        if verbose:
            raise
        sys.exit(1)


def _execute_sync_workflow(
    core,
    console_inst,
    backend,
    baseline,
    dry_run,
    verbose,
    detect_duplicates,
    duplicate_title_threshold,
    duplicate_content_threshold,
    duplicate_auto_resolve_threshold,
    push,
    pull,
    force_local,
    force_remote,
    local_only,
    remote_only,
    milestone,
    milestone_state,
    since,
    until,
    interactive,
    show_metrics,
) -> None:
    """Execute main sync workflow."""
    # Get thresholds from config
    sync_config = core.config_service.get_sync_config()
    title_threshold = (
        duplicate_title_threshold
        if duplicate_title_threshold is not None
        else sync_config["duplicate_title_threshold"]
    )
    content_threshold = (
        duplicate_content_threshold
        if duplicate_content_threshold is not None
        else sync_config["duplicate_content_threshold"]
    )
    auto_resolve_threshold = (
        duplicate_auto_resolve_threshold
        if duplicate_auto_resolve_threshold is not None
        else sync_config["duplicate_auto_resolve_threshold"]
    )

    # Initialize sync context
    (
        backend_type,
        sync_backend,
        orchestrator,
        pre_sync_baseline,
        pre_sync_issue_count,
        state_comparator,
        conflict_resolver,
    ) = _init_sync_context(
        core,
        backend,
        baseline,
        dry_run,
        verbose,
        console_inst,
        detect_duplicates,
        title_threshold,
        content_threshold,
        auto_resolve_threshold,
    )

    # Run analysis phase
    plan, analysis_report = _run_analysis_phase(
        orchestrator,
        push,
        pull,
        dry_run,
        verbose,
        console_inst,
        interactive_duplicates=False,
    )

    # Display local-only or remote-only lists if requested
    if local_only or remote_only:
        _display_issue_lists(
            core, analysis_report, local_only, remote_only, console_inst
        )

    # Handle dry-run
    if dry_run:
        from roadmap.adapters.cli.sync_handlers.dry_run_display import (
            display_detailed_dry_run_preview,
        )

        display_detailed_dry_run_preview(
            analysis_report,
            milestone_filter=milestone,
            milestone_state=milestone_state,
            since=since,
            until=until,
            verbose=verbose,
        )
        return

    # Check if there's anything to apply
    if not _present_apply_intent(analysis_report, console_inst):
        return

    # Confirm and apply changes
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
        interactive,
    )

    # User cancelled
    if report is None:
        return

    # Finalize real sync
    _finalize_sync(
        core,
        console_inst,
        report,
        pre_sync_issue_count,
        verbose,
        backend_type,
    )
    # Display metrics if requested
    if show_metrics and hasattr(report, "metrics") and report.metrics:
        from roadmap.presentation.formatters.sync_metrics_formatter import (
            create_metrics_summary_table,
        )
        from rich.panel import Panel

        console_inst.print()
        console_inst.print(
            Panel(
                create_metrics_summary_table(report.metrics, verbose),
                title="[bold cyan]Sync Metrics[/bold cyan]",
                border_style="cyan",
            )
        )
        console_inst.print()


# Register metrics subcommand
sync.add_command(sync_metrics, name="metrics")
