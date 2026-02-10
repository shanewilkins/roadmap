"""Apply phase orchestration: apply, present, confirm, finalize."""

from __future__ import annotations

import sys
from typing import Any

from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from structlog import get_logger

from roadmap.core.services.sync.error_classification import ErrorClassifier

logger = get_logger(__name__)


def display_error_summary(
    errors: dict[str, str], console_inst: Any, verbose: bool = False
) -> None:
    """Display a user-friendly error summary with fix suggestions using ErrorClassifier.

    Args:
        errors: Dict of issue_id -> error message
        console_inst: Rich console instance
        verbose: If True, show detailed error info including affected issue IDs
    """
    if not errors:
        return

    # Use ErrorClassifier to categorize errors
    classifier = ErrorClassifier()
    classifier.add_errors(errors)
    summary = classifier.get_summary_dict()

    if not summary or sum(summary.values()) == 0:
        return

    console_inst.print("\n[bold yellow]⚠️  Sync Errors[/bold yellow]")
    console_inst.print(
        f"[dim]Total errors: {sum(summary.values())} across {len(errors)} issues[/dim]\n"
    )

    # Map categories to display names, icons, and colors
    category_display = {
        "dependency_errors": ("🔗 Dependency Errors", "yellow"),
        "api_errors": ("🌐 API Errors", "yellow"),
        "auth_errors": ("🔒 Authentication Errors", "red"),
        "data_errors": ("💾 Data Errors", "yellow"),
        "resource_errors": ("📦 Resource Errors", "yellow"),
        "file_system_errors": ("📁 File System Errors", "yellow"),
        "unknown_errors": ("❓ Unknown Errors", "yellow"),
    }

    for category, count in summary.items():
        if count == 0:
            continue

        display_name, color = category_display.get(
            category, (category.replace("_", " ").title(), "yellow")
        )
        console_inst.print(f"[{color}]  • {display_name} ({count})[/{color}]")

        # Get recommendation for this category
        recommendation = classifier.get_recommendation(category)
        if recommendation:
            console_inst.print(f"[dim]    Fix: {recommendation}[/dim]")

        # In verbose mode, show affected issue IDs and their error messages
        if verbose:
            affected_issues = classifier.get_issues_by_category(category)
            if affected_issues:
                console_inst.print("[dim]    Affected issues:[/dim]")
                for issue_id in affected_issues[:5]:  # Show first 5 examples
                    error_msg = errors.get(issue_id, "Unknown error")
                    # Truncate long error messages
                    if len(error_msg) > 80:
                        error_msg = error_msg[:77] + "..."
                    console_inst.print(
                        f"[dim]      - {issue_id[:8]}: {error_msg}[/dim]"
                    )
                if len(affected_issues) > 5:
                    console_inst.print(
                        f"[dim]      ... and {len(affected_issues) - 5} more[/dim]"
                    )
        console_inst.print()  # Add blank line between categories


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
    # Create progress spinner for sync operation
    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        TimeElapsedColumn(),
        console=console_inst,
    ) as progress:
        progress.add_task("Syncing with remote...", total=None)

        report = orchestrator.sync_all_issues(
            dry_run=False,
            force_local=force_local,
            force_remote=force_remote,
            push_only=push,
            pull_only=pull,
        )

    if report.error:
        console_inst.print(f"\n❌ Sync error: {report.error}", style="bold red")
        sys.exit(1)

    # Display error summary BEFORE sync results
    if report.errors:
        display_error_summary(report.errors, console_inst, verbose)
        console_inst.print()

    console_inst.print("[bold cyan]✅ Sync Results[/bold cyan]")

    pushed = report.issues_pushed
    pulled = report.issues_pulled

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
    interactive: bool = False,
) -> Any | None:
    """Run the apply phase with optional interactive conflict resolution."""
    # If interactive mode and there are conflicts, resolve them first
    if interactive and analysis_report.conflicts_detected > 0:
        from roadmap.adapters.cli.sync_handlers.interactive_resolver import (
            InteractiveConflictResolver,
        )

        console_inst.print(
            f"\n[bold yellow]⚠️  {analysis_report.conflicts_detected} conflicts detected[/bold yellow]"
        )
        console_inst.print("[dim]Entering interactive resolution mode...[/dim]\n")

        # Collect conflicts from analysis report
        conflicts = []
        issues_by_id = {}

        for change in analysis_report.changes:
            if change.has_conflict:
                # Build issues_by_id mapping
                if change.local_state:
                    issues_by_id[change.issue_id] = change.local_state

                # Create conflict object (simplified for now)
                # In a real implementation, you'd extract the actual Conflict objects
                # from the orchestrator or conflict resolver
                console_inst.print(
                    f"[dim]Conflict on issue: {change.issue_id} - {change.title}[/dim]"
                )

        # If we have conflicts to resolve interactively
        if conflicts:
            resolver = InteractiveConflictResolver(console_inst)
            resolutions = resolver.resolve_interactively(conflicts, issues_by_id)

            # Apply resolutions
            # This would integrate with the orchestrator's conflict resolver
            # to apply the chosen resolutions
            resolver.show_conflict_summary(conflicts, resolutions)

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


