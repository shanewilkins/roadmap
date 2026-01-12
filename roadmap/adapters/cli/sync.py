"""Top-level sync command - backend-agnostic interface to sync operations.

This command provides a unified interface for syncing with any backend
(GitHub, Git, etc.) without requiring the user to specify which backend.
The backend is automatically detected from configuration.
"""

import sys

import click
from rich.progress import Progress, SpinnerColumn, TextColumn
from structlog import get_logger

from roadmap.adapters.cli.helpers import require_initialized
from roadmap.common.console import get_console

logger = get_logger(__name__)


def _show_baseline(core, backend, verbose, console_inst) -> bool:
    """Handle the `--base` flag: show or create baseline state."""
    import yaml

    from roadmap.adapters.cli.services.sync_service import get_sync_backend
    from roadmap.adapters.sync.sync_retrieval_orchestrator import (
        SyncRetrievalOrchestrator,
    )

    config_file = core.roadmap_dir / "config.yaml"
    full_config: dict = {}

    if config_file.exists():
        with open(config_file) as f:
            loaded = yaml.safe_load(f)
            if isinstance(loaded, dict):
                full_config = loaded

    if backend:
        backend_type = backend.lower()
    else:
        if full_config.get("github", {}).get("sync_backend"):
            backend_type = str(full_config["github"]["sync_backend"]).lower()
        else:
            backend_type = "git"

    # Prepare config for backend
    if backend_type == "github":
        github_config = full_config.get("github", {})
        from roadmap.infrastructure.security.credentials import CredentialManager

        cred_manager = CredentialManager()  # type: ignore[call-arg]
        token = cred_manager.get_token()

        config_dict = {
            "owner": github_config.get("owner"),
            "repo": github_config.get("repo"),
            "token": token,
        }
    else:
        config_dict = {}

    sync_backend = get_sync_backend(backend_type, core, config_dict)  # type: ignore
    if not sync_backend:
        console_inst.print("❌ Failed to initialize backend", style="bold red")
        sys.exit(1)

    # Create orchestrator to get baseline
    orchestrator = SyncRetrievalOrchestrator(core, sync_backend)
    baseline_state = orchestrator.get_baseline_state()

    if baseline_state:
        console_inst.print("\n📋 Baseline State (from database):", style="bold cyan")
        console_inst.print(f"   Last Sync: {baseline_state.last_sync}")
        console_inst.print(f"   Backend: {baseline_state.backend}")
        console_inst.print(f"   Issues in baseline: {len(baseline_state.issues)}")

        if verbose and baseline_state.issues:
            console_inst.print("\n   Issues:", style="bold")
            for issue_id, issue_state in sorted(baseline_state.issues.items()):
                console_inst.print(
                    f"      {issue_id}: {issue_state.title} [{issue_state.status}]"
                )
    else:
        console_inst.print(
            "ℹ️  No baseline state found. Creating initial baseline from local state...",
            style="bold yellow",
        )

        # Create initial baseline from current local state
        initial_baseline = orchestrator._create_initial_baseline()

        if initial_baseline and len(initial_baseline.issues) > 0:
            # Convert SyncState to baseline dict for saving
            baseline_dict = {}
            for issue_id, issue_state in initial_baseline.issues.items():
                baseline_dict[issue_id] = {
                    "status": issue_state.status,
                    "assignee": issue_state.assignee,
                    "milestone": issue_state.milestone,
                    "headline": issue_state.headline,
                    "content": issue_state.content,
                    "labels": issue_state.labels,
                }

            try:
                # Use the StateManager to save baseline (properly formatted)
                result = core.db.save_sync_baseline(baseline_dict)

                if result:
                    console_inst.print(
                        "\n✅ Initial baseline created and saved to database:",
                        style="bold green",
                    )
                    console_inst.print(
                        f"   Last Sync: {initial_baseline.last_sync}",
                    )
                    console_inst.print(
                        f"   Backend: {initial_baseline.backend}",
                    )
                    console_inst.print(
                        f"   Issues in baseline: {len(initial_baseline.issues)}",
                    )

                    if verbose and initial_baseline.issues:
                        console_inst.print("\n   Issues:", style="bold")
                        for issue_id, issue_state in sorted(
                            initial_baseline.issues.items()
                        ):
                            console_inst.print(
                                f"      {issue_id}: {issue_state.title} [{issue_state.status}]"
                            )
                else:
                    console_inst.print(
                        "❌ Failed to save baseline to database",
                        style="bold red",
                    )
                    sys.exit(1)

            except Exception as e:
                console_inst.print(
                    f"❌ Failed to save baseline to database: {str(e)}",
                    style="bold red",
                )
                sys.exit(1)
        else:
            console_inst.print(
                "❌ No local issues found. Create some issues first with `roadmap create`.",
                style="bold red",
            )
    return True


