"""Sync command handlers: facade re-exporting all handler functions.

This package organizes sync command handlers by category:
- baseline_ops: baseline state operations (show, reset, clear, capture)
- conflict_ops: conflict detection and manual link/unlink operations
- apply_ops: apply phase orchestration and finalization
"""

from roadmap.adapters.cli.sync_handlers.apply_ops import (
    confirm_and_apply,
    finalize_sync,
    perform_apply_phase,
    present_apply_intent,
    run_analysis_phase,
)
from roadmap.adapters.cli.sync_handlers.baseline_ops import (
    capture_and_save_post_sync_baseline,
    clear_baseline,
    reset_baseline,
    show_baseline,
)
from roadmap.adapters.cli.sync_handlers.conflict_ops import (
    handle_link_unlink,
    show_conflicts,
)

__all__ = [
    # Apply operations
    "perform_apply_phase",
    "present_apply_intent",
    "confirm_and_apply",
    "finalize_sync",
    "run_analysis_phase",
    # Baseline operations
    "show_baseline",
    "reset_baseline",
    "clear_baseline",
    "capture_and_save_post_sync_baseline",
    # Conflict operations
    "show_conflicts",
    "handle_link_unlink",
]


def handle_pre_sync_actions(
    core,
    backend,
    base: bool,
    reset_baseline_flag: bool,
    clear_baseline_flag: bool,
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
