"""Tests for the top-level sync command."""

from types import SimpleNamespace
from typing import Any
from unittest.mock import Mock

import pytest
from click.testing import CliRunner

from roadmap.adapters.cli.sync import (
    _build_local_status_breakdown,
    _build_remote_status_breakdown,
    _display_issue_lists,
    _display_local_only_issues,
    _display_remote_only_issues,
    _execute_sync_workflow,
    _handle_resume,
    sync,
)
from tests.unit.common.formatters.test_ansi_utilities import clean_cli_output


@pytest.fixture
def runner():
    """Create a Click CLI runner."""
    return CliRunner()


@pytest.fixture
def mock_core():
    """Create a mock RoadmapCore instance."""
    mock = Mock()
    mock.roadmap_dir = "/fake/roadmap"
    return mock


class TestSyncCommand:
    """Test the top-level sync command."""

    def test_sync_help(self, runner):
        """Test that sync --help works."""
        result = runner.invoke(sync, ["--help"])
        output = clean_cli_output(result.output)
        assert result.exit_code == 0
        assert "Sync roadmap with remote repository" in output
        assert "--dry-run" in output
        assert "--backend" in output

    def test_sync_help_mentions_backends(self, runner):
        """Test that help text mentions available backends."""
        result = runner.invoke(sync, ["--help"])
        output = clean_cli_output(result.output)
        assert "github" in output
        assert "git" in output

    def test_sync_help_mentions_conflict_resolution(self, runner):
        """Test that help mentions conflict resolution strategies."""
        result = runner.invoke(sync, ["--help"])
        output = clean_cli_output(result.output).lower()
        assert "conflict" in output or "three-way" in output

    def test_sync_option_force_local(self, runner):
        """Test that --force-local option exists."""
        result = runner.invoke(sync, ["--help"])
        output = clean_cli_output(result.output)
        assert "--force-local" in output

    def test_sync_option_force_remote(self, runner):
        """Test that --force-remote option exists."""
        result = runner.invoke(sync, ["--help"])
        output = clean_cli_output(result.output)
        assert "--force-remote" in output

    def test_sync_option_verbose(self, runner):
        """Test that --verbose option exists."""
        result = runner.invoke(sync, ["--help"])
        output = clean_cli_output(result.output)
        assert "--verbose" in output

    def test_sync_option_backend_override(self, runner):
        """Test that --backend option allows override."""
        result = runner.invoke(sync, ["--help"])
        output = clean_cli_output(result.output)
        assert "--backend" in output
        # Check it mentions the choices
        assert "github" in output
        assert "git" in output


def _change(
    issue_id: str,
    title: str,
    local_status: str | None = None,
    remote_status: str | None = None,
    remote_id: int | None = None,
):
    local_state = SimpleNamespace(status=local_status) if local_status else None
    remote_state: dict[str, Any] = {"status": remote_status} if remote_status else {}
    if remote_id is not None:
        remote_state["backend_id"] = remote_id

    return SimpleNamespace(
        issue_id=issue_id,
        title=title,
        local_state=local_state,
        remote_state=remote_state,
        is_local_only_change=lambda: local_status is not None,
        is_remote_only_change=lambda: remote_status is not None,
    )


def test_build_local_status_breakdown_counts_statuses():
    changes = [
        _change("A", "a", local_status="todo"),
        _change("B", "b", local_status="todo"),
    ]
    assert _build_local_status_breakdown(changes) == "todo: 2"


def test_build_remote_status_breakdown_counts_statuses():
    changes = [
        _change("A", "a", remote_status="closed"),
        _change("B", "b", remote_status="todo"),
    ]
    assert _build_remote_status_breakdown(changes) == "closed: 1, todo: 1"


def test_display_local_only_issues_prints_summary():
    console = Mock()
    _display_local_only_issues(
        [_change("A1234567", "Alpha", local_status="todo")],
        console,
    )
    assert console.print.call_count >= 3


