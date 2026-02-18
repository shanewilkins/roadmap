"""Tests for sync metrics CLI command."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock

from click.testing import CliRunner
from rich.panel import Panel

from roadmap.adapters.cli.sync_metrics_command import sync_metrics


def _core() -> SimpleNamespace:
    return SimpleNamespace(is_initialized=lambda: True, db_manager=object())


def test_sync_metrics_latest_no_data_prints_message(monkeypatch) -> None:
    console = Mock()

    class _Repo:
        def __init__(self, _db_manager):
            pass

        def get_latest(self, backend_type=None):
            return None

    monkeypatch.setattr(
        "roadmap.adapters.cli.sync_metrics_command.get_console",
        lambda: console,
    )
    monkeypatch.setattr(
        "roadmap.adapters.cli.sync_metrics_command.SyncMetricsRepository",
        _Repo,
    )

    runner = CliRunner()
    result = runner.invoke(sync_metrics, ["--latest"], obj={"core": _core()})

    assert result.exit_code == 0
    rendered = " ".join(str(call) for call in console.print.call_args_list)
    assert "No sync metrics found" in rendered


def test_sync_metrics_stats_no_syncs_prints_period_message(monkeypatch) -> None:
    console = Mock()

    class _Repo:
        def __init__(self, _db_manager):
            pass

        def get_statistics(self, backend_type=None, days=7):
            return {"total_syncs": 0}

    monkeypatch.setattr(
        "roadmap.adapters.cli.sync_metrics_command.get_console",
        lambda: console,
    )
    monkeypatch.setattr(
        "roadmap.adapters.cli.sync_metrics_command.SyncMetricsRepository",
        _Repo,
    )

    runner = CliRunner()
    result = runner.invoke(
        sync_metrics, ["--stats", "--days", "14"], obj={"core": _core()}
    )

    assert result.exit_code == 0
    rendered = " ".join(str(call) for call in console.print.call_args_list)
    assert "No sync metrics found for the specified period" in rendered


def test_sync_metrics_history_verbose_renders_details_panel(monkeypatch) -> None:
    console = Mock()
    metrics = SimpleNamespace()

    class _Repo:
        def __init__(self, _db_manager):
            pass

        def list_by_date(self, backend_type=None, days=7):
            return [metrics]

    monkeypatch.setattr(
        "roadmap.adapters.cli.sync_metrics_command.get_console",
        lambda: console,
    )
    monkeypatch.setattr(
        "roadmap.adapters.cli.sync_metrics_command.SyncMetricsRepository",
        _Repo,
    )
    monkeypatch.setattr(
        "roadmap.adapters.cli.sync_metrics_command.create_metrics_history_table",
        lambda *_args, **_kwargs: "history-table",
    )
    monkeypatch.setattr(
        "roadmap.adapters.cli.sync_metrics_command.create_metrics_summary_table",
        lambda *_args, **_kwargs: "summary-table",
    )

    runner = CliRunner()
    result = runner.invoke(sync_metrics, ["--verbose"], obj={"core": _core()})

    assert result.exit_code == 0
    assert console.print.call_count >= 3


def test_sync_metrics_latest_renders_summary_panel(monkeypatch) -> None:
    console = Mock()
    metric = SimpleNamespace()

    class _Repo:
        def __init__(self, _db_manager):
            pass

        def get_latest(self, backend_type=None):
            return metric

    monkeypatch.setattr(
        "roadmap.adapters.cli.sync_metrics_command.get_console",
        lambda: console,
    )
    monkeypatch.setattr(
        "roadmap.adapters.cli.sync_metrics_command.SyncMetricsRepository",
        _Repo,
    )
    monkeypatch.setattr(
        "roadmap.adapters.cli.sync_metrics_command.create_metrics_summary_table",
        lambda *_args, **_kwargs: "summary-table",
    )

    runner = CliRunner()
    result = runner.invoke(sync_metrics, ["--latest"], obj={"core": _core()})

    assert result.exit_code == 0
    panels = [
        arg
        for call in console.print.call_args_list
        for arg in call.args
        if isinstance(arg, Panel)
    ]
    assert any("Latest Sync Metrics" in str(panel.title) for panel in panels)


def test_sync_metrics_stats_renders_statistics_panel(monkeypatch) -> None:
    console = Mock()
    captured: dict[str, object] = {}

    class _Repo:
        def __init__(self, _db_manager):
            pass

        def get_statistics(self, backend_type=None, days=7):
            captured["backend_type"] = backend_type
            captured["days"] = days
            return {
                "total_syncs": 9,
                "avg_duration_seconds": 12.34,
                "total_duplicates_detected": 3,
                "total_conflicts_detected": 2,
                "total_errors": 1,
            }

    monkeypatch.setattr(
        "roadmap.adapters.cli.sync_metrics_command.get_console",
        lambda: console,
    )
    monkeypatch.setattr(
        "roadmap.adapters.cli.sync_metrics_command.SyncMetricsRepository",
        _Repo,
    )

    runner = CliRunner()
    result = runner.invoke(
        sync_metrics, ["--stats", "--days", "14"], obj={"core": _core()}
    )

    assert result.exit_code == 0
    panels = [
        arg
        for call in console.print.call_args_list
        for arg in call.args
        if isinstance(arg, Panel)
    ]
    assert any("Statistics (14 days)" in str(panel.title) for panel in panels)
    assert captured["backend_type"] is None
    assert captured["days"] == 14


def test_sync_metrics_history_no_data_prints_days_message(monkeypatch) -> None:
    console = Mock()

    class _Repo:
        def __init__(self, _db_manager):
            pass

        def list_by_date(self, backend_type=None, days=7):
            return []

    monkeypatch.setattr(
        "roadmap.adapters.cli.sync_metrics_command.get_console",
        lambda: console,
    )
    monkeypatch.setattr(
        "roadmap.adapters.cli.sync_metrics_command.SyncMetricsRepository",
        _Repo,
    )

    runner = CliRunner()
    result = runner.invoke(sync_metrics, ["--days", "3"], obj={"core": _core()})

    assert result.exit_code == 0
    rendered = " ".join(str(call) for call in console.print.call_args_list)
    assert "No sync metrics found in the last 3 days" in rendered


def test_sync_metrics_prints_error_when_repository_raises(monkeypatch) -> None:
    console = Mock()

    class _Repo:
        def __init__(self, _db_manager):
            raise RuntimeError("boom")

    monkeypatch.setattr(
        "roadmap.adapters.cli.sync_metrics_command.get_console",
        lambda: console,
    )
    monkeypatch.setattr(
        "roadmap.adapters.cli.sync_metrics_command.SyncMetricsRepository",
        _Repo,
    )

    runner = CliRunner()
    result = runner.invoke(sync_metrics, [], obj={"core": _core()})

    assert result.exit_code == 0
    rendered = " ".join(str(call) for call in console.print.call_args_list)
    assert "Error retrieving metrics: boom" in rendered


def test_sync_metrics_verbose_reraises_on_error(monkeypatch) -> None:
    console = Mock()

    class _Repo:
        def __init__(self, _db_manager):
            raise RuntimeError("boom")

    monkeypatch.setattr(
        "roadmap.adapters.cli.sync_metrics_command.get_console",
        lambda: console,
    )
    monkeypatch.setattr(
        "roadmap.adapters.cli.sync_metrics_command.SyncMetricsRepository",
        _Repo,
    )

    runner = CliRunner()
    result = runner.invoke(sync_metrics, ["--verbose"], obj={"core": _core()})

    assert result.exit_code != 0
    assert isinstance(result.exception, RuntimeError)
    assert str(result.exception) == "boom"
