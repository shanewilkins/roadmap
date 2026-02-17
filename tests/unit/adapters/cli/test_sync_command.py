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