def test_display_remote_only_issues_prints_link_counts():
    console = Mock()
    _display_remote_only_issues(
        [
            _change("ABCDEF12", "Linked", remote_status="todo", remote_id=10),
            _change("_remote_999", "Orphan", remote_status="todo", remote_id=99),
        ],
        console,
    )
    rendered = " ".join(str(call) for call in console.print.call_args_list)
    assert "Linked to local" in rendered
    assert "Orphaned" in rendered


def test_display_issue_lists_handles_empty_change_set():
    console = Mock()
    report = SimpleNamespace(changes=[])
    _display_issue_lists(
        Mock(), report, local_only=True, remote_only=False, console_inst=console
    )
    rendered = " ".join(str(call) for call in console.print.call_args_list)
    assert "No issues found" in rendered


def test_handle_resume_no_checkpoint(monkeypatch):
    console = Mock()
    core = Mock()

    class _CheckpointManager:
        def __init__(self, _core):
            pass

        def can_resume(self):
            return False, None

    monkeypatch.setattr(
        "roadmap.core.services.sync.sync_checkpoint.SyncCheckpointManager",
        _CheckpointManager,
    )

    assert _handle_resume(console, core) is False
    rendered = " ".join(str(call) for call in console.print.call_args_list)
    assert "No resumable checkpoint" in rendered


def test_handle_resume_checkpoint_cancelled(monkeypatch):
    console = Mock()
    core = Mock()
    checkpoint = SimpleNamespace(
        checkpoint_id="cp-1",
        phase="apply",
        timestamp="2026-02-17T10:00:00Z",
    )

    class _CheckpointManager:
        def __init__(self, _core):
            pass

        def can_resume(self):
            return True, checkpoint

    monkeypatch.setattr(
        "roadmap.core.services.sync.sync_checkpoint.SyncCheckpointManager",
        _CheckpointManager,
    )
    monkeypatch.setattr(
        "roadmap.adapters.cli.sync.click.confirm", lambda *_a, **_k: False
    )

    assert _handle_resume(console, core) is False
    rendered = " ".join(str(call) for call in console.print.call_args_list)
    assert "Resume cancelled" in rendered


def test_execute_sync_workflow_dry_run_displays_preview_and_returns(monkeypatch):
    console = Mock()
    pre_count = 2
    analysis_report = SimpleNamespace(changes=[])

    core = SimpleNamespace(
        config_service=SimpleNamespace(
            get_sync_config=lambda: {
                "duplicate_title_threshold": 0.9,
                "duplicate_content_threshold": 0.85,
                "duplicate_auto_resolve_threshold": 0.95,
            }
        )
    )

    monkeypatch.setattr(
        "roadmap.adapters.cli.sync._init_sync_context",
        lambda *_args, **_kwargs: (
            "github",
            SimpleNamespace(),
            SimpleNamespace(),
            SimpleNamespace(),
            pre_count,
            None,
            None,
        ),
    )
    monkeypatch.setattr(
        "roadmap.adapters.cli.sync._run_analysis_phase",
        lambda *_args, **_kwargs: (SimpleNamespace(), analysis_report),
    )

    seen = {"called": False}

    def _preview(*_args, **_kwargs):
        seen["called"] = True

    monkeypatch.setattr(
        "roadmap.adapters.cli.sync_handlers.dry_run_display.display_detailed_dry_run_preview",
        _preview,
    )

    _execute_sync_workflow(
        core,
        console,
        backend=None,
        baseline=None,
        dry_run=True,
        verbose=False,
        detect_duplicates=True,
        duplicate_title_threshold=None,
        duplicate_content_threshold=None,
        duplicate_auto_resolve_threshold=None,
        push=False,
        pull=False,
        force_local=False,
        force_remote=False,
        local_only=False,
        remote_only=False,
        milestone=(),
        milestone_state="all",
        since=None,
        until=None,
        interactive=False,
        show_metrics=False,
    )

    assert seen["called"] is True


