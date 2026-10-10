"""Explicit source capture without transferring authority over local planning."""

import json
import re
from dataclasses import dataclass, replace
from hashlib import sha256
from typing import Any, Protocol
from uuid import uuid4

from roadmap.application.failures import ApplicationFailure, FailureCategory
from roadmap.application.ports import Clock, IssueUnitOfWorkFactory
from roadmap.domain.aggregates import Issue
from roadmap.domain.types import EntityId, IssueComment, IssueStatus, Title

REPOSITORY = r"[A-Za-z0-9][A-Za-z0-9_.-]*/[A-Za-z0-9][A-Za-z0-9_.-]*"
URL = re.compile(rf"https://github\.com/({REPOSITORY})/issues/([1-9][0-9]*)\Z", re.I)
MARKER = re.compile(
    rf"<!-- roadmap-github-source:v1 ({REPOSITORY})#([1-9][0-9]*) ([a-f0-9]{{64}}) -->\n"
)
LEGACY = re.compile(
    rf"^(?:# GitHub source record:|Baseline GitHub report:) (https://github\.com/{REPOSITORY}/issues/[1-9][0-9]*)\s*$",
    re.M | re.I,
)


def invalid(message: str) -> ApplicationFailure:
    return ApplicationFailure(FailureCategory.INVALID_REQUEST, message)


def selection(repository: str, numbers: tuple[int, ...]) -> str:
    if not re.fullmatch(REPOSITORY, repository):
        raise invalid("Repository must be OWNER/REPO")
    if not 1 <= len(numbers) <= 25 or len(set(numbers)) != len(numbers):
        raise invalid("Select 1–25 distinct issue numbers")
    if any(type(number) is not int or number <= 0 for number in numbers):
        raise invalid("Issue numbers must be positive integers")
    return repository.casefold()


def _comment_complete(item: dict[str, Any]) -> bool:
    return all(
        (
            type(item.get("id")) is int,
            isinstance(item.get("body"), str),
            "user" in item,
            isinstance(item.get("created_at"), str),
            isinstance(item.get("updated_at"), str),
            isinstance(item.get("html_url"), str),
        )
    )


def _record_identity(item: dict[str, Any]) -> str:
    return str(item.get("id") or item.get("node_id") or canonical_json(item))


def _entry_valid(item: dict[str, Any], kind: str) -> bool:
    return (
        _comment_complete(item)
        if kind == "comments"
        else isinstance(item.get("event"), str)
    )


def _records(value: Any, kind: str) -> list[dict[str, Any]]:
    if not isinstance(value, list) or any(not isinstance(item, dict) for item in value):
        raise invalid(f"Invalid GitHub {kind} records")
    if any(not _entry_valid(item, kind) for item in value):
        raise invalid(f"Incomplete GitHub {kind} record")
    identities = [_record_identity(item) for item in value]
    if len(set(identities)) != len(identities):
        raise invalid(f"Duplicate GitHub {kind} records; retry extraction")
    return sorted(value, key=_record_identity)


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


@dataclass(frozen=True)
class GitHubSource:
    repository: str
    number: int
    payload: str
    fingerprint: str
    title: str
    node_id: str

    @property
    def target(self) -> str:
        return f"{self.repository}#{self.number}"


def _issue_identity(issue: dict[str, Any], repository: str, number: int) -> bool:
    return all(
        (
            "pull_request" not in issue,
            type(issue.get("number")) is int,
            issue.get("number") == number,
            str(issue.get("html_url", "")).casefold()
            == f"https://github.com/{repository}/issues/{number}",
            isinstance(issue.get("node_id"), str),
            bool(issue.get("node_id")),
        )
    )


def _issue_content(issue: dict[str, Any]) -> bool:
    required = {
        "body",
        "user",
        "created_at",
        "updated_at",
        "labels",
        "assignees",
        "milestone",
    }
    return all(
        (
            required <= set(issue),
            issue.get("state") in {"open", "closed"},
            isinstance(issue.get("title"), str),
            bool(str(issue.get("title", "")).strip()),
            issue.get("body") is None or isinstance(issue.get("body"), str),
        )
    )


