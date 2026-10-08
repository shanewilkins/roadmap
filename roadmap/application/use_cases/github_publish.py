"""Explicit, one-way publication of committed issue closure decisions."""

import re
from dataclasses import dataclass
from hashlib import sha256
from typing import Protocol

from roadmap.application.failures import ApplicationFailure, FailureCategory
from roadmap.domain.aggregates import Issue
from roadmap.domain.types import IssueStatus


@dataclass(frozen=True)
class CommittedIssue:
    issue: Issue
    path: str


@dataclass(frozen=True)
class CommittedIssues:
    revision: str
    issues: tuple[CommittedIssue, ...]


@dataclass(frozen=True)
class ClosurePublication:
    issue_id: str
    repository: str
    number: int
    disposition: str
    evidence_url: str
    marker: str
    comment: str


class CommittedIssueSource(Protocol):
    def snapshot(self) -> CommittedIssues: ...


class GitHubClosureDestination(Protocol):
    def publish(self, publication: ClosurePublication) -> str: ...


_REPOSITORY = r"[A-Za-z0-9][A-Za-z0-9_.-]*/[A-Za-z0-9][A-Za-z0-9_.-]*"
_TARGET = re.compile(rf"github-publish:({_REPOSITORY})#([1-9][0-9]*)\Z")
_DISPOSITIONS = {
    "github-close:completed": "completed",
    "github-close:not-planned": "not_planned",
}


def _invalid(message: str) -> ApplicationFailure:
    return ApplicationFailure(FailureCategory.INVALID_REQUEST, message)


def _target(issue: Issue, repository: str) -> int | None:
    labels = [label for label in issue.labels if label.startswith("github-publish:")]
    if not labels or issue.status is not IssueStatus.CLOSED:
        return None
    matches = [_TARGET.fullmatch(label) for label in labels]
    if len(matches) != 1 or matches[0] is None:
        raise _invalid(
            f"Issue {issue.id} needs exactly one valid GitHub publish target"
        )
    target_repository, raw_number = matches[0].groups()
    return (
        int(raw_number)
        if target_repository.casefold() == repository.casefold()
        else None
    )


def _publication(
    record: CommittedIssue, repository: str, number: int, revision: str
) -> ClosurePublication:
    issue = record.issue
    dispositions = [
        label for label in issue.labels if label.startswith("github-close:")
    ]
    if len(dispositions) != 1 or dispositions[0] not in _DISPOSITIONS:
        raise _invalid(
            f"Issue {issue.id} needs github-close:completed or github-close:not-planned"
        )
    closure = next(
        (
            event
            for event in reversed(issue.history)
            if event.action in {"closed", "status:closed"}
        ),
        None,
    )
    if closure is None or not closure.reason:
        raise _invalid(f"Issue {issue.id} needs a recorded closure reason")
    disposition = _DISPOSITIONS[dispositions[0]]
    fingerprint = sha256(
        f"{issue.id}\n{repository.casefold()}#{number}\n{closure.at.value.isoformat()}\n{disposition}\n{closure.reason}".encode()
    ).hexdigest()
    marker = f"<!-- roadmap-closure:{fingerprint} -->"
    # Git paths are encoded by the source adapter for safe URL use.
    evidence = f"https://github.com/{repository}/blob/{revision}/{record.path}"
    comment = (
        f"{marker}\nClosed through Roadmap: **{issue.title}**\n\n"
        f"{closure.reason}\n\n"
        f"[Committed decision, history and evidence]({evidence})\n"
        f"Local issue: `{issue.id}`; disposition: `{disposition}`."
    )
    return ClosurePublication(
        str(issue.id), repository, number, disposition, evidence, marker, comment
    )


class PublishGitHubClosures:
    """Plan the entire batch before any network writes; never mutate local state."""

    def __init__(
        self, source: CommittedIssueSource, destination: GitHubClosureDestination
    ) -> None:
        self._source = source
        self._destination = destination

    def plan(self, repository: str) -> tuple[ClosurePublication, ...]:
        if not re.fullmatch(_REPOSITORY, repository):
            raise _invalid("Repository must be OWNER/REPO")
        snapshot = self._source.snapshot()
        publications: list[ClosurePublication] = []
        identities: set[str] = set()
        targets: set[int] = set()
        for record in snapshot.issues:
            issue = record.issue
            if str(issue.id) in identities:
                raise _invalid(f"Duplicate canonical issue identity: {issue.id}")
            identities.add(str(issue.id))
            number = _target(issue, repository)
            if number is None:
                continue
            if number in targets:
                raise _invalid(f"Multiple local closures target {repository}#{number}")
            targets.add(number)
            publications.append(
                _publication(record, repository, number, snapshot.revision)
            )
        return tuple(sorted(publications, key=lambda item: item.number))

    def execute(
        self, repository: str, *, apply: bool = False
    ) -> tuple[tuple[ClosurePublication, str], ...]:
        plan = self.plan(repository)
        return tuple(
            (item, self._destination.publish(item) if apply else "preview")
            for item in plan
        )
