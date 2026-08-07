"""Wave 3 tests for dry-run sync preview display behavior."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock

from roadmap.adapters.cli.sync_handlers.dry_run_display import (
    _determine_pull_action,
    _determine_push_action,
    _display_active_filters,
    _format_changes,
    _get_conflict_fields,
    display_detailed_dry_run_preview,
)


def _change(
    issue_id: str,
    title: str,
    *,
    local_only: bool = False,
    remote_only: bool = False,
    has_conflict: bool = False,
    field_changes: dict | None = None,
    conflicting_fields: list[str] | None = None,
):
    return SimpleNamespace(
        issue_id=issue_id,
        title=title,
        has_conflict=has_conflict,
        field_changes=field_changes or {},
        conflicting_fields=conflicting_fields or [],
        is_local_only_change=lambda: local_only,
        is_remote_only_change=lambda: remote_only,
    )


def test_display_active_filters_no_output_when_all_defaults() -> None:
    console = Mock()

    _display_active_filters(
        console,
        milestone_filter=None,
        milestone_state="all",
        since=None,
        until=None,
    )

    console.print.assert_not_called()


def test_display_active_filters_renders_all_active_values() -> None:
    console = Mock()

    _display_active_filters(
        console,
        milestone_filter=("M1", "M2"),
        milestone_state="open",
        since="2026-01-01",
        until="2026-02-01",
    )

    rendered = " ".join(str(call) for call in console.print.call_args_list)
    assert "Active Filters" in rendered
    assert "M1, M2" in rendered
    assert "State" in rendered
    assert "Since" in rendered
    assert "Until" in rendered


def test_display_detailed_dry_run_preview_handles_empty_changes(monkeypatch) -> None:
    console = Mock()
    monkeypatch.setattr(
        "roadmap.adapters.cli.sync_handlers.dry_run_display.get_console",
        lambda: console,
    )

    report = SimpleNamespace(changes=[])
    display_detailed_dry_run_preview(report)

    rendered = " ".join(str(call) for call in console.print.call_args_list)
    assert "DRY-RUN PREVIEW" in rendered
    assert "No changes detected" in rendered


def test_display_detailed_dry_run_preview_renders_push_pull_conflict_sections(
    monkeypatch,
) -> None:
    console = Mock()
    monkeypatch.setattr(
        "roadmap.adapters.cli.sync_handlers.dry_run_display.get_console",
        lambda: console,
    )

    report = SimpleNamespace(
        changes=[
            _change("A1", "Local", local_only=True),
            _change("B2", "Remote", remote_only=True),
            _change("C3", "Conflict", has_conflict=True, conflicting_fields=["status"]),
        ]
    )

    display_detailed_dry_run_preview(report, verbose=True)

    rendered = " ".join(str(call) for call in console.print.call_args_list)
    assert "PUSH Operations" in rendered
    assert "PULL Operations" in rendered
    assert "CONFLICTS Detected" in rendered
    assert "No changes will be applied" in rendered


def test_action_and_change_helpers_cover_edge_paths() -> None:
    push_create = _determine_push_action(_change("1", "t", local_only=True))
    pull_create = _determine_pull_action(_change("2", "t", remote_only=True))

    changed = _change("3", "t", field_changes={"status": ("a", "b")})
    push_update = _determine_push_action(changed)
    pull_update = _determine_pull_action(changed)

    assert "CREATE" in push_create
    assert "CREATE" in pull_create
    assert "UPDATE" in push_update
    assert "UPDATE" in pull_update
    assert _format_changes(_change("4", "t")) == "[dim]new[/dim]"
    assert _format_changes(_change("5", "t", field_changes={})) == "[dim]new[/dim]"
    assert _get_conflict_fields(_change("6", "t")) == "[dim]unknown[/dim]"
    assert _get_conflict_fields(
        _change("7", "t", conflicting_fields=["a", "b", "c", "d"])
    ).endswith("...")
