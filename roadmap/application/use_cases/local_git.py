"""Explicit local Git inspection, branch creation, and issue linking."""

from __future__ import annotations

import re

from roadmap.application.contracts import GitBranchResult, GitSnapshot
from roadmap.application.failures import ApplicationFailure, FailureCategory
from roadmap.application.ports import LocalGitPort
from roadmap.domain.types import EntityId

from .issue_mutations import IssueMutations
from .issues import IssueQueries

_UNSAFE_SLUG = re.compile(r"[^a-z0-9]+")


class LocalGit:
    """Retained Git behavior with no remote, credential, or hook operations."""

    def __init__(
        self,
        repository: LocalGitPort,
        issues: IssueQueries,
        mutations: IssueMutations,
    ) -> None:
        self._repository = repository
        self._issues = issues
        self._mutations = mutations

    def inspect(self) -> GitSnapshot:
        snapshot = self._repository.inspect_local_git()
        if not snapshot.is_repository or snapshot.branch is None:
            return snapshot
        linked = tuple(
            sorted(
                (
                    record.issue.id
                    for record in self._issues.list_all()
                    if snapshot.branch in record.issue.git_branches
                ),
                key=str,
            )
        )
        return GitSnapshot(
            snapshot.is_repository,
            snapshot.branch,
            snapshot.head,
            snapshot.changed_paths,
            linked,
        )

    def create_issue_branch(
        self, issue_id: EntityId, *, checkout: bool
    ) -> GitBranchResult:
        snapshot = self._repository.inspect_local_git()
        if not snapshot.is_repository:
            raise ApplicationFailure(
                FailureCategory.INVALID_REQUEST,
                "Current workspace is not a Git repository",
            )
        issue = self._issues.view(issue_id).issue
        slug = _UNSAFE_SLUG.sub("-", str(issue.title).casefold()).strip("-")[:48]
        branch = f"issue/{issue.id}-{slug}" if slug else f"issue/{issue.id}"
        self._repository.create_branch(branch, checkout=checkout)
        receipt = self._mutations.link_branch(issue.id, branch)
        return GitBranchResult(
            branch,
            issue.id,
            checkout,
            snapshot.changed_paths,
            receipt.projection_stale,
        )

    def link_current_branch(self, issue_id: EntityId) -> GitBranchResult:
        snapshot = self._repository.inspect_local_git()
        if not snapshot.is_repository:
            raise ApplicationFailure(
                FailureCategory.INVALID_REQUEST,
                "Current workspace is not a Git repository",
            )
        if snapshot.branch is None:
            raise ApplicationFailure(
                FailureCategory.INVALID_REQUEST,
                "Cannot link an issue while Git HEAD is detached or unborn",
            )
        issue = self._issues.view(issue_id).issue
        receipt = self._mutations.link_branch(issue.id, snapshot.branch)
        return GitBranchResult(
            snapshot.branch,
            issue.id,
            True,
            snapshot.changed_paths,
            receipt.projection_stale,
        )