def _display_sync_metrics(console_inst: Any, metrics: dict[str, Any]) -> None:
    """Display formatted sync metrics summary.

    Args:
        console_inst: Rich console instance
        metrics: Dictionary of metrics from SyncMetrics.to_dict()
    """
    from rich.table import Table

    console_inst.print("\n[bold cyan]📊 Sync Metrics[/bold cyan]")

    # Create main metrics table
    table = Table(show_header=True, header_style="bold")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    # Extract and format key metrics
    def format_time(seconds: float | int) -> str:
        """Format seconds into readable time string."""
        if isinstance(seconds, (int, float)) and seconds > 0:
            if seconds < 1:
                return f"{seconds * 1000:.0f}ms"
            return f"{seconds:.2f}s"
        return "N/A"

    def format_count(count: int | None) -> str:
        """Format count or return N/A."""
        return str(count) if count is not None else "N/A"

    # Deduplication metrics
    if metrics.get("duplicates_detected"):
        table.add_row(
            "Duplicates Detected",
            format_count(metrics.get("duplicates_detected")),
        )
    if metrics.get("duplicates_resolved"):
        table.add_row(
            "Duplicates Resolved",
            format_count(metrics.get("duplicates_resolved")),
        )

    # Local dedup metrics
    if metrics.get("local_dedup_count"):
        reduction_pct = (
            (
                metrics.get("local_dedup_count", 0)
                / (
                    metrics.get("local_dedup_count", 0)
                    + metrics.get("local_final_count", 1)
                )
            )
            * 100
            if (
                metrics.get("local_dedup_count", 0)
                + metrics.get("local_final_count", 1)
            )
            > 0
            else 0
        )
        table.add_row(
            "Local Dedup Reduction",
            f"{metrics.get('local_dedup_count')} duplicates "
            f"({reduction_pct:.1f}% reduction)",
        )

    # Remote dedup metrics
    if metrics.get("remote_dedup_count"):
        reduction_pct = (
            (
                metrics.get("remote_dedup_count", 0)
                / (
                    metrics.get("remote_dedup_count", 0)
                    + metrics.get("remote_final_count", 1)
                )
            )
            * 100
            if (
                metrics.get("remote_dedup_count", 0)
                + metrics.get("remote_final_count", 1)
            )
            > 0
            else 0
        )
        table.add_row(
            "Remote Dedup Reduction",
            f"{metrics.get('remote_dedup_count')} duplicates "
            f"({reduction_pct:.1f}% reduction)",
        )

    # Timing metrics
    if metrics.get("total_duration_seconds"):
        table.add_row(
            "Total Duration",
            format_time(metrics.get("total_duration_seconds", 0)),
        )

    # Fetch metrics
    if metrics.get("total_fetch_time_seconds"):
        table.add_row(
            "Fetch Time",
            format_time(metrics.get("total_fetch_time_seconds", 0)),
        )

    # Conflict metrics
    if metrics.get("merge_conflicts_found"):
        table.add_row(
            "Merge Conflicts",
            format_count(metrics.get("merge_conflicts_found")),
        )

    # API call metrics
    if metrics.get("api_calls_made"):
        table.add_row(
            "API Calls",
            format_count(metrics.get("api_calls_made")),
        )

    if metrics.get("api_rate_limit_remaining") is not None:
        table.add_row(
            "API Rate Limit Remaining",
            format_count(metrics.get("api_rate_limit_remaining")),
        )

    console_inst.print(table)


