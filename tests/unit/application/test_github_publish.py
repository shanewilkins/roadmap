"""Closure publication selection, validation and retry boundaries."""

from dataclasses import replace
from datetime import UTC, datetime

import pytest

from roadmap.application.failures import ApplicationFailure, FailureCategory
from roadmap.application.use_cases.github_publish import (
    CommittedIssue,
    CommittedIssues,
    PublishGitHubClosures,
)
from roadmap.domain.aggregates import Issue
from roadmap.domain.types import EntityId, IssueStatus, Timestamp, Title


def issue(**changes):
    at = Timestamp(datetime(2026, 10, 8, tzinfo=UTC))
    original = Issue(
        EntityId("local-1"),
        at,
        at,
        title=Title("Investigate hang"),
        labels=("github-publish:owner/repo#3756", "github-close:not-planned"),
    ).close(at, None, "Not reproducible on 0.3.1; eight cases verified")
    return replace(original, **changes)


class Source:
    def __init__(self, *issues):
        self.issues = issues
        self.revision = "a" * 40

    def snapshot(self):
        return CommittedIssues(
            self.revision,
            tuple(
                CommittedIssue(item, f".roadmap/issues/{item.id}.md")
                for item in self.issues
            ),
        )


class Destination:
    def __init__(self):
        self.calls = []
        self.fail_number = None

    def publish(self, publication):
        self.calls.append(publication.number)
        if publication.number == self.fail_number:
            raise ApplicationFailure(
                FailureCategory.STORAGE_UNAVAILABLE, "network failure"
            )
        return "closed"


def test_preview_is_offline_and_links_committed_evidence():
    destination = Destination()
    publisher = PublishGitHubClosures(Source(issue()), destination)
    [(publication, result)] = publisher.execute("owner/repo")
    assert destination.calls == []
    assert result == "preview"
    assert publication.disposition == "not_planned"
    assert "/blob/" + "a" * 40 in publication.evidence_url
    assert "Not reproducible on 0.3.1" in publication.comment


def test_only_explicit_matching_closed_records_are_selected():
    publisher = PublishGitHubClosures(
        Source(
            issue(id=EntityId("no-opt-in"), labels=("github:3756",)),
            issue(id=EntityId("open"), status=IssueStatus.TODO),
            issue(id=EntityId("elsewhere"), labels=("github-publish:other/repo#2",)),
            issue(),
        ),
        Destination(),
    )
    assert [item.issue_id for item in publisher.plan("OWNER/repo")] == ["local-1"]


@pytest.mark.parametrize(
    "changes",
    [
        {"labels": ("github-publish:bad#2",)},
        {"labels": ("github-publish:owner/repo#2",)},
        {"labels": ("github-publish:owner/repo#2", "github-close:unknown")},
        {
            "labels": (
                "github-publish:owner/repo#2",
                "github-close:completed",
                "github-close:not-planned",
            )
        },
        {
            "labels": (
                "github-publish:owner/repo#2",
                "github-publish:owner/repo#3",
                "github-close:completed",
            )
        },
        {"history": ()},
    ],
)
def test_invalid_batch_never_partially_publishes(changes):
    destination = Destination()
    publisher = PublishGitHubClosures(
        Source(issue(), issue(id=EntityId("invalid"), **changes)), destination
    )
    with pytest.raises(ApplicationFailure):
        publisher.execute("owner/repo", apply=True)
    assert destination.calls == []


@pytest.mark.parametrize("duplicate", [issue(), issue(id=EntityId("different-id"))])
def test_duplicate_identity_or_target_is_rejected(duplicate):
    with pytest.raises(ApplicationFailure, match="Duplicate|Multiple"):
        PublishGitHubClosures(Source(issue(), duplicate), Destination()).plan(
            "owner/repo"
        )


def test_failure_is_non_success_and_retry_replans_the_batch():
    destination = Destination()
    second = issue(
        id=EntityId("second"),
        labels=("github-publish:owner/repo#4000", "github-close:completed"),
    )
    publisher = PublishGitHubClosures(Source(issue(), second), destination)
    destination.fail_number = 4000
    with pytest.raises(ApplicationFailure, match="network failure"):
        publisher.execute("owner/repo", apply=True)
    assert destination.calls == [3756, 4000]
    destination.fail_number = None
    assert len(publisher.execute("owner/repo", apply=True)) == 2


def test_marker_survives_unrelated_commit_but_changes_with_disposition():
    source = Source(issue())
    publisher = PublishGitHubClosures(source, Destination())
    first = publisher.plan("owner/repo")[0]
    source.revision = "b" * 40
    later = publisher.plan("OWNER/REPO")[0]
    assert first.marker == later.marker
    assert first.evidence_url != later.evidence_url
    source.issues = (
        issue(labels=("github-publish:owner/repo#3756", "github-close:completed")),
    )
    assert first.marker != publisher.plan("owner/repo")[0].marker


@pytest.mark.parametrize(
    "repository", ["owner", "-owner/repo", "owner/repo/extra", "owner/repo\n"]
)
def test_invalid_repository_is_rejected(repository):
    with pytest.raises(ApplicationFailure, match="OWNER/REPO"):
        PublishGitHubClosures(Source(), Destination()).plan(repository)