def _reset_baseline(core, backend, verbose, console_inst) -> bool:
    """Handle the `--reset-baseline` flag: force recalculation of baseline."""

    from roadmap.adapters.cli.services.sync_service import get_sync_backend

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
    """Capture local issues and save them as the post-sync baseline.

    This helper isolates the baseline capture / save control flow from
    the main `sync()` command to reduce cyclomatic complexity.
    """
    try:
        baseline_dict = {}

        all_local_issues = core.issues.list_all_including_archived()

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console_inst,
            transient=True,
        ) as progress:
            task = progress.add_task(
                f"Building baseline... (0/{len(all_local_issues)})",
                total=len(all_local_issues),
            )

            for idx, issue in enumerate(all_local_issues):
                labels = issue.labels or []
                sorted_labels = sorted(labels) if labels else []

                baseline_dict[issue.id] = {
                    "status": (
                        issue.status.value
                        if hasattr(issue.status, "value")
                        else str(issue.status)
                    ),
                    "assignee": issue.assignee,
                    "milestone": issue.milestone,
                    "headline": issue.headline,
                    "content": issue.content,
                    "labels": sorted_labels,
                }

                progress.update(
                    task,
                    description=f"Building baseline... ({idx + 1}/{len(all_local_issues)})",
                    advance=1,
                )

        post_sync_issue_count = len(baseline_dict)

        try:
            result = core.db.save_sync_baseline(baseline_dict)
            if result:
                console_inst.print(
                    f"   After:  {post_sync_issue_count} issues in baseline"
                )
            if post_sync_issue_count != pre_sync_issue_count:
                diff = post_sync_issue_count - pre_sync_issue_count
                symbol = "+" if diff > 0 else ""
                console_inst.print(
                    f"   Change: {symbol}{diff} issue(s)",
                    style="green" if diff > 0 else "yellow",
                )
            if verbose:
                console_inst.print(
                    "✅ Baseline updated with post-sync state", style="dim"
                )
        except OSError as e:
            logger.error(
                "post_sync_baseline_save_exception",
                operation="save_post_sync_baseline",
                error_type=type(e).__name__,
                error=str(e),
                is_recoverable=True,
                suggested_action="check_disk_space",
            )
            if verbose:
                console_inst.print(
                    f"⚠️  Warning: Could not update baseline: {str(e)}", style="yellow"
                )
        except Exception as e:
            logger.error(
                "post_sync_baseline_save_exception",
                operation="save_post_sync_baseline",
                error_type=type(e).__name__,
                error=str(e),
                error_classification="sync_error",
            )
            if verbose:
                console_inst.print(
                    f"⚠️  Warning: Could not update baseline: {str(e)}", style="yellow"
                )
    except Exception as e:
        logger.error(
            "post_sync_baseline_capture_exception",
            operation="capture_post_sync_baseline",
            error_type=type(e).__name__,
            error=str(e),
            error_classification="sync_error",
        )
        if verbose:
            console_inst.print(
                f"⚠️  Warning: Could not update baseline: {str(e)}", style="yellow"
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
    """Run the actual apply phase: perform sync and display summary.

    Returns the sync report produced by the orchestrator.
    """
    console_inst.print(
        "[bold cyan]Syncing with remote...[/bold cyan]", style="bold cyan"
    )
    report = orchestrator.sync_all_issues(
        dry_run=False,
        force_local=force_local,
        force_remote=force_remote,
        show_progress=True,
        push_only=push,
        pull_only=pull,
    )

    if report.error:
        console_inst.print(f"\n❌ Sync error: {report.error}", style="bold red")
        sys.exit(1)

    # Display sync results with summary
    console_inst.print("\n[bold cyan]✅ Sync Results[/bold cyan]")

    # Show counts
    pushed = analysis_report.issues_needs_push
    pulled = analysis_report.issues_needs_pull

    if pushed > 0:
        console_inst.print(f"   📤 Pushed: {pushed}")
    if pulled > 0:
        console_inst.print(f"   📥 Pulled: {pulled}")

    if pushed == 0 and pulled == 0:
        console_inst.print("   ✓ Everything up-to-date")

    console_inst.print()

    # Explain the baseline concept for confused users
    if analysis_report.issues_needs_pull > 0 or analysis_report.issues_needs_push > 0:
        console_inst.print(
            "[dim]💡 Tip: The baseline is the 'agreed-upon state' from the last sync.[/dim]"
        )
        console_inst.print(
            "[dim]   After this sync completes, the baseline updates. The next sync should[/dim]"
        )
        console_inst.print(
            "[dim]   show these same issues as 'up-to-date' (all three states match).[/dim]"
        )

    return report


def _present_apply_intent(analysis_report, console_inst) -> bool:
    """Present whether there are changes to apply and return True if apply is needed."""
    if (
        analysis_report.issues_needs_push > 0
        or analysis_report.issues_needs_pull > 0
        or analysis_report.conflicts_detected > 0
    ):
        console_inst.print("\n✨ [bold cyan]Applied Changes[/bold cyan]")
        return True
    else:
        console_inst.print(
            "\n[bold green]✓ Already up-to-date, no changes needed[/bold green]"
        )
        return False


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
    """Ask for confirmation and run the apply phase if confirmed.

    Returns the apply `report` if applied, or None if cancelled.
    """
    from roadmap.adapters.cli.sync_presenter import confirm_apply

    # Ask for confirmation before applying
    if not confirm_apply():
        console_inst.print("Aborting sync (user cancelled)")
        return None

    report = _perform_apply_phase(
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

    return report


def _finalize_sync(core, console_inst, report, pre_sync_issue_count, verbose):
    """Finalize sync run: capture post-sync baseline and print completion messages."""
    # For real sync: capture and display BEFORE/AFTER
    console_inst.print("[bold]BASELINE CHANGES:[/bold]")
    console_inst.print(f"   Before: {pre_sync_issue_count} issues in baseline")

    _capture_and_save_post_sync_baseline(
        core, console_inst, pre_sync_issue_count, verbose
    )

    console_inst.print()
    console_inst.print("✅ Sync completed successfully", style="bold green")


def _run_analysis_phase(orchestrator, push, pull, dry_run, verbose, console_inst):
    """Run analysis phase using orchestrator and present results.

    Returns: tuple(plan, analysis_report)
    """
    from roadmap.adapters.cli.sync_presenter import present_analysis

    console_inst.print("\n📊 Analyzing sync status...", style="bold cyan")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console_inst,
        transient=True,
    ) as progress:
        task = progress.add_task("Comparing local, remote, and baseline...", total=None)

        plan, analysis_report = orchestrator.analyze_all_issues(
            push_only=push, pull_only=pull
        )

        progress.update(task, description="Analysis complete")

    console_inst.print("\n[bold cyan]📈 Sync Analysis[/bold cyan]")
    console_inst.print(f"   ✓ Up-to-date: {analysis_report.issues_up_to_date}")
    if push:
        console_inst.print(f"   📤 Needs Push: {analysis_report.issues_needs_push}")
    elif pull:
        console_inst.print(f"   📥 Needs Pull: {analysis_report.issues_needs_pull}")
    else:
        console_inst.print(f"   📤 Needs Push: {analysis_report.issues_needs_push}")
        console_inst.print(f"   📥 Needs Pull: {analysis_report.issues_needs_pull}")
    console_inst.print(
        f"   ✓ Potential Conflicts: {analysis_report.conflicts_detected}"
    )

    present_analysis(analysis_report, verbose=verbose)

    return plan, analysis_report


def _clear_baseline(core, backend, console_inst) -> bool:
    """Handle the `--clear-baseline` flag to clear baseline without syncing."""
    import sqlite3

    console_inst.print(
        "⚠️  WARNING: Clearing baseline will:",
        style="bold yellow",
    )
    console_inst.print("  • Delete all sync history")
    console_inst.print("  • Next sync will rebuild baseline from scratch")
    console_inst.print()

    if not click.confirm("Continue with baseline clear?"):
        console_inst.print("Cancelled.", style="dim")
        return True

    try:
        db_path = core.roadmap_dir / ".roadmap" / "db" / "state.db"
        if db_path.exists():
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            cursor.execute("DELETE FROM sync_base_state")
            conn.commit()
            conn.close()
            console_inst.print("✅ Baseline cleared successfully", style="bold green")
        else:
            console_inst.print(
                "ℹ️  No baseline file found (already empty)",
                style="dim",
            )
    except OSError as e:
        logger.error(
            "baseline_clear_failed",
            operation="clear_baseline",
            error_type=type(e).__name__,
            error=str(e),
            is_recoverable=True,
        )
        console_inst.print(
            f"❌ Failed to clear baseline: {str(e)}",
            style="bold red",
        )
        sys.exit(1)
    except Exception as e:
        logger.error(
            "baseline_clear_failed",
            operation="clear_baseline",
            error_type=type(e).__name__,
            error=str(e),
        )
        console_inst.print(
            f"❌ Failed to clear baseline: {str(e)}",
            style="bold red",
        )
        sys.exit(1)
    return True


def _show_conflicts(core, backend, verbose, console_inst) -> bool:
    """Handle the `--conflicts` flag to analyze and present conflicts."""
    import yaml

    from roadmap.adapters.cli.services.sync_service import get_sync_backend
    from roadmap.adapters.sync.sync_retrieval_orchestrator import (
        SyncRetrievalOrchestrator,
    )
    from roadmap.core.services.sync_conflict_resolver import SyncConflictResolver
    from roadmap.core.services.sync_state_comparator import SyncStateComparator

    config_file = core.roadmap_dir / "config.yaml"
    full_config: dict = {}

    if config_file.exists():
        with open(config_file) as f:
            loaded = yaml.safe_load(f)
            if isinstance(loaded, dict):
                full_config = loaded

    if backend:
        backend_type = backend.lower()
    else:
        if full_config.get("github", {}).get("sync_backend"):
            backend_type = str(full_config["github"]["sync_backend"]).lower()
        else:
            backend_type = "git"

    # Prepare config for backend
    if backend_type == "github":
        github_config = full_config.get("github", {})
        from roadmap.infrastructure.security.credentials import CredentialManager

        cred_manager = CredentialManager()  # type: ignore[call-arg]
        token = cred_manager.get_token()

        config_dict = {
            "owner": github_config.get("owner"),
            "repo": github_config.get("repo"),
            "token": token,
        }
    else:
        config_dict = {}

    sync_backend = get_sync_backend(backend_type, core, config_dict)  # type: ignore
    if not sync_backend:
        console_inst.print("❌ Failed to initialize backend", style="bold red")
        sys.exit(1)

    # Run conflict detection via dry-run
    state_comparator = SyncStateComparator()
    conflict_resolver = SyncConflictResolver()

    orchestrator = SyncRetrievalOrchestrator(
        core,
        sync_backend,
        state_comparator=state_comparator,
        conflict_resolver=conflict_resolver,
    )

    console_inst.print(
        "\n🔍 Analyzing conflicts between local, remote, and baseline...",
        style="bold cyan",
    )
    report = orchestrator.sync_all_issues(
        dry_run=True, force_local=False, force_remote=False
    )

    if report.conflicts_detected > 0:
        console_inst.print(
            f"\n⚠️  Found {report.conflicts_detected} conflict(s):",
            style="bold yellow",
        )

        for change in report.changes:
            if change.has_conflict:
                console_inst.print(
                    f"\n   📌 {change.issue_id}: {change.title}",
                    style="bold",
                )

                if change.local_changes:
                    console_inst.print(
                        f"      Local changes: {change.local_changes}",
                        style="yellow",
                    )

                if change.github_changes:
                    console_inst.print(
                        f"      Remote changes: {change.github_changes}",
                        style="blue",
                    )

                if change.flagged_conflicts:
                    console_inst.print(
                        f"      Flagged conflicts: {change.flagged_conflicts}",
                        style="bold red",
                    )

                if verbose:
                    console_inst.print(
                        f"      Full conflict info: {change.get_conflict_description()}",
                        style="dim",
                    )
    else:
        console_inst.print(
            "✅ No conflicts detected. Local and remote are in sync.",
            style="bold green",
        )

    return True


def _handle_link_unlink(core, backend, link, unlink, issue_id, console_inst) -> bool:
    """Handle `--link`/`--unlink` operations for manual remote ID management."""
    import yaml

    # Validate required --issue-id
    if not issue_id:
        console_inst.print(
            "❌ --issue-id is required when using --link or --unlink",
            style="bold red",
        )
        sys.exit(1)

    # Determine backend name
    config_file = core.roadmap_dir / "config.yaml"
    full_config: dict = {}

    if config_file.exists():
        with open(config_file) as f:
            loaded = yaml.safe_load(f)
            if isinstance(loaded, dict):
                full_config = loaded

    if backend:
        backend_name = backend.lower()
    else:
        if full_config.get("github", {}).get("sync_backend"):
            backend_name = str(full_config["github"]["sync_backend"]).lower()
        else:
            backend_name = "git"

    # Load the issue
    issue = core.issues.get(issue_id)

    if not issue:
        console_inst.print(
            f"❌ Issue not found: {issue_id}",
            style="bold red",
        )
        sys.exit(1)

    # Perform link or unlink operation
    if link:
        # Link the issue to a remote ID
        if issue.remote_ids is None:
            issue.remote_ids = {}
        issue.remote_ids[backend_name] = link
        core.issues.update(issue_id, remote_ids=issue.remote_ids)
        console_inst.print(
            f"✅ Linked issue {issue_id} to {backend_name}:{link}",
            style="bold green",
        )
    elif unlink:
        # Unlink the issue from remote
        if issue.remote_ids and backend_name in issue.remote_ids:
            del issue.remote_ids[backend_name]
            core.issues.update(issue_id, remote_ids=issue.remote_ids)
            console_inst.print(
                f"✅ Unlinked issue {issue_id} from {backend_name}",
                style="bold green",
            )
        else:
            console_inst.print(
                f"⚠️  Issue {issue_id} is not linked to {backend_name}",
                style="bold yellow",
            )

    return True


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
    """Handle pre-sync CLI actions that may short-circuit the main sync flow.

    Returns True when an action was handled and the caller should exit.
    """
    # Show baseline
    if base:
        return _show_baseline(core, backend, verbose, console_inst)

    # Reset baseline
    if reset_baseline:
        return _reset_baseline(core, backend, verbose, console_inst)

    # Clear baseline
    if clear_baseline:
        return _clear_baseline(core, backend, console_inst)

    # Show conflicts
    if conflicts:
        return _show_conflicts(core, backend, verbose, console_inst)

    # Link/unlink operations
    if link or unlink:
        return _handle_link_unlink(core, backend, link, unlink, issue_id, console_inst)

    return False


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