def validate_source(repository: str, number: int, payload: Any) -> GitHubSource:
    if not isinstance(payload, dict) or set(payload) != {
        "issue",
        "comments",
        "timeline",
    }:
        raise invalid("Incomplete GitHub source envelope")
    issue = payload["issue"]
    if (
        not isinstance(issue, dict)
        or not _issue_identity(issue, repository, number)
        or not _issue_content(issue)
    ):
        raise invalid(
            "GitHub issue identity/content does not match the requested issue"
        )
    comments = _records(payload["comments"], "comments")
    timeline = _records(payload["timeline"], "timeline")
    if type(issue.get("comments")) is not int or issue["comments"] != len(comments):
        raise invalid("GitHub comment count changed or extraction is incomplete; retry")
    normalized = canonical_json(
        {"issue": issue, "comments": comments, "timeline": timeline}
    )
    if len(normalized.encode()) > 20_000_000:
        raise invalid(
            "GitHub source exceeds the 20 MB per-issue bound; no import performed"
        )
    return GitHubSource(
        repository,
        number,
        normalized,
        sha256(normalized.encode()).hexdigest(),
        issue["title"],
        issue["node_id"],
    )


class GitHubIssueSource(Protocol):
    def fetch(
        self, repository: str, numbers: tuple[int, ...]
    ) -> tuple[GitHubSource, ...]: ...


def captured_sources(issue: Issue) -> tuple[GitHubSource, ...]:
    sources = []
    for comment in issue.comments:
        if not comment.body.startswith("<!-- roadmap-github-source:"):
            continue
        match = MARKER.match(comment.body)
        if match is None:
            raise invalid(f"Issue {issue.id} has malformed import provenance")
        repository, raw_number, digest = match.groups()
        try:
            raw = comment.body.split("\n```json\n", 1)[1].removesuffix("\n```")
            source = validate_source(
                repository.casefold(), int(raw_number), json.loads(raw)
            )
        except (IndexError, ValueError) as error:
            raise invalid(f"Issue {issue.id} has invalid import source data") from error
        if source.fingerprint != digest:
            raise invalid(
                f"Issue {issue.id} import provenance was edited; resolve before retry"
            )
        sources.append(source)
    return tuple(sources)


def bindings(issue: Issue, sources: tuple[GitHubSource, ...]) -> set[str]:
    targets = {source.target for source in sources}
    for text in (issue.content, *(comment.body for comment in issue.comments)):
        for raw_url in LEGACY.findall(text):
            match = URL.fullmatch(raw_url)
            if match:
                targets.add(f"{match[1].casefold()}#{int(match[2])}")
    for label in issue.labels:
        if label.startswith(("github-publish:", "github-source:")):
            value = label.split(":", 1)[1]
            if re.fullmatch(rf"{REPOSITORY}#[1-9][0-9]*", value):
                targets.add(value.casefold())
    if len(targets) > 1:
        raise invalid(
            f"Issue {issue.id} has conflicting qualified GitHub identities: {sorted(targets)}"
        )
    return targets


@dataclass(frozen=True)
class ImportResult:
    target: str
    issue_id: str | None
    action: str
    fingerprint: str
    projection_stale: bool = False


def _match(source: GitHubSource, records) -> tuple[Issue | None, str]:
    _check_foreign_node(source, records)
    matches = [
        (issue, history)
        for issue, targets, history in records
        if source.target in targets
    ]
    if len(matches) > 1:
        raise invalid(
            f"Duplicate local records for {source.target}: {[str(issue.id) for issue, _ in matches]}"
        )
    if not matches:
        return None, "create"
    issue, history = matches[0]
    if any(item.node_id != source.node_id for item in history):
        raise invalid(
            f"GitHub node identity changed for {source.target}; explicit reconciliation required"
        )
    return issue, _revision_action(source, history)


def _check_foreign_node(source: GitHubSource, records) -> None:
    foreign = [
        str(issue.id)
        for issue, targets, history in records
        if source.target not in targets
        and any(item.node_id == source.node_id for item in history)
    ]
    if foreign:
        raise invalid(
            f"GitHub node already belongs to other qualified targets in local issues {foreign}; explicit transfer/rename reconciliation required"
        )


def _revision_action(source: GitHubSource, history: tuple[GitHubSource, ...]) -> str:
    if history and history[-1].fingerprint == source.fingerprint:
        return "unchanged"
    if any(item.fingerprint == source.fingerprint for item in history):
        return "reuse-revision"
    return "capture-revision"


def _owner_redirect(issue: Issue) -> str | None:
    values = [
        label.split(":", 1)[1]
        for label in issue.labels
        if label.startswith("github-source-owner:")
    ]
    if len(values) > 1:
        raise invalid(f"Issue {issue.id} has multiple source owners")
    return values[0] if values else None


