"""Targeted tests for IssueService merge/archive and error branches."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from roadmap.common.constants import Priority, Status
from roadmap.core.domain.comment import Comment
from roadmap.core.domain.issue import Issue
from roadmap.core.services.issue.issue_service import IssueService


class _Repo:
    def __init__(self) -> None:
        self.items: dict[str, Issue] = {}
        self.raise_on_save = False
        self.raise_on_list_all = False

    def get(self, issue_id: str) -> Issue | None:
        return self.items.get(issue_id)

    def save(self, issue: Issue) -> None:
        if self.raise_on_save:
            raise RuntimeError("save failed")
        self.items[issue.id] = issue

    def list(
        self, milestone: str | None = None, status: str | None = None
    ) -> list[Issue]:
        del milestone, status
        return list(self.items.values())

    def update(self, issue_id: str, updates: dict) -> Issue | None:
        issue = self.items.get(issue_id)
        if issue is None:
            return None
        for key, value in updates.items():
            setattr(issue, key, value)
        self.items[issue_id] = issue
        return issue

    def delete(self, issue_id: str) -> bool:
        return self.items.pop(issue_id, None) is not None

    def delete_many(self, issue_ids: list[str]) -> int:
        deleted = 0
        for issue_id in issue_ids:
            if self.delete(issue_id):
                deleted += 1
        return deleted

    def list_all_including_archived(self) -> list[Issue]:
        if self.raise_on_list_all:
            raise RuntimeError("list-all failed")
        return list(self.items.values())


def _issue(issue_id: str, title: str = "Issue") -> Issue:
    return Issue(
        id=issue_id,
        title=title,
        status=Status.TODO,
        priority=Priority.MEDIUM,
        labels=[],
        depends_on=[],
        blocks=[],
        git_branches=[],
        git_commits=[],
        comments=[],
        remote_ids={},
        created=datetime(2024, 1, 1, tzinfo=UTC),
        updated=datetime(2024, 1, 2, tzinfo=UTC),
    )


def test_list_all_including_archived_returns_empty_on_repo_error() -> None:
    repo = _Repo()
    repo.raise_on_list_all = True
    service = IssueService(repo)

    issues = service.list_all_including_archived()

    assert issues == []


def test_get_issue_converts_file_path_to_string() -> None:
    repo = _Repo()
    issue = _issue("i1")
    issue.file_path = str(Path("issues/i1.md"))
    repo.items[issue.id] = issue
    service = IssueService(repo)

    found = service.get_issue("i1")

    assert found is not None
    assert found.file_path == "issues/i1.md"


def test_merge_issues_returns_err_when_canonical_missing() -> None:
    service = IssueService(_Repo())

    result = service.merge_issues("missing", "dup")

    assert result.is_err()
    assert "Canonical issue missing not found" == result.unwrap_err()


def test_merge_issues_returns_err_when_duplicate_missing() -> None:
    repo = _Repo()
    repo.items["canonical"] = _issue("canonical")
    service = IssueService(repo)

    result = service.merge_issues("canonical", "missing")

    assert result.is_err()
    assert "Duplicate issue missing not found" == result.unwrap_err()


def test_merge_issues_merges_fields_and_saves() -> None:
    repo = _Repo()
    canonical = _issue("canonical", "Canonical")
    canonical.labels = ["bug"]
    canonical.depends_on = ["d1"]
    canonical.blocks = ["b1"]
    canonical.git_branches = ["feat/a"]
    canonical.git_commits = [{"sha": "c1"}]
    canonical.comments = [
        Comment(
            id=1,
            issue_id="canonical",
            author="alice",
            body="note1",
            created_at=datetime(2024, 1, 1, tzinfo=UTC),
            updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        )
    ]
    canonical.remote_ids = {"github": 1}
    canonical.updated = datetime(2024, 1, 2, tzinfo=UTC)

    duplicate = _issue("duplicate", "Duplicate")
    duplicate.labels = ["bug", "security"]
    duplicate.depends_on = ["d2"]
    duplicate.blocks = ["b2"]
    duplicate.git_branches = ["feat/b"]
    duplicate.git_commits = [{"sha": "c2"}]
    duplicate.comments = [
        Comment(
            id=2,
            issue_id="duplicate",
            author="bob",
            body="note2",
            created_at=datetime(2024, 1, 1, tzinfo=UTC),
            updated_at=datetime(2024, 1, 1, tzinfo=UTC),
        )
    ]
    duplicate.remote_ids = {"jira": "PRJ-1"}
    duplicate.updated = datetime(2024, 1, 3, tzinfo=UTC)

    repo.items[canonical.id] = canonical
    repo.items[duplicate.id] = duplicate
    service = IssueService(repo)

    result = service.merge_issues(canonical.id, duplicate.id)

    assert result.is_ok()
    merged = result.unwrap()
    assert merged.id == "canonical"
    assert set(merged.labels) == {"bug", "security"}
    assert set(merged.depends_on) == {"d1", "d2"}
    assert set(merged.blocks) == {"b1", "b2"}
    assert set(merged.git_branches) == {"feat/a", "feat/b"}
    assert merged.git_commits == [{"sha": "c1"}, {"sha": "c2"}]
    assert [comment.body for comment in merged.comments] == ["note1", "note2"]
    assert merged.remote_ids == {"github": 1, "jira": "PRJ-1"}
    assert merged.updated == datetime(2024, 1, 3, tzinfo=UTC)


def test_merge_issues_returns_err_when_save_fails() -> None:
    repo = _Repo()
    repo.items["canonical"] = _issue("canonical")
    repo.items["duplicate"] = _issue("duplicate")
    repo.raise_on_save = True
    service = IssueService(repo)

    result = service.merge_issues("canonical", "duplicate")

    assert result.is_err()
    assert "Failed to merge issues: save failed" == result.unwrap_err()


def test_archive_issue_returns_err_when_not_found() -> None:
    service = IssueService(_Repo())

    result = service.archive_issue("missing")

    assert result.is_err()
    assert "Issue missing not found" == result.unwrap_err()


def test_archive_issue_sets_metadata_and_status(monkeypatch) -> None:
    repo = _Repo()
    issue = _issue("i1")
    repo.items[issue.id] = issue
    service = IssueService(repo)

    fixed_now = datetime(2024, 2, 1, tzinfo=UTC)
    monkeypatch.setattr(
        "roadmap.core.services.issue.issue_service.now_utc",
        lambda: fixed_now,
    )

    result = service.archive_issue("i1", duplicate_of_id="i0", resolution_type="merge")

    assert result.is_ok()
    archived = result.unwrap()
    assert archived.status == Status.ARCHIVED
    assert archived.github_sync_metadata is not None
    assert archived.github_sync_metadata["resolution_type"] == "merge"
    assert archived.github_sync_metadata["duplicate_of_id"] == "i0"
    assert archived.github_sync_metadata["archived_at"] == fixed_now.isoformat()


def test_archive_issue_returns_err_when_save_fails() -> None:
    repo = _Repo()
    issue = _issue("i1")
    repo.items[issue.id] = issue
    repo.raise_on_save = True
    service = IssueService(repo)

    result = service.archive_issue("i1")

    assert result.is_err()
    assert "Failed to archive issue: save failed" == result.unwrap_err()
