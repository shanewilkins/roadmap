"""Tests for interactive conflict resolver UI behavior."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import Mock

import pytest

from roadmap.adapters.cli.sync_handlers.interactive_resolver import (
    InteractiveConflictResolver,
)


def test_resolve_interactively_returns_empty_for_no_conflicts() -> None:
    resolver = InteractiveConflictResolver(console=Mock())
    result = resolver.resolve_interactively([], {})
    assert result == {}


def test_resolve_interactively_skips_missing_issue() -> None:
    console = Mock()
    resolver = InteractiveConflictResolver(console=console)
    conflict = SimpleNamespace(issue_id="A-1", field_names=["status"])

    result = resolver.resolve_interactively(
        cast(Any, [conflict]),
        issues_by_id={},
    )

    assert result == {}


def test_format_value_for_display_none_and_long_text() -> None:
    resolver = InteractiveConflictResolver(console=Mock())

    assert resolver._format_value_for_display(None, "title") == "[dim]<none>[/dim]"
    formatted = resolver._format_value_for_display("x" * 60, "title")
    assert formatted.endswith("...")
    assert len(formatted) == 47


def test_is_mergeable_field_for_lists_and_known_fields() -> None:
    resolver = InteractiveConflictResolver(console=Mock())

    assert resolver._is_mergeable_field("title", ["a"], ["b"]) is True
    assert resolver._is_mergeable_field("labels", "a", "b") is True
    assert resolver._is_mergeable_field("title", "a", "b") is False


def test_get_manual_edit_cancelled(monkeypatch: pytest.MonkeyPatch) -> None:
    resolver = InteractiveConflictResolver(console=Mock())

    def _raise(*_args, **_kwargs):
        raise KeyboardInterrupt

    monkeypatch.setattr(
        "roadmap.adapters.cli.sync_handlers.interactive_resolver.Prompt.ask",
        _raise,
    )

    assert resolver._get_manual_edit("title", "local", "remote") is None


def test_show_conflict_summary_renders_manual_as_manual() -> None:
    console = Mock()
    resolver = InteractiveConflictResolver(console=console)

    conflict = SimpleNamespace(issue_id="A-1234567890", field_names=["title", "labels"])
    resolutions = {"A-1234567890": {"title": "MANUAL:new title", "labels": "LOCAL"}}

    captured_rows: list[tuple[str, str, str]] = []

    class _FakeTable:
        def __init__(self, *_args, **_kwargs):
            return None

        def add_column(self, *_args, **_kwargs):
            return None

        def add_row(self, issue_id: str, field: str, resolution: str):
            captured_rows.append((issue_id, field, resolution))

    from roadmap.adapters.cli.sync_handlers import interactive_resolver as module

    original_table = module.Table
    module.Table = _FakeTable  # type: ignore[assignment]

    try:
        resolver.show_conflict_summary(cast(Any, [conflict]), resolutions)
    finally:
        module.Table = original_table  # type: ignore[assignment]

    rendered = " ".join(str(call) for call in console.print.call_args_list)
    assert "Conflict Resolution Summary" in rendered
    assert "Resolved:" in rendered
    assert ("A-1234567890"[:12], "title", "MANUAL") in captured_rows
