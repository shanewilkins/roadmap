"""Behavior-focused tests for GitHubSyncBackend."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import MagicMock

import pytest

from roadmap.adapters.sync.backends.github_sync_backend import GitHubSyncBackend
from roadmap.core.domain.issue import Issue
from roadmap.core.interfaces import SyncConflict, SyncReport
from roadmap.core.services.sync.sync_errors import SyncErrorType


def _build_backend(config: dict | None = None) -> GitHubSyncBackend:
    repo = SimpleNamespace()
    core = SimpleNamespace(db=SimpleNamespace(remote_links=repo))
    return GitHubSyncBackend(
        core=cast(Any, core),
        config=config
        or {
            "token": "token",
            "owner": "owner",
            "repo": "repo",
        },
    )


def test_init_requires_owner_and_repo() -> None:
    with pytest.raises(ValueError, match="owner"):
        GitHubSyncBackend(core=cast(Any, SimpleNamespace()), config={"token": "abc"})


def test_authenticate_success_sets_client() -> None:
    backend = _build_backend()
    expected_client = MagicMock()
    backend.github_client = None
    cast(Any, backend)._auth_service = SimpleNamespace(
        authenticate=lambda: True,
        github_client=expected_client,
    )

    result = backend.authenticate()

    assert result.is_ok()
    assert result.unwrap() is True
    assert backend.github_client is expected_client


def test_authenticate_false_returns_auth_error() -> None:
    backend = _build_backend()
    cast(Any, backend)._auth_service = SimpleNamespace(authenticate=lambda: False)

    result = backend.authenticate()

    assert result.is_err()
    err = result.unwrap_err()
    assert err.error_type == SyncErrorType.AUTHENTICATION_FAILED


def test_authenticate_exception_returns_sync_error() -> None:
    backend = _build_backend()

    def _raise() -> bool:
        raise RuntimeError("token exploded")

    cast(Any, backend)._auth_service = SimpleNamespace(authenticate=_raise)

    result = backend.authenticate()

    assert result.is_err()
    err = result.unwrap_err()
    assert err.error_type == SyncErrorType.AUTHENTICATION_FAILED
    assert "token exploded" in err.message


def test_get_issues_requires_fetch_service_or_authenticated_client() -> None:
    backend = _build_backend({"owner": "owner", "repo": "repo"})
    backend.github_client = None
    backend._fetch_service = None

    result = backend.get_issues()

    assert result.is_err()
    err = result.unwrap_err()
    assert err.error_type == SyncErrorType.AUTHENTICATION_FAILED


def test_get_issues_uses_fetch_service_and_returns_ok(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    backend = _build_backend()
    backend.github_client = MagicMock()
    expected_issues = {"123": SimpleNamespace(id="123")}

    class _FetchService:
        def __init__(self, _client, _config, _helpers):
            pass

        def get_issues(self):
            return expected_issues

    monkeypatch.setattr(
        "roadmap.adapters.sync.backends.github_sync_backend.GitHubIssueFetchService",
        _FetchService,
    )

    result = backend.get_issues()

    assert result.is_ok()
    assert result.unwrap() == expected_issues


def test_get_issues_wraps_exception_as_network_error() -> None:
    backend = _build_backend()
    cast(Any, backend)._fetch_service = SimpleNamespace(
        get_issues=lambda: (_ for _ in ()).throw(ConnectionError("boom"))
    )

    result = backend.get_issues()

    assert result.is_err()
    err = result.unwrap_err()
    assert err.error_type == SyncErrorType.NETWORK_ERROR


def test_push_issue_success_and_failure_paths() -> None:
    backend = _build_backend()
    issue = Issue(id="A-1", title="Issue")

    success_report = SyncReport()
    success_report.pushed.append("A-1")
    backend.push_issues = lambda _issues: SimpleNamespace(  # type: ignore[method-assign]
        is_err=lambda: False,
        unwrap=lambda: success_report,
    )
    success = backend.push_issue(issue)
    assert success.is_ok()

    failed_report = SyncReport()
    failed_report.errors["A-1"] = "failed"
    backend.push_issues = lambda _issues: SimpleNamespace(  # type: ignore[method-assign]
        is_err=lambda: False,
        unwrap=lambda: failed_report,
    )
    failed = backend.push_issue(issue)
    assert failed.is_err()
    assert failed.unwrap_err().entity_id == "A-1"


@pytest.mark.parametrize(
    "issue_id,expected_ok",
    [
        ("1", True),
        ("_remote_42", True),
        ("bad-id", False),
    ],
)
def test_pull_issue_validates_issue_id(issue_id: str, expected_ok: bool) -> None:
    backend = _build_backend()

    result = backend.pull_issue(issue_id)

    assert result.is_ok() is expected_ok
    if not expected_ok:
        assert result.unwrap_err().error_type == SyncErrorType.VALIDATION_ERROR


def test_get_milestones_no_client_returns_auth_error() -> None:
    backend = _build_backend()
    backend.github_client = None

    result = backend.get_milestones()

    assert result.is_err()
    assert result.unwrap_err().error_type == SyncErrorType.AUTHENTICATION_FAILED


def test_get_milestones_returns_service_data(monkeypatch: pytest.MonkeyPatch) -> None:
    backend = _build_backend()
    backend.github_client = MagicMock()

    class _MilestoneService:
        def __init__(self, _client, _config):
            pass

        def get_milestones(self, state: str = "all"):
            return {"1": {"name": "v1-0"}, "2": {"name": "v2-0"}}

    monkeypatch.setattr(
        "roadmap.adapters.sync.backends.services.github_milestone_fetch_service.GitHubMilestoneFetchService",
        _MilestoneService,
    )

    result = backend.get_milestones()

    assert result.is_ok()
    assert len(result.unwrap()) == 2


def test_get_label_client_returns_none_without_token() -> None:
    backend = _build_backend({"owner": "owner", "repo": "repo"})
    assert backend.get_label_client() is None


def test_get_conflict_options_and_resolve_conflict() -> None:
    backend = _build_backend()
    conflict = SyncConflict(
        issue_id="A-1",
        local_version=None,
        remote_version={"id": "1"},
        conflict_type="both_modified",
    )

    assert backend.get_conflict_resolution_options(conflict) == [
        "use_local",
        "use_remote",
        "merge",
    ]
    assert backend.resolve_conflict(conflict, "merge") is True


def test_post_graphql_with_backoff_retries_rate_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    backend = _build_backend()

    payloads = iter(
        [
            {"errors": [{"type": "RESOURCE_LIMITS_EXCEEDED"}]},
            {"data": {"ok": True}},
        ]
    )
    sleep_calls: list[float] = []

    monkeypatch.setattr(
        backend,
        "_post_graphql",
        lambda *_args, **_kwargs: next(payloads),
    )
    monkeypatch.setattr(
        "roadmap.adapters.sync.backends.github_sync_backend.time.sleep",
        lambda delay: sleep_calls.append(delay),
    )

    result = backend._post_graphql_with_backoff("query", "token", "op")

    assert result == {"data": {"ok": True}}
    assert sleep_calls == [2.0]
