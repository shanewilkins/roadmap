"""Wave 3 tests for sync presenter output behavior."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock

from roadmap.adapters.cli.sync_presenter import present_analysis


def test_present_analysis_renders_summary_counts(monkeypatch) -> None:
    console = Mock()
    monkeypatch.setattr(
        "roadmap.adapters.cli.sync_presenter.get_console",
        lambda: console,
    )

    report = SimpleNamespace(
        issues_up_to_date=3,
        issues_needs_push=2,
        issues_needs_pull=1,
        conflicts_detected=4,
    )

    present_analysis(report, verbose=False)

    rendered = " ".join(str(call) for call in console.print.call_args_list)
    assert "Sync Analysis" in rendered
    assert "Up-to-date: 3" in rendered
    assert "Needs Push: 2" in rendered
    assert "Needs Pull: 1" in rendered
    assert "Potential Conflicts: 4" in rendered


def test_present_analysis_verbose_renders_change_rows(monkeypatch) -> None:
    console = Mock()
    monkeypatch.setattr(
        "roadmap.adapters.cli.sync_presenter.get_console",
        lambda: console,
    )

    changes = [
        SimpleNamespace(issue_id="A1", has_conflict=True, title="Conflict issue"),
        SimpleNamespace(issue_id="B2", has_conflict=False, title="Normal issue"),
    ]
    report = SimpleNamespace(changes=changes)

    present_analysis(report, verbose=True)

    rendered = " ".join(str(call) for call in console.print.call_args_list)
    assert "Detailed changes" in rendered
    assert "A1" in rendered
    assert "CONFLICT" in rendered
    assert "B2" in rendered


def test_present_analysis_verbose_handles_bad_change_object(monkeypatch) -> None:
    console = Mock()
    logger = Mock()

    monkeypatch.setattr(
        "roadmap.adapters.cli.sync_presenter.get_console",
        lambda: console,
    )
    monkeypatch.setattr(
        "roadmap.common.logging.get_logger",
        lambda _name: logger,
    )

    class _BrokenChange:
        @property
        def issue_id(self):
            raise RuntimeError("bad attr")

    report = SimpleNamespace(changes=[_BrokenChange()])

    present_analysis(report, verbose=True)

    assert logger.debug.called
