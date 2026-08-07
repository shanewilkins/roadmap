"""Wave 2 tests for GitHub fetch services."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import MagicMock, patch

import pytest

from roadmap.adapters.sync.backends.services.github_issue_fetch_service import (
    GitHubIssueFetchService,
)
from roadmap.adapters.sync.backends.services.github_milestone_fetch_service import (
    GitHubMilestoneFetchService,
)


def test_github_issue_fetch_service_returns_empty_without_client() -> None:
    service = GitHubIssueFetchService(
        github_client=cast(Any, None),
        config={"owner": "acme", "repo": "roadmap"},
        helpers=MagicMock(),
    )

    assert service.get_issues() == {}


def test_github_issue_fetch_service_converts_and_skips_failed_items() -> None:
    client = MagicMock()
    client.get_issues.return_value = [{"number": 1, "title": "ok"}, {"number": 2}]
    service = GitHubIssueFetchService(
        github_client=client,
        config={"owner": "acme", "repo": "roadmap"},
        helpers=MagicMock(),
    )

    def _convert(issue_dict: dict) -> SimpleNamespace:
        if issue_dict.get("number") == 2:
            raise ValueError("bad conversion")
        return SimpleNamespace(id="github-1")

    with patch.object(service, "_dict_to_sync_issue", side_effect=_convert):
        result = service.get_issues()

    assert list(result.keys()) == ["1"]


def test_github_issue_fetch_service_returns_empty_on_client_exception() -> None:
    client = MagicMock()
    client.get_issues.side_effect = RuntimeError("api down")
    service = GitHubIssueFetchService(
        github_client=client,
        config={"owner": "acme", "repo": "roadmap"},
        helpers=MagicMock(),
    )

    assert service.get_issues() == {}


def test_dict_to_sync_issue_normalizes_labels_and_status() -> None:
    issue = GitHubIssueFetchService._dict_to_sync_issue(
        {
            "number": 42,
            "title": "Ship feature",
            "body": "details",
            "state": "closed",
            "labels": [{"name": "bug"}, "ops"],
            "assignee": {"login": "shane"},
            "milestone": {"title": "M1"},
        }
    )

    assert issue.backend_id == 42
    assert issue.status == "closed"
    assert issue.labels == ["bug", "ops"]
    assert issue.assignee == "shane"
    assert issue.milestone == "M1"


def test_dict_to_sync_issue_rejects_empty_dict() -> None:
    with pytest.raises(ValueError):
        GitHubIssueFetchService._dict_to_sync_issue({})


def test_github_milestone_fetch_service_returns_empty_without_client() -> None:
    service = GitHubMilestoneFetchService(
        github_client=cast(Any, None),
        config={"owner": "acme", "repo": "roadmap"},
    )

    assert service.get_milestones() == {}


def test_github_milestone_fetch_service_converts_and_skips_failed_items() -> None:
    service = GitHubMilestoneFetchService(
        github_client=MagicMock(),
        config={"owner": "acme", "repo": "roadmap", "token": "tkn"},
    )

    fake_handler = MagicMock()
    fake_handler.get_milestones.return_value = [
        {"number": 1, "title": "M1", "state": "open"},
        {"number": 2},
    ]

    with (
        patch(
            "requests.Session",
            return_value=MagicMock(),
        ),
        patch(
            "roadmap.adapters.github.handlers.milestones.MilestoneHandler",
            return_value=fake_handler,
        ),
    ):
        result = service.get_milestones()

    assert list(result.keys()) == ["1"]


def test_github_milestone_fetch_service_returns_empty_on_fetch_exception() -> None:
    service = GitHubMilestoneFetchService(
        github_client=MagicMock(),
        config={"owner": "acme", "repo": "roadmap", "token": "tkn"},
    )

    with patch(
        "requests.Session",
        side_effect=RuntimeError("session boom"),
    ):
        assert service.get_milestones() == {}


def test_dict_to_sync_milestone_parses_dates_and_metadata() -> None:
    service = GitHubMilestoneFetchService(github_client=MagicMock(), config={})

    milestone = service._dict_to_sync_milestone(
        {
            "number": 7,
            "title": "Release",
            "state": "open",
            "description": "Milestone details",
            "due_on": "2026-03-01T00:00:00Z",
            "open_issues": 3,
            "closed_issues": 4,
        }
    )

    assert milestone.backend_id == 7
    assert milestone.name == "Release"
    assert milestone.status == "open"
    assert milestone.due_date is not None
    assert milestone.metadata["open_issues"] == 3


def test_dict_to_sync_milestone_requires_number_and_title() -> None:
    service = GitHubMilestoneFetchService(github_client=MagicMock(), config={})

    with pytest.raises(ValueError):
        service._dict_to_sync_milestone({"title": "No number"})

    with pytest.raises(ValueError):
        service._dict_to_sync_milestone({"number": 8})
