"""Focused tests for GitHub backend helper behavior."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from roadmap.adapters.sync.backends.github_backend_helpers import GitHubBackendHelpers
from roadmap.core.models.sync_models import SyncIssue


def test_parse_timestamp_handles_z_suffix_and_invalid_values() -> None:
    helper = GitHubBackendHelpers(core=SimpleNamespace())

    parsed = helper._parse_timestamp("2024-01-01T10:00:00Z")
    invalid = helper._parse_timestamp("not-a-timestamp")

    assert parsed is not None
    assert parsed.tzinfo is not None
    assert invalid is None


def test_dict_to_sync_issue_maps_number_and_backend_fields() -> None:
    helper = GitHubBackendHelpers(core=SimpleNamespace())

    sync_issue = helper._dict_to_sync_issue(
        {
            "number": 77,
            "title": "Issue title",
            "state": "open",
            "body": "Description",
            "labels": ["bug"],
        }
    )

    assert sync_issue.id == "77"
    assert sync_issue.backend_name == "github"
    assert sync_issue.remote_ids["github"] == "77"


def test_convert_github_to_issue_extracts_labels_assignee_and_milestone() -> None:
    helper = GitHubBackendHelpers(core=SimpleNamespace())

    issue = helper._convert_github_to_issue(
        "L-1",
        {
            "title": "Issue",
            "state": "open",
            "body": "Body",
            "labels": [{"name": "priority:high"}, "status:todo"],
            "assignees": [{"login": "alice"}],
            "milestone": {"title": "Sprint-1"},
            "created_at": "2024-01-01T10:00:00Z",
            "updated_at": "2024-01-02T10:00:00Z",
        },
    )

    assert issue.id == "L-1"
    assert issue.assignee == "alice"
    assert issue.milestone == "Sprint-1"
    assert issue.labels == ["priority:high", "status:todo"]


def test_find_matching_local_issue_checks_remote_id_before_title_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    issue_with_remote = SimpleNamespace(
        id="A-1", remote_ids={"github": "123"}, title="A"
    )
    issue_without_remote = SimpleNamespace(id="A-2", remote_ids={}, title="B")
    core = SimpleNamespace(
        issues=SimpleNamespace(list=lambda: [issue_without_remote, issue_with_remote])
    )
    helper = GitHubBackendHelpers(core=core)

    called = {"duplicate_search": False}

    def _duplicate_search(_title: str, _backend: str, _core) -> None:
        called["duplicate_search"] = True
        return None

    monkeypatch.setattr(
        "roadmap.adapters.sync.services.SyncLinkingService.find_duplicate_by_title",
        _duplicate_search,
    )

    matched = helper._find_matching_local_issue("A", 123)

    assert matched is issue_with_remote
    assert called["duplicate_search"] is False


def test_apply_or_create_local_issue_updates_existing_match(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    updated: list[tuple[str, dict]] = []
    linked: list[tuple[str, str, int]] = []
    persisted: list[str] = []

    existing = SimpleNamespace(id="A-1", title="Existing")
    core = SimpleNamespace(
        issues=SimpleNamespace(
            update=lambda issue_id, **kwargs: updated.append((issue_id, kwargs)),
            get=lambda _issue_id: existing,
            create=lambda **_kwargs: None,
        )
    )
    helper = GitHubBackendHelpers(core=core, remote_link_repo=SimpleNamespace())

    monkeypatch.setattr(
        "roadmap.adapters.sync.services.IssuePersistenceService.update_issue_with_remote_id",
        lambda issue, backend, remote_id: persisted.append(
            f"{issue.id}:{backend}:{remote_id}"
        ),
    )
    monkeypatch.setattr(
        "roadmap.adapters.sync.services.IssuePersistenceService.save_issue",
        lambda issue, _core: persisted.append(issue.id),
    )
    monkeypatch.setattr(
        "roadmap.adapters.sync.services.SyncLinkingService.link_issue_in_database",
        lambda _repo, issue_id, backend, remote_id: linked.append(
            (issue_id, backend, remote_id)
        ),
    )

    helper._apply_or_create_local_issue(
        issue_id="A-1",
        matching_local_issue=existing,
        updates={"title": "Updated", "status": "todo", "labels": ["bug"]},
        github_issue_number=99,
        remote_issue=None,
    )

    assert updated and updated[0][0] == "A-1"
    assert linked == [("A-1", "github", 99)]
    assert persisted


def test_apply_or_create_local_issue_creates_and_links_when_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    created = SimpleNamespace(id="N-1")
    created_payloads: list[dict] = []
    linked: list[tuple[str, str, int]] = []

    core = SimpleNamespace(
        issues=SimpleNamespace(
            update=lambda *_args, **_kwargs: None,
            get=lambda _issue_id: None,
            create=lambda **kwargs: created_payloads.append(kwargs) or created,
        )
    )
    helper = GitHubBackendHelpers(core=core, remote_link_repo=SimpleNamespace())

    monkeypatch.setattr(
        "roadmap.adapters.sync.services.IssuePersistenceService.update_issue_with_remote_id",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        "roadmap.adapters.sync.services.IssuePersistenceService.save_issue",
        lambda *_args, **_kwargs: True,
    )
    monkeypatch.setattr(
        "roadmap.adapters.sync.services.SyncLinkingService.link_issue_in_database",
        lambda _repo, issue_id, backend, remote_id: linked.append(
            (issue_id, backend, remote_id)
        ),
    )

    helper._apply_or_create_local_issue(
        issue_id="N-1",
        matching_local_issue=None,
        updates={"title": "New", "content": "Body", "labels": ["enhancement"]},
        github_issue_number=101,
        remote_issue=SyncIssue(
            id="101",
            title="New",
            status="open",
            headline="Body",
            backend_id="101",
            created_at=datetime(2024, 1, 1, tzinfo=UTC),
            updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        ),
    )

    assert created_payloads
    assert linked == [("N-1", "github", 101)]
