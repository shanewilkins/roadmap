"""Unit tests for GitHubLocalIssueSyncService behavior."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from roadmap.adapters.sync.backends.services.github_local_issue_sync_service import (
    GitHubLocalIssueSyncService,
)


def _build_service(backend: Any) -> GitHubLocalIssueSyncService:
    return GitHubLocalIssueSyncService(backend)


def test_persist_issue_before_linking_creates_missing_issue() -> None:
    created_payload: dict[str, Any] | None = None

    class _IssueRepo:
        def get(self, _issue_id: str):
            return None

        def create(self, payload: dict[str, Any]) -> None:
            nonlocal created_payload
            created_payload = payload

    backend = SimpleNamespace(
        core=SimpleNamespace(
            db=SimpleNamespace(get_issue_repository=lambda: _IssueRepo())
        )
    )
    service = _build_service(backend)
    issue = SimpleNamespace(
        title="Issue",
        headline="Head",
        content="Body",
        status="todo",
        priority="medium",
        type="feature",
        assignee="sam",
        estimated_hours=2.0,
    )

    result = service.persist_issue_before_linking(issue, "I-1")

    assert result is True
    assert created_payload is not None
    assert created_payload["id"] == "I-1"
    assert created_payload["title"] == "Issue"


def test_link_issue_to_github_returns_error_tuple_on_failure() -> None:
    class _RemoteLinks:
        def link_issue(self, **_kwargs):
            raise RuntimeError("db down")

    backend = SimpleNamespace(
        core=SimpleNamespace(db=SimpleNamespace(remote_links=_RemoteLinks()))
    )
    service = _build_service(backend)

    success, error = service.link_issue_to_github("I-1", 10)

    assert success is False
    assert error == "db down"


def test_get_project_id_for_synced_issue_first_project() -> None:
    projects = [SimpleNamespace(id="P-1"), SimpleNamespace(id="P-2")]
    backend = SimpleNamespace(
        core=SimpleNamespace(projects=SimpleNamespace(list=lambda: projects))
    )
    service = _build_service(backend)

    assert service.get_project_id_for_synced_issue() == "P-1"


def test_resolve_local_issue_id_prefers_remote_link() -> None:
    class _RemoteLinks:
        def get_issue_uuid(self, backend_name: str, remote_id: str | int):
            if backend_name == "github" and str(remote_id) == "22":
                return "I-22"
            return None

    backend = SimpleNamespace(
        core=SimpleNamespace(db=SimpleNamespace(remote_links=_RemoteLinks()))
    )
    service = _build_service(backend)
    local_issue = SimpleNamespace(id="I-local")

    assert service.resolve_local_issue_id("22", local_issue) == "I-22"


def test_create_or_update_issue_locally_updates_existing_issue() -> None:
    updates_seen: list[tuple[str, dict[str, Any]]] = []

    class _IssueRepo:
        def get(self, issue_id: str):
            if issue_id == "I-1":
                return {"project_id": "P-9"}
            return None

        def update(self, issue_id: str, updates: dict[str, Any]) -> None:
            updates_seen.append((issue_id, updates))

        def create(self, _issue_data: dict[str, Any]) -> None:
            raise AssertionError("create should not be called")

    backend = SimpleNamespace(
        core=SimpleNamespace(
            db=SimpleNamespace(
                get_issue_repository=lambda: _IssueRepo(),
                remote_links=SimpleNamespace(get_issue_uuid=lambda **_kwargs: "I-1"),
            )
        )
    )
    service = _build_service(backend)
    local_issue = SimpleNamespace(
        id="I-local",
        title="Title",
        headline="Headline",
        content="Body",
        status="todo",
        priority="medium",
        issue_type="feature",
        assignee="sam",
        estimated_hours=1.5,
    )

    local_id = service.create_or_update_issue_locally(
        SimpleNamespace(), local_issue, "11"
    )

    assert local_id == "I-1"
    assert updates_seen
    assert updates_seen[0][0] == "I-1"
    assert updates_seen[0][1]["project_id"] == "P-9"


def test_create_or_update_issue_locally_creates_new_issue() -> None:
    created_payloads: list[dict[str, Any]] = []

    class _IssueRepo:
        def get(self, _issue_id: str):
            return None

        def update(self, _issue_id: str, _updates: dict[str, Any]) -> None:
            raise AssertionError("update should not be called")

        def create(self, issue_data: dict[str, Any]) -> None:
            created_payloads.append(issue_data)

    backend = SimpleNamespace(
        core=SimpleNamespace(
            db=SimpleNamespace(
                get_issue_repository=lambda: _IssueRepo(),
                remote_links=SimpleNamespace(get_issue_uuid=lambda **_kwargs: None),
            ),
            projects=SimpleNamespace(list=lambda: [SimpleNamespace(id="P-2")]),
        )
    )
    service = _build_service(backend)
    local_issue = SimpleNamespace(
        id="I-2",
        title="Title 2",
        headline="Headline 2",
        content="Body 2",
        status="todo",
        priority="medium",
        issue_type="feature",
        assignee=None,
        estimated_hours=None,
    )

    local_id = service.create_or_update_issue_locally(
        SimpleNamespace(), local_issue, None
    )

    assert local_id == "I-2"
    assert created_payloads
    assert created_payloads[0]["project_id"] == "P-2"


def test_link_pulled_issue_locally_skips_missing_ids() -> None:
    backend = SimpleNamespace(
        core=SimpleNamespace(db=SimpleNamespace(remote_links=None))
    )
    service = _build_service(backend)

    assert service.link_pulled_issue_locally(None, 3) is True
    assert service.link_pulled_issue_locally("I-1", None) is True
