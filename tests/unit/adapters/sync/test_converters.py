"""Wave 2 tests for sync backend converters."""

from __future__ import annotations

from roadmap.adapters.sync.backends.converters import (
    GitHubPayloadToIssueConverter,
    IssueToGitHubPayloadConverter,
)
from roadmap.common.constants import Status
from roadmap.core.domain.issue import Issue
from roadmap.core.models.sync_models import SyncIssue


def test_to_create_payload_filters_labels_and_formats_assignee() -> None:
    issue = Issue(
        title="Test",
        content="Body",
        labels=["bug", "", "  "],
        assignee="  shane  ",
    )

    payload = IssueToGitHubPayloadConverter.to_create_payload(issue)

    assert payload["title"] == "Test"
    assert payload["body"] == "Body"
    assert payload["labels"] == ["bug"]
    assert payload["assignees"] == ["shane"]
    assert "state" not in payload


def test_to_update_payload_sets_state_from_status() -> None:
    issue = Issue(
        title="Closed item",
        content="done",
        status=Status.CLOSED,
    )

    payload = IssueToGitHubPayloadConverter.to_update_payload(issue)

    assert payload["state"] == "closed"


def test_get_github_number_handles_int_string_and_invalid_values() -> None:
    issue_int = Issue(title="A", remote_ids={"github": 12})
    issue_str = Issue(title="B", remote_ids={"github": "34"})
    issue_bad = Issue(title="C", remote_ids={"github": "x"})

    assert IssueToGitHubPayloadConverter.get_github_number(issue_int) == 12
    assert IssueToGitHubPayloadConverter.get_github_number(issue_str) == 34
    assert IssueToGitHubPayloadConverter.get_github_number(issue_bad) is None


def test_from_sync_issue_maps_status_and_remote_id() -> None:
    sync_issue = SyncIssue(
        id="github-9",
        title="Remote",
        status="closed",
        headline="details",
        backend_id="9",
    )

    issue = GitHubPayloadToIssueConverter.from_sync_issue(sync_issue)

    assert issue.status == Status.CLOSED
    assert issue.content == "details"
    assert issue.remote_ids["github"] == 9


def test_from_github_dict_maps_fields() -> None:
    issue = GitHubPayloadToIssueConverter.from_github_dict(
        {
            "number": 77,
            "title": "From API",
            "body": "api body",
            "state": "open",
            "labels": [{"name": "enhancement"}],
            "assignees": [{"login": "dev1"}],
            "milestone": {"title": "Sprint 10"},
        }
    )

    assert issue.status == Status.TODO
    assert issue.labels == ["enhancement"]
    assert issue.assignee == "dev1"
    assert issue.milestone == "Sprint 10"
    assert issue.remote_ids["github"] == 77
