"""Application tests for retained local-only Git behavior."""

from types import SimpleNamespace
from typing import cast

import pytest

from roadmap.application.contracts import GitSnapshot, IssueMutationResult
from roadmap.application.failures import ApplicationFailure
from roadmap.application.use_cases.issue_mutations import IssueMutations
from roadmap.application.use_cases.issues import IssueQueries
from roadmap.application.use_cases.local_git import LocalGit
from roadmap.domain.types import EntityId


class _Repository:
    def __init__(self, snapshot: GitSnapshot) -> None:
        self.snapshot = snapshot
        self.created: list[tuple[str, bool]] = []

    def inspect_local_git(self) -> GitSnapshot:
        return self.snapshot

    def create_branch(self, name: str, *, checkout: bool) -> None:
        self.created.append((name, checkout))

    def user_identity(self) -> tuple[str | None, str | None]:
        return None, None


class _Issues:
    def __init__(self, *issues: SimpleNamespace) -> None:
        self._issues = {issue.id: issue for issue in issues}

    def list_all(self):
        return tuple(SimpleNamespace(issue=issue) for issue in self._issues.values())

    def view(self, issue_id: EntityId):
        return SimpleNamespace(issue=self._issues[issue_id])


class _Mutations:
    def __init__(self) -> None:
        self.linked: list[tuple[EntityId, str]] = []

    def link_branch(self, issue_id: EntityId, branch: str) -> IssueMutationResult:
        self.linked.append((issue_id, branch))
        return cast(IssueMutationResult, SimpleNamespace(projection_stale=False))


def _issue(identity: str, title: str, branches: tuple[str, ...] = ()):
    return SimpleNamespace(id=EntityId(identity), title=title, git_branches=branches)


def test_inspect_enriches_local_snapshot_with_canonical_links() -> None:
    repository = _Repository(GitSnapshot(True, "work/topic", "abc", ("file",)))
    issues = _Issues(
        _issue("issue-b", "Second", ("work/topic",)),
        _issue("issue-a", "First", ("work/topic",)),
    )

    snapshot = LocalGit(
        repository, cast(IssueQueries, issues), cast(IssueMutations, _Mutations())
    ).inspect()

    assert snapshot.linked_issue_ids == ("issue-a", "issue-b")
    assert snapshot.changed_paths == ("file",)


def test_create_branch_uses_safe_name_and_persists_explicit_link() -> None:
    repository = _Repository(GitSnapshot(True, "main", "abc", ("notes.txt",)))
    issue = _issue("issue-7", "Fix Weird / Shell $(input)!")
    mutations = _Mutations()

    result = LocalGit(
        repository,
        cast(IssueQueries, _Issues(issue)),
        cast(IssueMutations, mutations),
    ).create_issue_branch(issue.id, checkout=False)

    assert result.branch == "issue/issue-7-fix-weird-shell-input"
    assert repository.created == [(result.branch, False)]
    assert mutations.linked == [(issue.id, result.branch)]
    assert result.dirty_paths == ("notes.txt",)


def test_link_fails_cleanly_outside_repository() -> None:
    service = LocalGit(
        _Repository(GitSnapshot(False, None, None, ())),
        cast(IssueQueries, _Issues(_issue("issue-1", "Example"))),
        cast(IssueMutations, _Mutations()),
    )

    with pytest.raises(ApplicationFailure, match="not a Git repository"):
        service.link_current_branch(EntityId("issue-1"))
