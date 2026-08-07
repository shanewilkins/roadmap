"""Tests for sync baseline operations."""

from __future__ import annotations

import io
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from rich.console import Console

from roadmap.adapters.cli.sync_handlers.baseline_ops import (
    capture_and_save_post_sync_baseline,
    clear_baseline,
    reset_baseline,
)


def test_reset_baseline_cancelled(monkeypatch: pytest.MonkeyPatch) -> None:
    console = Mock()
    monkeypatch.setattr(
        "roadmap.adapters.cli.sync_handlers.baseline_ops.click.confirm",
        lambda *_a, **_k: False,
    )

    result = reset_baseline(
        core=SimpleNamespace(),
        backend=None,
        verbose=False,
        console_inst=console,
    )

    assert result is True
    rendered = " ".join(str(call) for call in console.print.call_args_list)
    assert "Cancelled" in rendered


def test_clear_baseline_cancelled(monkeypatch: pytest.MonkeyPatch) -> None:
    console = Mock()
    monkeypatch.setattr(
        "roadmap.adapters.cli.sync_handlers.baseline_ops.click.confirm",
        lambda *_a, **_k: False,
    )

    result = clear_baseline(
        core=SimpleNamespace(db_dir=Path("/tmp/does-not-matter")),
        backend=None,
        console_inst=console,
    )

    assert result is True
    rendered = " ".join(str(call) for call in console.print.call_args_list)
    assert "Cancelled" in rendered


def test_clear_baseline_success(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    console = Mock()
    db_dir = tmp_path
    state_db = db_dir / "state.db"
    state_db.write_text("x")

    class _Cursor:
        def execute(self, _query: str) -> None:
            return None

    class _Conn:
        def cursor(self):
            return _Cursor()

        def commit(self):
            return None

        def close(self):
            return None

    monkeypatch.setattr(
        "roadmap.adapters.cli.sync_handlers.baseline_ops.click.confirm",
        lambda *_a, **_k: True,
    )
    monkeypatch.setattr(
        "roadmap.adapters.cli.sync_handlers.baseline_ops.sqlite3.connect",
        lambda _path: _Conn(),
    )

    result = clear_baseline(
        core=SimpleNamespace(db_dir=db_dir),
        backend=None,
        console_inst=console,
    )

    assert result is True
    rendered = " ".join(str(call) for call in console.print.call_args_list)
    assert "Baseline cleared successfully" in rendered


def test_clear_baseline_oserror_exits(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    console = Mock()
    state_db = tmp_path / "state.db"
    state_db.write_text("x")

    monkeypatch.setattr(
        "roadmap.adapters.cli.sync_handlers.baseline_ops.click.confirm",
        lambda *_a, **_k: True,
    )

    def _raise(_path: str):
        raise OSError("disk problem")

    monkeypatch.setattr(
        "roadmap.adapters.cli.sync_handlers.baseline_ops.sqlite3.connect",
        _raise,
    )

    with pytest.raises(SystemExit):
        clear_baseline(
            core=SimpleNamespace(db_dir=tmp_path),
            backend=None,
            console_inst=console,
        )


def test_capture_and_save_post_sync_baseline_success() -> None:
    captured: dict = {}

    issue_a = SimpleNamespace(
        id="A-1",
        status=SimpleNamespace(value="todo"),
        assignee="sam",
        milestone="v1-0",
        headline="Head",
        content="Body",
        labels=["b", "a"],
    )

    core = SimpleNamespace(
        issues=SimpleNamespace(list_all_including_archived=lambda: [issue_a]),
        db=SimpleNamespace(
            save_sync_baseline=lambda payload: captured.update(payload) or True
        ),
    )

    result = capture_and_save_post_sync_baseline(
        core=core,
        console_inst=Console(file=io.StringIO(), force_terminal=False),
        pre_sync_issue_count=0,
        verbose=False,
    )

    assert result is True
    assert captured["A-1"]["labels"] == ["a", "b"]
    assert captured["A-1"]["status"] == "todo"


def test_capture_and_save_post_sync_baseline_save_failure_verbose_true() -> None:
    core = SimpleNamespace(
        issues=SimpleNamespace(list_all_including_archived=lambda: []),
        db=SimpleNamespace(
            save_sync_baseline=lambda _payload: (_ for _ in ()).throw(
                RuntimeError("db fail")
            )
        ),
    )

    assert (
        capture_and_save_post_sync_baseline(
            core=core,
            console_inst=Console(file=io.StringIO(), force_terminal=False),
            pre_sync_issue_count=0,
            verbose=True,
        )
        is False
    )


def test_capture_and_save_post_sync_baseline_outer_exception() -> None:
    core = SimpleNamespace(
        issues=SimpleNamespace(
            list_all_including_archived=lambda: (_ for _ in ()).throw(
                ValueError("bad data")
            )
        ),
        db=SimpleNamespace(save_sync_baseline=lambda _payload: True),
    )

    assert (
        capture_and_save_post_sync_baseline(
            core=core,
            console_inst=Console(file=io.StringIO(), force_terminal=False),
            pre_sync_issue_count=0,
            verbose=True,
        )
        is False
    )
