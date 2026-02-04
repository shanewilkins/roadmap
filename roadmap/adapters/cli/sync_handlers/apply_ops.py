"""Apply phase orchestration: apply, present, confirm, finalize."""

from __future__ import annotations

import sys
from collections import Counter
from typing import Any

from rich.progress import Progress, SpinnerColumn, TextColumn
from structlog import get_logger

logger = get_logger(__name__)


def categorize_sync_errors(errors: dict[str, str]) -> dict[str, list[str]]:
    """Categorize errors by type.

    Args:
        errors: Dict of issue_id -> error message

    Returns:
        Dict of error_type -> list of issue_ids
    """
    categorized = {}

    for issue_id, error_msg in errors.items():
        if "Permission denied" in error_msg or "Access forbidden" in error_msg:
            category = "permission_denied"
        elif "Resource has been deleted" in error_msg or "Gone" in error_msg:
            category = "resource_deleted"
        elif "not found" in error_msg.lower() or "not exist" in error_msg.lower():
            category = "not_found"
        elif "Rate limit" in error_msg:
            category = "rate_limited"
        elif "Validation error" in error_msg:
            category = "validation_error"
        else:
            category = "other"

        if category not in categorized:
            categorized[category] = []
        categorized[category].append(issue_id)

    return categorized


def display_error_summary(errors: dict[str, str], console_inst: Any) -> None:
    """Display a user-friendly error summary with fix suggestions.

    Args:
        errors: Dict of issue_id -> error message
        console_inst: Rich console instance
    """
    if not errors:
        return

    console_inst.print("\n[bold yellow]⚠️  Sync Errors[/bold yellow]")

    categorized = categorize_sync_errors(errors)

    for category, issue_ids in categorized.items():
        count = len(issue_ids)

        if category == "permission_denied":
            console_inst.print(
                f"[yellow]  • Permission Denied ({count} issues)[/yellow]"
            )
            console_inst.print(
                "[dim]    Fix: Regenerate GitHub token with 'repo' scope (repo:write access)[/dim]"
            )

        elif category == "resource_deleted":
            console_inst.print(
                f"[yellow]  • Resource Deleted ({count} issues)[/yellow]"
            )
            console_inst.print(
                "[dim]    Fix: These issues were deleted on GitHub. They were skipped.[/dim]"
            )

        elif category == "not_found":
            console_inst.print(
                f"[yellow]  • Resource Not Found ({count} issues)[/yellow]"
            )
            console_inst.print(
                "[dim]    Fix: Check that the remote repository still exists.[/dim]"
            )

        elif category == "rate_limited":
            console_inst.print(f"[yellow]  • Rate Limited ({count} issues)[/yellow]")
            console_inst.print(
                "[dim]    Fix: Wait a bit and try again. GitHub allows 60 requests/hour for unauthenticated, 5000/hour for authenticated.[/dim]"
            )

        elif category == "validation_error":
            console_inst.print(
                f"[yellow]  • Validation Error ({count} issues)[/yellow]"
            )
            console_inst.print(
                "[dim]    Fix: Check issue data (title, description, etc.) for invalid values.[/dim]"
            )

        else:
            console_inst.print(f"[yellow]  • Other Error ({count} issues)[/yellow]")
            console_inst.print(
                "[dim]    Fix: Check logs for more details using verbose mode.[/dim]"
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
        push_only=push,
        pull_only=pull,
    )

    if report.error:
        console_inst.print(f"\n❌ Sync error: {report.error}", style="bold red")
        sys.exit(1)

    # Display error summary BEFORE sync results
    if report.errors:
        display_error_summary(report.errors, console_inst)
        console_inst.print()

    console_inst.print("[bold cyan]✅ Sync Results[/bold cyan]")

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