def _owned_records(records):
    indexed = {
        str(issue.id): (issue, targets, history) for issue, targets, history in records
    }
    owned = []
    for issue, targets, history in records:
        redirect = _owner_redirect(issue)
        if redirect is None:
            owned.append((issue, targets, history))
            continue
        owner = indexed.get(redirect)
        if not _valid_redirect(issue, targets, owner):
            raise invalid(
                f"Invalid source-owner redirect on issue {issue.id}; require a closed resolution:duplicate record and one matching non-redirected canonical owner"
            )
    return owned


def _valid_redirect(issue: Issue, targets: set[str], owner) -> bool:
    if owner is None:
        return False
    aggregate, owner_targets, _history = owner
    return all(
        (
            issue.status is IssueStatus.CLOSED,
            "resolution:duplicate" in issue.labels,
            aggregate.id != issue.id,
            bool(targets),
            targets == owner_targets,
            _owner_redirect(aggregate) is None,
        )
    )


class ImportGitHubIssues:
    def __init__(
        self, source: GitHubIssueSource, units: IssueUnitOfWorkFactory, clock: Clock
    ):
        self._source, self._units, self._clock = source, units, clock

    def _capture(self, source: GitHubSource, issue: Issue | None) -> Issue:
        now = self._clock.now()
        if issue is None:
            issue = Issue(
                EntityId(str(uuid4())),
                now,
                now,
                title=Title(source.title),
                content=f"GitHub source: https://github.com/{source.repository}/issues/{source.number}\n\nFull attributed source is retained in the import revision comments.",
            ).record_event("created", now)
        marker = (
            f"<!-- roadmap-github-source:v1 {source.target} {source.fingerprint} -->"
        )
        body = (
            marker
            + "\nAttributed GitHub source revision; source state is not local planning state.\n```json\n"
            + json.dumps(
                json.loads(source.payload), ensure_ascii=False, sort_keys=True, indent=2
            )
            + "\n```"
        )
        comment = IssueComment(
            max((item.id for item in issue.comments), default=0) + 1,
            "GitHub source import",
            body,
            now,
            now,
            external_url=f"https://github.com/{source.repository}/issues/{source.number}",
        )
        return issue.add_comment(comment, now).record_event(
            "github-source-captured", now, source.target
        )

    def _fetch(
        self, repository: str, numbers: tuple[int, ...]
    ) -> tuple[GitHubSource, ...]:
        fetched = self._source.fetch(repository, numbers)
        try:
            sources = tuple(
                validate_source(repository, item.number, json.loads(item.payload))
                for item in fetched
            )
        except ValueError as error:
            raise invalid("Invalid extracted GitHub source JSON") from error
        if len(sources) != len(numbers) or {item.number for item in sources} != set(
            numbers
        ):
            raise invalid(
                "GitHub extraction did not return exactly the selected issues"
            )
        return sources

    @staticmethod
    def _plan(issues: tuple[Issue, ...], sources: tuple[GitHubSource, ...]):
        records = []
        for issue in issues:
            history = captured_sources(issue)
            targets = bindings(issue, history)
            if not targets and any(
                f"github:{source.number}" in issue.labels for source in sources
            ):
                raise invalid(
                    f"Issue {issue.id} has an unqualified legacy GitHub reference; establish a github-source:OWNER/REPO#NUMBER label before importing"
                )
            records.append((issue, targets, history))
        owned = _owned_records(records)
        return [(source, *_match(source, owned)) for source in sources]

    def execute(
        self, repository: str, numbers: tuple[int, ...], *, apply: bool = False
    ) -> tuple[ImportResult, ...]:
        repository = selection(repository, numbers)
        sources = self._fetch(repository, numbers)
        # Extraction completes before taking the workspace lock; every apply rechecks
        # all identities under that lock before staging the first local write.
        with self._units.create(read_only=not apply) as unit:
            plan = self._plan(unit.list_issues(), sources)
            results = []
            for source, issue, action in plan:
                if apply and action in {"create", "capture-revision"}:
                    issue = self._capture(source, issue)
                    unit.save_issue(issue)
                results.append(
                    ImportResult(
                        source.target,
                        str(issue.id) if issue else None,
                        action,
                        source.fingerprint,
                    )
                )
            if apply and any(
                item.action in {"create", "capture-revision"} for item in results
            ):
                unit.commit()
                results = [
                    replace(item, projection_stale=unit.projection_stale)
                    for item in results
                ]
        return tuple(results)
