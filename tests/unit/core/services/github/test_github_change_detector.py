"""Tests for GitHub change detector service."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock

from roadmap.common.constants import Status
from roadmap.core.domain.issue import Issue
from roadmap.core.services.github.github_change_detector import GitHubChangeDetector
from roadmap.core.services.github.github_issue_client import GitHubIssueClient


def _client(fetch_return=None, fetch_side_effect=None) -> MagicMock:
    client = MagicMock(spec=GitHubIssueClient)
    if fetch_side_effect is not None:
        client.fetch_issue.side_effect = fetch_side_effect
    else:
        client.fetch_issue.return_value = fetch_return
    return client


def test_detect_issue_changes_requires_owner_and_repo() -> None:
    detector = GitHubChangeDetector(github_client=_client(fetch_return=None))
    issue = Issue(id="abc12345", title="My issue")
    issue.github_issue = 5

    change = detector.detect_issue_changes(issue, owner="", repo="repo")

    assert "error" in change.github_changes
    assert "owner/repo" in change.github_changes["error"]


def test_detect_issue_changes_requires_github_link() -> None:
    detector = GitHubChangeDetector(github_client=_client(fetch_return=None))
    issue = Issue(id="abc12345", title="My issue")

    change = detector.detect_issue_changes(issue, owner="owner", repo="repo")

    assert change.github_changes == {"error": "Issue not linked to GitHub"}


def test_detect_issue_changes_handles_deleted_remote_issue() -> None:
    detector = GitHubChangeDetector(github_client=_client(fetch_return=None))
    issue = Issue(id="abc12345", title="My issue")
    issue.github_issue = 77

    change = detector.detect_issue_changes(issue, owner="owner", repo="repo")

    assert change.github_changes == {"issue": "deleted on GitHub"}


def test_detect_issue_changes_flags_conflict_when_both_sides_changed() -> None:
    detector = GitHubChangeDetector(
        github_client=_client(
            fetch_return={
                "title": "Remote title",
                "body": "remote body",
                "state": "closed",
            }
        )
    )
    issue = Issue(id="abc12345", title="Local title", content="local body")
    issue.github_issue = 10

    change = detector.detect_issue_changes(
        issue,
        owner="owner",
        repo="repo",
        last_sync_time=datetime.now(UTC),
    )

    assert change.local_changes == {}
    assert "title" in change.github_changes
    assert "content" in change.github_changes
    assert change.has_conflict is False


def test_detect_issue_changes_surfaces_exception_as_error() -> None:
    detector = GitHubChangeDetector(
        github_client=_client(fetch_side_effect=RuntimeError("network down"))
    )
    issue = Issue(id="abc12345", title="My issue")
    issue.github_issue = 11

    change = detector.detect_issue_changes(issue, owner="owner", repo="repo")

    assert change.github_changes == {"error": "network down"}


def test_detect_milestone_changes_returns_none() -> None:
    detector = GitHubChangeDetector(github_client=_client(fetch_return=None))

    assert detector.detect_milestone_changes(object()) is None


def test_parse_github_issue_number_accepts_string_and_int() -> None:
    assert GitHubChangeDetector._parse_github_issue_number("42") == 42
    assert GitHubChangeDetector._parse_github_issue_number(7) == 7


def test_detect_github_changes_handles_equal_values_without_status_change() -> None:
    issue = Issue(
        id="abc12345",
        title="Same title",
        content="Same body",
        status=Status.CLOSED,
    )

    changes = GitHubChangeDetector._detect_github_changes(
        issue,
        {"title": "Same title", "body": "Same body", "state": "closed"},
    )

    assert changes == {}
