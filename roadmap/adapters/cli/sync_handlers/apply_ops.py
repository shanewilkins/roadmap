"""Apply phase orchestration: apply, present, confirm, finalize."""

from __future__ import annotations

import sys
from typing import Any

from rich.progress import Progress, SpinnerColumn, TextColumn
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
                console_inst.print(f"[dim]    Affected issues:[/dim]")
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
    console_inst.print(
        "[bold cyan]Syncing with remote...[/bold cyan]", style="bold cyan"
    )
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
) -> Any | None:
    """Run the apply phase without confirmation."""
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
    from roadmap.adapters.cli.sync_handlers.baseline_ops import (
        capture_and_save_post_sync_baseline,
    )

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

    present_analysis(analysis_report, verbose=verbose)

    return plan, analysis_report
