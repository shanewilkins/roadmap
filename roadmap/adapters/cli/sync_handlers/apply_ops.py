"""Apply phase orchestration: apply, present, confirm, finalize."""
from __future__ import annotations

import sys
from typing import Any

from rich.progress import Progress, SpinnerColumn, TextColumn
from structlog import get_logger

logger = get_logger(__name__)


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
    console_inst.print("[bold cyan]Syncing with remote...[/bold cyan]", style="bold cyan")
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
        console_inst.print("\n[bold green]✓ Already up-to-date, no changes needed[/bold green]")
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
    from roadmap.adapters.cli.sync_handlers.baseline_ops import (
        capture_and_save_post_sync_baseline,
    )

    console_inst.print("[bold]BASELINE CHANGES:[/bold]")
    console_inst.print(f"   Before: {pre_sync_issue_count} issues in baseline")

    capture_and_save_post_sync_baseline(core, console_inst, pre_sync_issue_count, verbose)

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
