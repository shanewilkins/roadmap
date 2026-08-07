"""Wave 3 tests for conflict and manual link/unlink operations."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from roadmap.adapters.cli.sync_handlers.conflict_ops import (
    handle_link_unlink,
    show_conflicts,
)


def test_show_conflicts_exits_when_backend_init_fails(monkeypatch: pytest.MonkeyPatch):
    console = Mock()
    core = SimpleNamespace()

    monkeypatch.setattr(
        "roadmap.adapters.cli.sync_handlers.conflict_ops._resolve_backend_and_init",
        lambda *_args, **_kwargs: ("github", None),
    )

    with pytest.raises(SystemExit):
        show_conflicts(core, backend=None, verbose=False, console_inst=console)


def test_show_conflicts_renders_conflict_details(monkeypatch: pytest.MonkeyPatch):
    console = Mock()
    core = SimpleNamespace()

    conflict = SimpleNamespace(
        has_conflict=True,
        issue_id="ISSUE-1",
        title="Broken sync",
        local_changes={"status": "closed"},
        github_changes={"status": "open"},
        flagged_conflicts=["status"],
        get_conflict_description=lambda: "status mismatch",
    )
    report = SimpleNamespace(conflicts_detected=1, changes=[conflict])

    monkeypatch.setattr(
        "roadmap.adapters.cli.sync_handlers.conflict_ops._resolve_backend_and_init",
        lambda *_args, **_kwargs: ("github", object()),
    )

    class _FakeOrchestrator:
        def __init__(self, *_args, **_kwargs):
            pass

        def sync_all_issues(self, **_kwargs):
            return report

    monkeypatch.setattr(
        "roadmap.adapters.cli.sync_handlers.conflict_ops.SyncRetrievalOrchestrator",
        _FakeOrchestrator,
    )

    assert show_conflicts(core, backend=None, verbose=True, console_inst=console)

    rendered = " ".join(str(call) for call in console.print.call_args_list)
    assert "Found 1 conflict" in rendered
    assert "Full conflict info" in rendered


def test_handle_link_unlink_requires_issue_id() -> None:
    with pytest.raises(SystemExit):
        handle_link_unlink(
            core=SimpleNamespace(),
            backend=None,
            link="123",
            unlink=False,
            issue_id=None,
            console_inst=Mock(),
        )


def test_handle_link_unlink_link_and_unlink_success(tmp_path: Path) -> None:
    issue = SimpleNamespace(remote_ids={})
    issues = SimpleNamespace(get=lambda _issue_id: issue, update=Mock())
    core = SimpleNamespace(
        roadmap_dir=tmp_path,
        issues=issues,
    )
    console = Mock()

    linked = handle_link_unlink(
        core=core,
        backend="github",
        link="456",
        unlink=False,
        issue_id="ISS-1",
        console_inst=console,
    )
    assert linked is True
    assert issue.remote_ids["github"] == "456"

    unlinked = handle_link_unlink(
        core=core,
        backend="github",
        link=None,
        unlink=True,
        issue_id="ISS-1",
        console_inst=console,
    )
    assert unlinked is True
    assert "github" not in issue.remote_ids


def test_handle_link_unlink_warns_when_not_linked(tmp_path: Path) -> None:
    issue = SimpleNamespace(remote_ids={})
    core = SimpleNamespace(
        roadmap_dir=tmp_path,
        issues=SimpleNamespace(get=lambda _issue_id: issue, update=Mock()),
    )
    console = Mock()

    handle_link_unlink(
        core=core,
        backend="github",
        link=None,
        unlink=True,
        issue_id="ISS-2",
        console_inst=console,
    )

    rendered = " ".join(str(call) for call in console.print.call_args_list)
    assert "is not linked" in rendered
