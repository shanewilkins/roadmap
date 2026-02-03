"""Three-way merge helpers for building IssueChange objects.

This module provides a single helper that constructs an `IssueChange` using
callable dependencies passed in from `SyncStateComparator`. Keeping the
implementation here makes it easier to unit-test the three-way logic in
isolation while the comparator remains a thin facade.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from roadmap.core.services.sync.sync_report import IssueChange
from roadmap.core.services.sync.sync_state import IssueBaseState


def build_issue_change(
    issue_id: str,
    local: Any | None,
    remote: Any | None,
    baseline: IssueBaseState | None,
    *,
    resolve_title: Callable[[str, Any, Any, Any], str],
    normalize_remote_state: Callable[[Any], dict | None],
    compute_changes: Callable[[Any, Any], dict],
    compute_changes_remote: Callable[[Any, Any], dict],
    handle_first_sync_semantics: Callable[[IssueChange, Any, Any, Any], None],
    detect_and_flag_conflicts: Callable[[IssueChange, Any, Any], None],
    extract_timestamp: Callable[[Any, str], Any],
    fields_to_sync: list[str],
    logger: Any | None = None,
) -> IssueChange:
    """Construct an IssueChange for a single issue using three-way context.

    Most of the behavior is the same as the old `_build_issue_change` on
    `SyncStateComparator` but extracted to allow focused testing. The helper
    depends on several callables passed in from the comparator to avoid
    duplicating logic or breaking encapsulation.
    """
    title = resolve_title(issue_id, local, remote, baseline)
    change = IssueChange(issue_id=issue_id, title=title)
    change.baseline_state = baseline
    change.local_state = local

    remote_state = normalize_remote_state(remote)
    change.remote_state = remote_state

    change.local_changes = compute_changes(baseline, local) if local is not None else {}
    change.remote_changes = (
        compute_changes_remote(baseline, remote_state)
        if remote_state is not None
        else {}
    )

    if baseline is None:
        handle_first_sync_semantics(change, local, remote_state, baseline)
    else:
        detect_and_flag_conflicts(change, local, remote_state)

        if change.local_changes and change.remote_changes:
            change.conflict_type = "both_changed"
            change.has_conflict = True
        elif change.local_changes:
            change.conflict_type = "local_only"
        elif change.remote_changes:
            change.conflict_type = "remote_only"
        else:
            change.conflict_type = "no_change"

    last_sync = None
    if baseline is not None and getattr(baseline, "updated_at", None):
        last_sync = baseline.updated_at
    elif remote is not None:
        last_sync = extract_timestamp(remote, "updated_at")
    change.last_sync_time = last_sync

    return change
