"""Transactional issue lifecycle and relationship use cases."""

from __future__ import annotations

from collections.abc import Callable

from roadmap.application.contracts import (
    IssueBatchResult,
    IssueCreateCommand,
    IssueMutationResult,
    IssueUpdateCommand,
)
from roadmap.application.failures import ApplicationFailure, FailureCategory
from roadmap.application.ports import (
    AssigneeDirectory,
    Clock,
    CurrentIdentity,
    IssueUnitOfWork,
    IssueUnitOfWorkFactory,
)
from roadmap.domain.aggregates import Issue
from roadmap.domain.failures import DomainFailure
from roadmap.domain.types import (
    EntityId,
    IssueComment,
    IssueRelations,
    IssueStatus,
    RetentionState,
    Timestamp,
)


class IssueMutations:
    """One Application path for retained issue mutations."""

    def __init__(
        self,
        units: IssueUnitOfWorkFactory,
        identity: CurrentIdentity,
        assignees: AssigneeDirectory,
        clock: Clock,
    ):
        self._units = units
        self._identity = identity
        self._assignees = assignees
        self._clock = clock

    def create(self, command: IssueCreateCommand) -> IssueMutationResult:
        at = self._clock.now()
        try:
            with self._units.create() as unit:
                issues = self._issues(unit)
                self._require_milestone(unit, command.milestone_id)
                assignee = self._resolve_assignee(command.assignee, auto=True)
                issue = Issue(
                    EntityId.new(),
                    at,
                    at,
                    title=command.title,
                    priority=command.priority,
                    issue_type=command.issue_type,
                    relations=IssueRelations(
                        command.milestone_id, command.depends_on, command.blocks
                    ),
                    labels=command.labels,
                    assignee=assignee,
                    estimated_hours=command.estimated_hours,
                    content=command.content,
                ).record_event("created", at)
                changed = self._reciprocate_new(issue, issues, at)
                self._require_acyclic((*issues.values(), issue, *changed))
                unit.save_issue(issue)
                for related in changed:
                    unit.save_issue(related)
                return self._commit(unit, issue)
        except DomainFailure as error:
            raise self._invalid(error) from error

    def _resolved_update_assignee(
        self, issue: Issue, command: IssueUpdateCommand
    ) -> str | None:
        if command.assignee is not None:
            return self._resolve_assignee(command.assignee)
        return issue.assignee

    @staticmethod
    def _resolved_update_relations(
        issue: Issue, command: IssueUpdateCommand
    ) -> IssueRelations:
        if command.milestone_id is not None:
            return IssueRelations(
                command.milestone_id,
                issue.relations.depends_on,
                issue.relations.blocks,
            )
        return issue.relations

    @staticmethod
    def _update_unchanged(
        issue: Issue,
        *,
        title: str,
        content: str,
        priority,
        relations: IssueRelations,
        assignee: str | None,
        estimated_hours: float | None,
    ) -> bool:
        return (
            title == issue.title
            and content == issue.content
            and priority is issue.priority
            and relations == issue.relations
            and assignee == issue.assignee
            and estimated_hours == issue.estimated_hours
        )

    def _apply_update_status(
        self, changed: Issue, command: IssueUpdateCommand, at: Timestamp
    ) -> Issue:
        if command.status is not None:
            return self._transition(
                changed, IssueStatus(command.status), at, command.reason
            )
        return changed.record_event("updated", at, command.reason)

    def update(self, command: IssueUpdateCommand) -> IssueMutationResult:
        at = self._clock.now()
        try:
            with self._units.create() as unit:
                issue = self._load(unit, command.issue_id)
                self._require_milestone(unit, command.milestone_id)
                assignee = self._resolved_update_assignee(issue, command)
                relations = self._resolved_update_relations(issue, command)
                title = command.title or issue.title
                content = (
                    command.content if command.content is not None else issue.content
                )
                priority = command.priority or issue.priority
                estimated_hours = (
                    command.estimated_hours
                    if command.estimated_hours is not None
                    else issue.estimated_hours
                )
                unchanged = self._update_unchanged(
                    issue,
                    title=title,
                    content=content,
                    priority=priority,
                    relations=relations,
                    assignee=assignee,
                    estimated_hours=estimated_hours,
                )
                if unchanged and (
                    command.status is None
                    or IssueStatus(command.status) is issue.status
                ):
                    return IssueMutationResult(issue)
                changed = issue.revise(
                    at=at,
                    title=title,
                    content=content,
                    priority=priority,
                    relations=relations,
                    assignee=assignee,
                    estimated_hours=estimated_hours,
                )
                changed = self._apply_update_status(changed, command, at)
                unit.save_issue(changed)
                return self._commit(unit, changed)
        except (DomainFailure, ValueError) as error:
            raise self._invalid(error) from error

    def start(
        self, issue_id: EntityId, at: Timestamp | None = None
    ) -> IssueMutationResult:
        started_at = at or self._clock.now()
        return self._change(
            issue_id,
            lambda issue: (
                issue
                if issue.status is IssueStatus.IN_PROGRESS
                and issue.actual_start_at is not None
                else issue.start(started_at)
            ),
        )

    def progress(self, issue_id: EntityId, percentage: float) -> IssueMutationResult:
        at = self._clock.now()
        return self._change(
            issue_id,
            lambda issue: (
                issue
                if issue.progress_percentage == percentage
                else issue.set_progress(percentage, at)
            ),
        )

    def transition(
        self, issue_id: EntityId, status: IssueStatus, reason: str | None = None
    ) -> IssueMutationResult:
        at = self._clock.now()
        return self._change(
            issue_id, lambda issue: self._transition(issue, status, at, reason)
        )

    def close(
        self,
        issue_id: EntityId,
        completed_at: Timestamp | None,
        reason: str | None,
        *,
        record_time: bool = False,
    ) -> IssueMutationResult:
        at = self._clock.now()
        actual_end = completed_at or (at if record_time else None)
        return self._change(
            issue_id,
            lambda issue: (
                issue
                if issue.status is IssueStatus.CLOSED
                else issue.close(at, actual_end, reason)
            ),
        )

    def add_comment(
        self,
        issue_id: EntityId,
        author: str,
        body: str,
        in_reply_to: int | None,
    ) -> IssueComment:
        at = self._clock.now()
        try:
            with self._units.create() as unit:
                issue = self._load(unit, issue_id)
                if in_reply_to is not None and not any(
                    comment.id == in_reply_to for comment in issue.comments
                ):
                    raise ApplicationFailure(
                        FailureCategory.INVALID_REQUEST,
                        f"Cannot find comment {in_reply_to} to reply to",
                    )
                comment = IssueComment(
                    id=max((item.id for item in issue.comments), default=0) + 1,
                    author=author.strip(),
                    body=body.strip(),
                    created_at=at,
                    updated_at=at,
                    in_reply_to=in_reply_to,
                )
                unit.save_issue(issue.add_comment(comment, at))
                unit.commit()
                return comment
        except DomainFailure as error:
            raise self._invalid(error) from error

    def link_branch(self, issue_id: EntityId, branch: str) -> IssueMutationResult:
        """Persist one explicit local branch reference on an issue."""
        at = self._clock.now()
        try:
            with self._units.create() as unit:
                issue = self._load(unit, issue_id)
                changed = issue.link_branch(branch, at)
                unit.save_issue(changed)
                return self._commit(unit, changed)
        except DomainFailure as error:
            raise self._invalid(error) from error

    def add_dependency(
        self, issue_id: EntityId, dependency_id: EntityId
    ) -> IssueMutationResult:
        return self._change_dependency(issue_id, dependency_id, "add")

    def remove_dependency(
        self, issue_id: EntityId, dependency_id: EntityId
    ) -> IssueMutationResult:
        return self._change_dependency(issue_id, dependency_id, "remove")

    def replace_dependency(
        self, issue_id: EntityId, old_id: EntityId, new_id: EntityId
    ) -> IssueMutationResult:
        at = self._clock.now()
        try:
            with self._units.create() as unit:
                issues = self._issues(unit)
                issue = self._from(issues, issue_id)
                old = self._from(issues, old_id)
                new = self._from(issues, new_id)
                if old_id not in issue.relations.depends_on:
                    raise ApplicationFailure(
                        FailureCategory.INVALID_REQUEST,
                        f"Dependency '{old_id}' is not linked to issue '{issue_id}'",
                    )
                if old_id == new_id:
                    return IssueMutationResult(issue)
                dependencies = tuple(
                    new_id if item == old_id else item
                    for item in issue.relations.depends_on
                )
                dependencies = tuple(dict.fromkeys(dependencies))
                changed = self._relations(
                    issue,
                    IssueRelations(
                        issue.relations.milestone_id,
                        dependencies,
                        issue.relations.blocks,
                    ),
                    at,
                )
                old_changed = self._remove_block(old, issue_id, at)
                new_changed = self._add_block(new, issue_id, at)
                prospective = self._replace(issues, changed, old_changed, new_changed)
                self._require_acyclic(prospective.values())
                for item in (changed, old_changed, new_changed):
                    unit.save_issue(item)
                return self._commit(unit, changed)
        except DomainFailure as error:
            raise self._invalid(error) from error

    @staticmethod
    def _require_closed_for_archive(selected: tuple[Issue, ...], force: bool) -> None:
        if not force and any(
            item.status is not IssueStatus.CLOSED for item in selected
        ):
            raise ApplicationFailure(
                FailureCategory.INVALID_REQUEST,
                "Only closed issues may be archived without --force",
            )

    @staticmethod
    def _archive_changes(
        selected: tuple[Issue, ...], at: Timestamp
    ) -> tuple[Issue, ...]:
        return tuple(
            item.change_retention(RetentionState.ARCHIVED, at).record_event(
                "archived", at
            )
            for item in selected
            if item.retention is RetentionState.VISIBLE
        )

    def archive(
        self,
        issue_id: EntityId | None = None,
        *,
        all_closed: bool = False,
        orphaned: bool = False,
        force: bool = False,
        dry_run: bool = False,
    ) -> IssueBatchResult:
        at = self._clock.now()
        try:
            with self._units.create() as unit:
                issues = self._issues(unit)
                selected = self._archive_selection(
                    issues, issue_id, all_closed, orphaned
                )
                selected = tuple(
                    item
                    for item in selected
                    if item.retention is RetentionState.VISIBLE
                )
                self._require_closed_for_archive(selected, force)
                changed = self._archive_changes(selected, at)
                if not dry_run:
                    for item in changed:
                        unit.save_issue(item)
                    unit.commit()
                return IssueBatchResult(changed, unit.projection_stale)
        except DomainFailure as error:
            raise self._invalid(error) from error

    def restore(
        self,
        issue_id: EntityId | None = None,
        *,
        restore_all: bool = False,
        status: IssueStatus | None = None,
        dry_run: bool = False,
    ) -> IssueBatchResult:
        at = self._clock.now()
        try:
            with self._units.create() as unit:
                issues = self._issues(unit)
                selected = (
                    tuple(
                        item
                        for item in issues.values()
                        if item.retention is RetentionState.ARCHIVED
                    )
                    if restore_all
                    else (self._from(issues, issue_id),)
                )
                changed = []
                for item in selected:
                    if item.retention is not RetentionState.ARCHIVED:
                        continue
                    restored = item.change_retention(RetentionState.VISIBLE, at)
                    if status is not None:
                        restored = self._transition(restored, status, at, None)
                    changed.append(restored.record_event("restored", at))
                if not dry_run:
                    for item in changed:
                        unit.save_issue(item)
                    unit.commit()
                return IssueBatchResult(tuple(changed), unit.projection_stale)
        except DomainFailure as error:
            raise self._invalid(error) from error

    def purge(self, issue_id: EntityId) -> Issue:
        at = self._clock.now()
        try:
            with self._units.create() as unit:
                issues = self._issues(unit)
                issue = self._from(issues, issue_id)
                if issue.retention is not RetentionState.ARCHIVED:
                    raise ApplicationFailure(
                        FailureCategory.INVALID_REQUEST,
                        f"Issue '{issue_id}' must be archived before it can be deleted",
                    )
                issue.change_retention(RetentionState.PURGED, at)
                inbound = [
                    item.id
                    for item in issues.values()
                    if issue_id in item.relations.depends_on + item.relations.blocks
                ]
                if inbound:
                    joined = ", ".join(str(item) for item in sorted(inbound))
                    raise ApplicationFailure(
                        FailureCategory.CONFLICT,
                        f"Cannot purge issue '{issue_id}'; referenced by {joined}",
                    )
                unit.delete_issue(issue_id)
                unit.commit()
                return issue
        except DomainFailure as error:
            raise self._invalid(error) from error

    def _change(
        self,
        issue_id: EntityId,
        operation: Callable[[Issue], Issue],
    ) -> IssueMutationResult:
        try:
            with self._units.create() as unit:
                issue = self._load(unit, issue_id)
                changed = operation(issue)
                if changed == issue:
                    return IssueMutationResult(issue)
                unit.save_issue(changed)
                return self._commit(unit, changed)
        except DomainFailure as error:
            raise self._invalid(error) from error

    def _change_dependency(
        self, issue_id: EntityId, dependency_id: EntityId, operation: str
    ) -> IssueMutationResult:
        at = self._clock.now()
        try:
            with self._units.create() as unit:
                issues = self._issues(unit)
                issue = self._from(issues, issue_id)
                dependency = self._from(issues, dependency_id)
                current = issue.relations.depends_on
                if operation == "add":
                    if dependency_id in current:
                        return IssueMutationResult(issue)
                    dependencies = (*current, dependency_id)
                    related = self._add_block(dependency, issue_id, at)
                else:
                    if dependency_id not in current:
                        raise ApplicationFailure(
                            FailureCategory.INVALID_REQUEST,
                            f"Dependency '{dependency_id}' is not linked to issue '{issue_id}'",
                        )
                    dependencies = tuple(
                        item for item in current if item != dependency_id
                    )
                    related = self._remove_block(dependency, issue_id, at)
                changed = self._relations(
                    issue,
                    IssueRelations(
                        issue.relations.milestone_id,
                        dependencies,
                        issue.relations.blocks,
                    ),
                    at,
                )
                prospective = self._replace(issues, changed, related)
                self._require_acyclic(prospective.values())
                unit.save_issue(changed)
                unit.save_issue(related)
                return self._commit(unit, changed)
        except DomainFailure as error:
            raise self._invalid(error) from error

    @staticmethod
    def _issues(unit: IssueUnitOfWork) -> dict[EntityId, Issue]:
        return {issue.id: issue for issue in unit.list_issues()}

    @staticmethod
    def _load(unit: IssueUnitOfWork, issue_id: EntityId) -> Issue:
        issue = unit.load_issue(issue_id)
        if issue is None:
            raise ApplicationFailure(
                FailureCategory.NOT_FOUND, f"Issue '{issue_id}' was not found"
            )
        return issue

    @staticmethod
    def _from(issues: dict[EntityId, Issue], issue_id: EntityId | None) -> Issue:
        issue = issues.get(issue_id) if issue_id is not None else None
        if issue is None:
            raise ApplicationFailure(
                FailureCategory.NOT_FOUND, f"Issue '{issue_id}' was not found"
            )
        return issue

    @staticmethod
    def _commit(unit: IssueUnitOfWork, issue: Issue) -> IssueMutationResult:
        unit.commit()
        return IssueMutationResult(issue, unit.projection_stale)

    def _resolve_assignee(self, value: str | None, *, auto: bool = False) -> str | None:
        if value is None and auto:
            return self._identity.current_identity()
        if value is None:
            return None
        canonical = self._assignees.canonical_assignee(value)
        if canonical is None:
            raise ApplicationFailure(
                FailureCategory.INVALID_REQUEST, f"Invalid assignee: {value}"
            )
        return canonical

    @staticmethod
    def _require_milestone(
        unit: IssueUnitOfWork, milestone_id: EntityId | None
    ) -> None:
        if milestone_id is not None and unit.load_milestone(milestone_id) is None:
            raise ApplicationFailure(
                FailureCategory.NOT_FOUND,
                f"Milestone '{milestone_id}' was not found",
            )

    @staticmethod
    def _transition(
        issue: Issue,
        status: IssueStatus,
        at: Timestamp,
        reason: str | None,
    ) -> Issue:
        if issue.status is status:
            return issue
        if status is IssueStatus.IN_PROGRESS and issue.actual_start_at is None:
            return issue.start(at, reason)
        if status is IssueStatus.CLOSED:
            return issue.close(at, None, reason)
        changed = issue.change_status(status, at)
        return changed.record_event(f"status:{status.value}", at, reason)

    @staticmethod
    def _relations(issue: Issue, relations: IssueRelations, at: Timestamp) -> Issue:
        return issue.revise(
            at=at,
            title=issue.title,
            content=issue.content,
            priority=issue.priority,
            relations=relations,
            assignee=issue.assignee,
            estimated_hours=issue.estimated_hours,
        )

    def _reciprocate_new(
        self, issue: Issue, issues: dict[EntityId, Issue], at: Timestamp
    ) -> tuple[Issue, ...]:
        changed: dict[EntityId, Issue] = {}
        for dependency_id in issue.relations.depends_on:
            target = self._from(issues, dependency_id)
            changed[target.id] = self._add_block(target, issue.id, at)
        for blocked_id in issue.relations.blocks:
            target = changed.get(blocked_id) or self._from(issues, blocked_id)
            dependencies = (*target.relations.depends_on, issue.id)
            changed[target.id] = self._relations(
                target,
                IssueRelations(
                    target.relations.milestone_id,
                    tuple(dict.fromkeys(dependencies)),
                    target.relations.blocks,
                ),
                at,
            )
        return tuple(changed.values())

    def _add_block(self, issue: Issue, blocked_id: EntityId, at: Timestamp) -> Issue:
        blocks = tuple(dict.fromkeys((*issue.relations.blocks, blocked_id)))
        return self._relations(
            issue,
            IssueRelations(
                issue.relations.milestone_id, issue.relations.depends_on, blocks
            ),
            at,
        )

    def _remove_block(self, issue: Issue, blocked_id: EntityId, at: Timestamp) -> Issue:
        blocks = tuple(item for item in issue.relations.blocks if item != blocked_id)
        return self._relations(
            issue,
            IssueRelations(
                issue.relations.milestone_id, issue.relations.depends_on, blocks
            ),
            at,
        )

    @staticmethod
    def _replace(
        issues: dict[EntityId, Issue], *changes: Issue
    ) -> dict[EntityId, Issue]:
        result = dict(issues)
        result.update((issue.id, issue) for issue in changes)
        return result

    @staticmethod
    def _require_acyclic(issues) -> None:
        graph = {issue.id: set(issue.relations.depends_on) for issue in issues}
        visiting: set[EntityId] = set()
        visited: set[EntityId] = set()

        def visit(identity: EntityId) -> None:
            if identity in visiting:
                raise ApplicationFailure(
                    FailureCategory.CONFLICT, "Issue dependency cycle is not permitted"
                )
            if identity in visited:
                return
            visiting.add(identity)
            for dependency in graph.get(identity, set()):
                visit(dependency)
            visiting.remove(identity)
            visited.add(identity)

        for identity in graph:
            visit(identity)

    @staticmethod
    def _archive_selection(
        issues: dict[EntityId, Issue],
        issue_id: EntityId | None,
        all_closed: bool,
        orphaned: bool,
    ) -> tuple[Issue, ...]:
        if issue_id is not None:
            return (IssueMutations._from(issues, issue_id),)
        if all_closed:
            return tuple(
                issue
                for issue in issues.values()
                if issue.retention is RetentionState.VISIBLE
                and issue.status is IssueStatus.CLOSED
            )
        if orphaned:
            return tuple(
                issue
                for issue in issues.values()
                if issue.retention is RetentionState.VISIBLE
                and issue.relations.milestone_id is None
            )
        raise ApplicationFailure(
            FailureCategory.INVALID_REQUEST,
            "Specify an issue ID, --all-closed, or --orphaned",
        )

    @staticmethod
    def _invalid(error: Exception) -> ApplicationFailure:
        return ApplicationFailure(FailureCategory.INVALID_REQUEST, str(error))
