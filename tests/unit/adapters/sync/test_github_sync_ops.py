"""Focused tests for GitHub sync operations behavior."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from roadmap.adapters.sync.backends.github_sync_ops import GitHubSyncOps
from roadmap.core.interfaces import SyncReport
from roadmap.core.models.sync_models import SyncIssue


def test_create_interval_defaults_and_invalid_values() -> None:
    backend_default = SimpleNamespace(config={})
    backend_valid = SimpleNamespace(
        config={"sync_settings": {"create_min_interval_seconds": "2.5"}}
    )
    backend_invalid = SimpleNamespace(
        config={"sync_settings": {"create_min_interval_seconds": "invalid"}}
    )

    assert GitHubSyncOps(backend_default)._create_min_interval_seconds == 1.0
    assert GitHubSyncOps(backend_valid)._create_min_interval_seconds == 2.5
    assert GitHubSyncOps(backend_invalid)._create_min_interval_seconds == 1.0


def test_sync_labels_enabled_reads_config_flag() -> None:
    backend_default = SimpleNamespace(config={})
    backend_disabled = SimpleNamespace(config={"sync_settings": {"sync_labels": False}})

    assert GitHubSyncOps(backend_default)._sync_labels_enabled() is True
    assert GitHubSyncOps(backend_disabled)._sync_labels_enabled() is False


def test_ensure_labels_exist_handles_missing_methods() -> None:
    backend = SimpleNamespace(config={}, get_label_client=lambda: SimpleNamespace())
    ops = GitHubSyncOps(backend)

    ops._ensure_labels_exist(["bug"])

    assert ops._label_support is False


def test_ensure_labels_exist_creates_and_caches_missing_labels() -> None:
    created: list[tuple[str, str]] = []

    class _LabelClient:
        def get_labels(self):
            return [{"name": "bug"}]

        def create_label(self, name: str, color: str) -> None:
            created.append((name, color))

    backend = SimpleNamespace(config={}, get_label_client=lambda: _LabelClient())
    ops = GitHubSyncOps(backend)

    ops._ensure_labels_exist(["bug", "feature"])
    ops._ensure_labels_exist(["feature"])

    assert created == [("feature", "CCCCCC")]
    assert ops._label_cache == {"bug", "feature"}


def test_throttle_issue_creation_waits_when_needed(monkeypatch) -> None:
    backend = SimpleNamespace(
        config={"sync_settings": {"create_min_interval_seconds": 1.0}}
    )
    ops = GitHubSyncOps(backend)
    ops._last_create_time = 9.8

    monotonic_values = iter([10.0, 11.0])
    delays: list[float] = []

    monkeypatch.setattr(
        "roadmap.adapters.sync.backends.github_sync_ops.time.monotonic",
        lambda: next(monotonic_values),
    )
    monkeypatch.setattr(
        "roadmap.adapters.sync.backends.github_sync_ops.time.sleep",
        lambda delay: delays.append(delay),
    )

    ops._throttle_issue_creation()

    assert delays == [pytest.approx(0.8, rel=1e-6)]
    assert ops._last_create_time == 11.0


@pytest.mark.parametrize(
    ("message", "expected_fragment"),
    [
        ("403 Access forbidden", "Permission denied"),
        ("410 Gone", "Remote issue deleted"),
        ("404 not found", "404 not found"),
        ("Rate limit exceeded", "Rate limited"),
        ("Validation error: invalid", "Validation error"),
    ],
)
def test_push_error_categorization(message: str, expected_fragment: str) -> None:
    backend = SimpleNamespace(config={})
    ops = GitHubSyncOps(backend)
    issue = SimpleNamespace(id="I-1")

    success, categorized = ops._handle_push_error(issue, message)

    assert success is False
    assert expected_fragment in categorized


def test_pull_error_categorization() -> None:
    backend = SimpleNamespace(config={})
    ops = GitHubSyncOps(backend)
    sync_issue = SimpleNamespace(backend_id="123")

    _, denied = ops._handle_pull_error(sync_issue, "403 Access forbidden")
    _, gone = ops._handle_pull_error(sync_issue, "410 Gone")
    _, other = ops._handle_pull_error(sync_issue, "Some other failure")

    assert "Permission denied" in denied
    assert "Remote issue deleted" in gone
    assert "Some other failure" in other


def test_link_and_resolve_paths_with_remote_links() -> None:
    linked: list[tuple[str, str, str]] = []

    class _RemoteLinks:
        def get_issue_uuid(self, backend_name: str, remote_id: str | int):
            if str(remote_id) == "77":
                return "I-77"
            return None

        def link_issue(self, issue_uuid: str, backend_name: str, remote_id: str):
            linked.append((issue_uuid, backend_name, remote_id))

    backend = SimpleNamespace(
        core=SimpleNamespace(db=SimpleNamespace(remote_links=_RemoteLinks()))
    )
    ops = GitHubSyncOps(backend)
    local_issue = SimpleNamespace(id="LOCAL-1")

    resolved = ops._resolve_local_issue_id("77", local_issue)
    linked_ok = ops._link_pulled_issue_locally(resolved, 77)

    assert resolved == "I-77"
    assert linked_ok is True
    assert linked == [("I-77", "github", "77")]


def test_analyze_dependencies_and_find_milestone_number() -> None:
    backend = SimpleNamespace(config={})
    ops = GitHubSyncOps(backend)

    remote_issue = SyncIssue(
        id="R-1",
        title="Issue",
        status="open",
        milestone="v1-0",
    )
    remote_issues = {"1": remote_issue}
    remote_milestones = {
        100: SimpleNamespace(name="v1-0"),
        200: SimpleNamespace(name="v2-0"),
    }
    report = SyncReport()

    issues_to_pull, milestones_needed, updated_report = ops._analyze_issue_dependencies(
        issue_ids=["_remote_1", "missing"],
        all_remote_issues=remote_issues,
        all_remote_milestones=remote_milestones,
        report=report,
    )

    assert len(issues_to_pull) == 1
    assert milestones_needed == {100}
    assert updated_report.errors["missing"] == "Issue not found on remote"
    assert ops._find_milestone_number("v1-0", remote_milestones) == 100
    assert ops._find_milestone_number("none", remote_milestones) is None
