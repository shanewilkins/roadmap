"""Handlers and helpers extracted from `sync.py` to reduce CLI command size.

These functions encapsulate baseline display/reset, conflict viewing,
apply/present logic, and other control flow used by the `sync` command.
"""

from __future__ import annotations

import sys
from typing import Any

from rich.progress import Progress, SpinnerColumn, TextColumn
from structlog import get_logger

from roadmap.adapters.cli.services.sync_service import get_sync_backend
from roadmap.adapters.sync.sync_retrieval_orchestrator import (
    SyncRetrievalOrchestrator,
)

logger = get_logger(__name__)


def show_baseline(
    core: Any, backend: str | None, verbose: bool, console_inst: Any
) -> bool:
    """Handle the `--base` flag: show or create baseline state."""
    import yaml

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

        initial_baseline = orchestrator._create_initial_baseline()

        if initial_baseline and len(initial_baseline.issues) > 0:
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
                result = core.db.save_sync_baseline(baseline_dict)

                if result:
                    console_inst.print(
                        "\n✅ Initial baseline created and saved to database:",
                        style="bold green",
                    )
                    console_inst.print(f"   Last Sync: {initial_baseline.last_sync}")
                    console_inst.print(f"   Backend: {initial_baseline.backend}")
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


def reset_baseline(
    core: Any, backend: str | None, verbose: bool, console_inst: Any
) -> bool:
    """Handle the `--reset-baseline` flag: force recalculation of baseline."""
    import click

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

    backend_type, sync_backend = _resolve_backend_and_init(
        core, backend, get_sync_backend
    )
    if not sync_backend:
        console_inst.print("❌ Failed to initialize backend", style="bold red")
        sys.exit(1)

    _clear_baseline_db(core, console_inst)

    success = _create_and_save_baseline(
        core, sync_backend, backend_type, console_inst, verbose
    )
    if not success:
        sys.exit(1)

    return True


def capture_and_save_post_sync_baseline(
    core: Any, console_inst: Any, pre_sync_issue_count: int, verbose: bool
) -> None:
    """Capture local issues and save them as the post-sync baseline."""
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


def perform_apply_phase(
    core: Any,
    orchestrator: Any,
    console_inst: Any,
    analysis_report: Any,
    force_local: bool,
    force_remote: bool,
    push: bool,
    pull: bool,
    verbose: bool,
) -> Any:
    """Run the actual apply phase: perform sync and display summary."""
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

    console_inst.print("\n[bold cyan]✅ Sync Results[/bold cyan]")

    pushed = analysis_report.issues_needs_push
    pulled = analysis_report.issues_needs_pull

    if pushed > 0:
        console_inst.print(f"   📤 Pushed: {pushed}")
    if pulled > 0:
        console_inst.print(f"   📥 Pulled: {pulled}")

    if pushed == 0 and pulled == 0:
        console_inst.print("   ✓ Everything up-to-date")

    console_inst.print()

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


def present_apply_intent(analysis_report: Any, console_inst: Any) -> bool:
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


def confirm_and_apply(
    core: Any,
    orchestrator: Any,
    console_inst: Any,
    analysis_report: Any,
    force_local: bool,
    force_remote: bool,
    push: bool,
    pull: bool,
    verbose: bool,
) -> Any | None:
    """Ask for confirmation and run the apply phase if confirmed."""
    from roadmap.adapters.cli.sync_presenter import confirm_apply

    if not confirm_apply():
        console_inst.print("Aborting sync (user cancelled)")
        return None

    report = perform_apply_phase(
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


def finalize_sync(
    core: Any, console_inst: Any, report: Any, pre_sync_issue_count: int, verbose: bool
) -> None:
    """Finalize sync run: capture post-sync baseline and print completion messages."""
    console_inst.print("[bold]BASELINE CHANGES:[/bold]")
    console_inst.print(f"   Before: {pre_sync_issue_count} issues in baseline")

    capture_and_save_post_sync_baseline(
        core, console_inst, pre_sync_issue_count, verbose
    )

    console_inst.print()
    console_inst.print("✅ Sync completed successfully", style="bold green")


def run_analysis_phase(
    orchestrator: Any,
    push: bool,
    pull: bool,
    dry_run: bool,
    verbose: bool,
    console_inst: Any,
):
    """Run analysis phase using orchestrator and present results."""
    from roadmap.adapters.cli.sync_presenter import present_analysis

    _ = dry_run  # Reserved for future use in analysis phase
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


def clear_baseline(core: Any, backend: str | None, console_inst: Any) -> bool:
    """Handle the `--clear-baseline` flag to clear baseline without syncing."""
    import sqlite3

    import click

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


def show_conflicts(
    core: Any, backend: str | None, verbose: bool, console_inst: Any
) -> bool:
    """Handle the `--conflicts` flag to analyze and present conflicts."""
    import yaml

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


def handle_link_unlink(
    core: Any,
    backend: str | None,
    link: str | None,
    unlink: bool,
    issue_id: str | None,
    console_inst: Any,
) -> bool:
    """Handle `--link`/`--unlink` operations for manual remote ID management."""
    import yaml

    if not issue_id:
        console_inst.print(
            "❌ --issue-id is required when using --link or --unlink",
            style="bold red",
        )
        sys.exit(1)

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

    issue = core.issues.get(issue_id)

    if not issue:
        console_inst.print(
            f"❌ Issue not found: {issue_id}",
            style="bold red",
        )
        sys.exit(1)

    if link:
        if issue.remote_ids is None:
            issue.remote_ids = {}
        issue.remote_ids[backend_name] = link
        core.issues.update(issue_id, remote_ids=issue.remote_ids)
        console_inst.print(
            f"✅ Linked issue {issue_id} to {backend_name}:{link}",
            style="bold green",
        )
    elif unlink:
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


def handle_pre_sync_actions(
    core: Any,
    backend: str | None,
    base: bool,
    reset_baseline_flag: bool,
    clear_baseline_flag: bool,
    conflicts: bool,
    link: str | None,
    unlink: bool,
    issue_id: str | None,
    verbose: bool,
    console_inst: Any,
) -> bool:
    """Handle pre-sync CLI actions that may short-circuit the main sync flow.

    Returns True when an action was handled and the caller should exit.
    """
    if base:
        return show_baseline(core, backend, verbose, console_inst)

    if reset_baseline_flag:
        return reset_baseline(core, backend, verbose, console_inst)

    if clear_baseline_flag:
        return clear_baseline(core, backend, console_inst)

    if conflicts:
        return show_conflicts(core, backend, verbose, console_inst)

    if link or unlink:
        return handle_link_unlink(core, backend, link, unlink, issue_id, console_inst)

    return False
