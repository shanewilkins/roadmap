"""Presentation helpers for the `roadmap sync` CLI command.

This module contains functions responsible for printing analysis results
and prompting the user for confirmation. It centralizes UI logic so that
the sync command can remain focused on orchestration.
"""

from typing import Any


from roadmap.common.console import get_console


def present_analysis(analysis_report: Any, verbose: bool = False) -> None:
    """Present a summary (and optional details) of the sync analysis.

    The function is defensive about which attributes exist on
    `analysis_report` to avoid tight coupling with concrete report classes.
    """
    console = get_console()

    console.print("\n[bold cyan]📈 Sync Analysis[/bold cyan]")
    console.print(
        f"   ✓ Up-to-date: {getattr(analysis_report, 'issues_up_to_date', 0)}"
    )
    console.print(
        f"   📤 Needs Push: {getattr(analysis_report, 'issues_needs_push', 0)}"
    )
    console.print(
        f"   📥 Needs Pull: {getattr(analysis_report, 'issues_needs_pull', 0)}"
    )
    console.print(
        f"   ✓ Potential Conflicts: {getattr(analysis_report, 'conflicts_detected', 0)}"
    )

    if verbose:
        # If the report exposes a list of changes, show a concise table-like view
        changes = getattr(analysis_report, "changes", None)
        if changes:
            console.print("\n[bold]Detailed changes:[/bold]")
            for change in changes:
                try:
                    line = f"   • {change.issue_id}: "
                    if getattr(change, "has_conflict", False):
                        line += "(CONFLICT) "
                    title = getattr(change, "title", None)
                    if title:
                        line += f"{title}"
                    console.print(line)
                except Exception as e:
                    from roadmap.common.logging import get_logger

                    logger = get_logger(__name__)
                    logger.debug(
                        "sync_change_presentation_failed",
                        error=str(e),
                        action="present_change",
                    )
                    continue
