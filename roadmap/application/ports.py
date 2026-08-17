"""Narrow capabilities required by retained application use cases."""

from typing import Protocol

from roadmap.domain.aggregates import Issue, Milestone, Project
from roadmap.domain.types import EntityId, Timestamp

from .contracts import GitSnapshot, IssueQueryRecord


class Clock(Protocol):
    def now(self) -> Timestamp: ...


class LoadIssue(Protocol):
    def load_issue(self, issue_id: EntityId) -> Issue | None: ...


class SaveIssue(Protocol):
    def save_issue(self, issue: Issue) -> None: ...


class LoadMilestone(Protocol):
    def load_milestone(self, milestone_id: EntityId) -> Milestone | None: ...


class SaveMilestone(Protocol):
    def save_milestone(self, milestone: Milestone) -> None: ...


class LoadProject(Protocol):
    def load_project(self, project_id: EntityId) -> Project | None: ...


class SaveProject(Protocol):
    def save_project(self, project: Project) -> None: ...


class UnitOfWork(Protocol):
    def commit(self) -> None: ...
    def rollback(self) -> None: ...


class ProjectionMaintenance(Protocol):
    def refresh(self, changed_ids: tuple[EntityId, ...]) -> None: ...
    def rebuild(self) -> None: ...


class InspectLocalGit(Protocol):
    def inspect_local_git(self) -> GitSnapshot: ...


class ReadIssueRecords(Protocol):
    """Canonical issue records, optionally accelerated by a projection."""

    def list_issue_records(self) -> tuple[IssueQueryRecord, ...]: ...
    def load_issue_record(self, issue_id: EntityId) -> IssueQueryRecord | None: ...
    def next_milestone_id(self) -> EntityId | None: ...


class CurrentIdentity(Protocol):
    def current_identity(self) -> str | None: ...