def finalize_sync(
    core: Any,
    console_inst: Any,
    report: Any,
    pre_sync_issue_count: int,
    verbose: bool,
    backend_type: str | None = None,
) -> None:
    """Finalize sync run: capture post-sync baseline and print completion messages."""
    from roadmap.adapters.cli.sync_handlers.baseline_ops import (
        capture_and_save_post_sync_baseline,
    )

    console_inst.print("[bold]BASELINE CHANGES:[/bold]")
    console_inst.print(f"   Before: {pre_sync_issue_count} issues in baseline")

    baseline_updated = capture_and_save_post_sync_baseline(
        core, console_inst, pre_sync_issue_count, verbose
    )
    if hasattr(report, "baseline_update_failed"):
        report.baseline_update_failed = not baseline_updated

    if (
        backend_type
        and backend_type.lower() == "github"
        and getattr(report, "issues_pulled", 0) > 0
    ):
        try:
            db = getattr(core, "db", None)
            roadmap_dir = getattr(core, "roadmap_dir", None)
            if db and roadmap_dir:
                sync_result = db.sync_directory_incremental(roadmap_dir)
                synced = sync_result.get("files_synced", 0)
                console_inst.print(f"[dim]DB cache sync: {synced} file(s) synced[/dim]")
            else:
                logger.warning(
                    "post_sync_db_cache_skipped",
                    reason="missing_db_or_path",
                    has_db=bool(db),
                    has_roadmap_dir=bool(roadmap_dir),
                    severity="operational",
                )
        except Exception as e:
            logger.warning(
                "post_sync_db_cache_failed",
                error=str(e),
                error_type=type(e).__name__,
                severity="operational",
            )

        try:
            from roadmap.adapters.cli.sync_context import _repair_remote_links

            backend_name = str(backend_type)
            _repair_remote_links(core, console_inst, backend_name, dry_run=False)
        except Exception as e:
            logger.warning(
                "post_sync_remote_link_repair_failed",
                error=str(e),
                error_type=type(e).__name__,
                severity="operational",
            )

    # Save and display sync metrics if available in report
    if hasattr(report, "metrics") and report.metrics:
        # Save metrics to database
        try:
            from roadmap.adapters.persistence.sync_metrics_repository import (
                SyncMetricsRepository,
            )

            db_manager = getattr(core, "db_manager", None)
            if db_manager is None and hasattr(core, "db"):
                db_manager = getattr(core.db, "_db_manager", None)
            if db_manager is None:
                raise AttributeError("No database manager available")
            metrics_repo = SyncMetricsRepository(db_manager)
            metrics_repo.save(report.metrics)
        except Exception as e:
            logger.warning(
                "failed_to_save_sync_metrics",
                error=str(e),
                severity="operational",
            )

        # Display metrics
        metrics_dict = (
            report.metrics.to_dict()
            if hasattr(report.metrics, "to_dict")
            else report.metrics
        )
        _display_sync_metrics(console_inst, metrics_dict)

    console_inst.print()
    console_inst.print("✅ Sync completed successfully", style="bold green")


def run_analysis_phase(
    orchestrator: Any,
    push: bool,
    pull: bool,
    dry_run: bool,
    verbose: bool,
    console_inst: Any,
    interactive_duplicates: bool = False,
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
            push_only=push,
            pull_only=pull,
            interactive_duplicates=interactive_duplicates,
        )

        progress.update(task, description="Analysis complete")

    present_analysis(analysis_report, verbose=verbose)

    return plan, analysis_report
