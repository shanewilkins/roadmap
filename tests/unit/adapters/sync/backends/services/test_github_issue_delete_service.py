"""Unit tests for GitHubIssueDeleteService behavior."""

from __future__ import annotations

from typing import Any

import pytest

from roadmap.adapters.sync.backends.services.github_issue_delete_service import (
    GitHubIssueDeleteService,
)


def _service(config: dict[str, Any] | None = None) -> GitHubIssueDeleteService:
    return GitHubIssueDeleteService(config or {})


def test_get_delete_issue_config_requires_fields() -> None:
    service = _service({"token": "t", "owner": "o"})

    assert service.get_delete_issue_config() is None


def test_get_delete_issue_config_returns_string_tuple() -> None:
    service = _service({"token": 1, "owner": 2, "repo": 3})

    assert service.get_delete_issue_config() == ("1", "2", "3")


def test_post_graphql_with_backoff_retries_on_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = _service()
    payloads = iter([None, {"data": {"ok": True}}])
    sleep_calls: list[float] = []

    monkeypatch.setattr(
        "roadmap.adapters.sync.backends.services.github_issue_delete_service.time.sleep",
        lambda delay: sleep_calls.append(delay),
    )

    result = service.post_graphql_with_backoff(
        "query",
        "token",
        "op",
        post_graphql_fn=lambda *_args, **_kwargs: next(payloads),
    )

    assert result == {"data": {"ok": True}}
    assert sleep_calls == [2.0]


def test_post_graphql_with_backoff_retries_rate_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = _service()
    payloads = iter(
        [
            {"errors": [{"type": "RESOURCE_LIMITS_EXCEEDED"}]},
            {"data": {"ok": True}},
        ]
    )
    sleep_calls: list[float] = []

    monkeypatch.setattr(
        "roadmap.adapters.sync.backends.services.github_issue_delete_service.time.sleep",
        lambda delay: sleep_calls.append(delay),
    )

    result = service.post_graphql_with_backoff(
        "query",
        "token",
        "op",
        post_graphql_fn=lambda *_args, **_kwargs: next(payloads),
    )

    assert result == {"data": {"ok": True}}
    assert sleep_calls == [2.0]


def test_extract_graphql_error_helpers() -> None:
    payload = {
        "errors": [
            {"type": "RESOURCE_LIMITS_EXCEEDED", "path": ["a"], "message": "x"},
            {"type": "OTHER", "path": ["b"], "message": "y"},
            "skip-me",
        ]
    }

    assert GitHubIssueDeleteService.extract_graphql_error_types(payload) == {
        "RESOURCE_LIMITS_EXCEEDED",
        "OTHER",
    }
    assert GitHubIssueDeleteService.extract_graphql_error_details(payload) == [
        {"type": "RESOURCE_LIMITS_EXCEEDED", "path": ["a"], "message": "x"},
        {"type": "OTHER", "path": ["b"], "message": "y"},
    ]


def test_resolve_issue_node_ids_splits_issue_and_pull_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = _service()
    response = {
        "data": {
            "issue0": {
                "issueOrPullRequest": {
                    "__typename": "Issue",
                    "id": "NODE1",
                    "number": 1,
                }
            },
            "issue1": {
                "issueOrPullRequest": {
                    "__typename": "PullRequest",
                    "id": "NODE2",
                    "number": 2,
                }
            },
            "issue2": {"issueOrPullRequest": None},
        }
    }

    monkeypatch.setattr(
        service,
        "post_graphql_with_backoff",
        lambda *_args, **_kwargs: response,
    )

    node_ids, skipped_prs = service.resolve_issue_node_ids(
        [1, 2, 3],
        "owner",
        "repo",
        "token",
    )

    assert node_ids == {1: "NODE1"}
    assert skipped_prs == [2]


def test_delete_issues_batch_reports_failures_and_rate_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = _service()
    payload = {
        "data": {"delete0": {"clientMutationId": None}, "delete1": None},
        "errors": [{"type": "RESOURCE_LIMITS_EXCEEDED", "message": "limit"}],
    }

    monkeypatch.setattr(
        service,
        "post_graphql_with_backoff",
        lambda *_args, **_kwargs: payload,
    )

    deleted, rate_limited, failed = service.delete_issues_batch(
        {10: "N10", 11: "N11"},
        "token",
    )

    assert deleted == 1
    assert rate_limited is True
    assert failed == [11]


def test_retry_failed_rate_limited_deletes_retries_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = _service()
    calls: list[dict[int, str]] = []
    sleep_calls: list[float] = []

    monkeypatch.setattr(
        service,
        "delete_issues_batch",
        lambda node_ids, _token: calls.append(node_ids) or (2, False, []),
    )
    monkeypatch.setattr(
        "roadmap.adapters.sync.backends.services.github_issue_delete_service.time.sleep",
        lambda delay: sleep_calls.append(delay),
    )

    retried_deleted = service.retry_failed_rate_limited_deletes(
        failed_numbers=[2, 3],
        rate_limited=True,
        node_ids={1: "N1", 2: "N2", 3: "N3"},
        token="token",
        rate_limit_delay_seconds=1.5,
    )

    assert retried_deleted == 2
    assert calls == [{2: "N2", 3: "N3"}]
    assert sleep_calls == [1.5]