def test_execute_sync_workflow_no_apply_intent_returns_early(monkeypatch):
    console = Mock()
    core = SimpleNamespace(
        config_service=SimpleNamespace(
            get_sync_config=lambda: {
                "duplicate_title_threshold": 0.9,
                "duplicate_content_threshold": 0.85,
                "duplicate_auto_resolve_threshold": 0.95,
            }
        )
    )

    monkeypatch.setattr(
        "roadmap.adapters.cli.sync._init_sync_context",
        lambda *_args, **_kwargs: (
            "github",
            SimpleNamespace(),
            SimpleNamespace(),
            SimpleNamespace(),
            1,
            None,
            None,
        ),
    )
    monkeypatch.setattr(
        "roadmap.adapters.cli.sync._run_analysis_phase",
        lambda *_args, **_kwargs: (SimpleNamespace(), SimpleNamespace(changes=[])),
    )
    monkeypatch.setattr(
        "roadmap.adapters.cli.sync._present_apply_intent",
        lambda *_args, **_kwargs: False,
    )

    finalize_seen = {"called": False}
    monkeypatch.setattr(
        "roadmap.adapters.cli.sync._finalize_sync",
        lambda *_args, **_kwargs: finalize_seen.__setitem__("called", True),
    )

    _execute_sync_workflow(
        core,
        console,
        backend=None,
        baseline=None,
        dry_run=False,
        verbose=False,
        detect_duplicates=True,
        duplicate_title_threshold=None,
        duplicate_content_threshold=None,
        duplicate_auto_resolve_threshold=None,
        push=False,
        pull=False,
        force_local=False,
        force_remote=False,
        local_only=False,
        remote_only=False,
        milestone=(),
        milestone_state="all",
        since=None,
        until=None,
        interactive=False,
        show_metrics=False,
    )

    assert finalize_seen["called"] is False


def test_execute_sync_workflow_show_metrics_renders_panel(monkeypatch):
    console = Mock()
    report = SimpleNamespace(metrics={"duration_seconds": 1.2}, errors={}, pushed=[])
    core = SimpleNamespace(
        config_service=SimpleNamespace(
            get_sync_config=lambda: {
                "duplicate_title_threshold": 0.9,
                "duplicate_content_threshold": 0.85,
                "duplicate_auto_resolve_threshold": 0.95,
            }
        )
    )

    monkeypatch.setattr(
        "roadmap.adapters.cli.sync._init_sync_context",
        lambda *_args, **_kwargs: (
            "github",
            SimpleNamespace(),
            SimpleNamespace(),
            SimpleNamespace(),
            1,
            None,
            None,
        ),
    )
    monkeypatch.setattr(
        "roadmap.adapters.cli.sync._run_analysis_phase",
        lambda *_args, **_kwargs: (SimpleNamespace(), SimpleNamespace(changes=[1])),
    )
    monkeypatch.setattr(
        "roadmap.adapters.cli.sync._present_apply_intent",
        lambda *_args, **_kwargs: True,
    )
    monkeypatch.setattr(
        "roadmap.adapters.cli.sync._confirm_and_apply",
        lambda *_args, **_kwargs: report,
    )
    monkeypatch.setattr(
        "roadmap.adapters.cli.sync._finalize_sync",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        "roadmap.presentation.formatters.sync_metrics_formatter.create_metrics_summary_table",
        lambda *_args, **_kwargs: "metrics-table",
    )

    _execute_sync_workflow(
        core,
        console,
        backend=None,
        baseline=None,
        dry_run=False,
        verbose=False,
        detect_duplicates=True,
        duplicate_title_threshold=None,
        duplicate_content_threshold=None,
        duplicate_auto_resolve_threshold=None,
        push=False,
        pull=False,
        force_local=False,
        force_remote=False,
        local_only=False,
        remote_only=False,
        milestone=(),
        milestone_state="all",
        since=None,
        until=None,
        interactive=False,
        show_metrics=True,
    )

    assert console.print.call_count >= 2
