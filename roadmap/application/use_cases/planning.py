"""Canonical project, milestone, assignment, and progress use cases."""

from __future__ import annotations

from datetime import timedelta

from roadmap.application.contracts import (
    CriticalPathNode,
    CriticalPathResult,
    DailySummary,
    MilestoneCreateCommand,
    MilestoneSummary,
    MilestoneUpdateCommand,
    PlanningBatchResult,
    PlanningMutationResult,
    PlanningSnapshot,
    ProjectCreateCommand,
    ProjectSummary,
    ProjectUpdateCommand,
)
from roadmap.application.failures import ApplicationFailure, FailureCategory
from roadmap.application.ports import (
    Clock,
    PlanningUnitOfWork,
    PlanningUnitOfWorkFactory,
)
from roadmap.domain.aggregates import Issue, Milestone, Project
from roadmap.domain.failures import DomainFailure
from roadmap.domain.types import (
    EntityId,
    IssueRelations,
    IssueStatus,
    MilestoneRelation,
    MilestoneStatus,
    ProjectRelations,
    ProjectStatus,
    RetentionState,
    Timestamp,
)


class Planning:
    """One Application path for the retained planning product."""

    def __init__(self, units: PlanningUnitOfWorkFactory, clock: Clock):
        self._units = units
        self._clock = clock

    def snapshot(self) -> PlanningSnapshot:
        with self._units.create() as unit:
            issues = tuple(
                item
                for item in unit.list_issues()
                if item.retention is RetentionState.VISIBLE
            )
            milestones = tuple(
                item
                for item in unit.list_milestones()
                if item.retention is RetentionState.VISIBLE
            )
            projects = tuple(
                item
                for item in unit.list_projects()
                if item.retention is RetentionState.VISIBLE
            )
            milestone_summaries = tuple(
                self._milestone_summary(item, issues)
                for item in sorted(milestones, key=lambda value: str(value.name))
            )
            by_id = {item.milestone.id: item for item in milestone_summaries}
            project_summaries = tuple(
                self._project_summary(item, by_id)
                for item in sorted(projects, key=lambda value: str(value.name))
            )
            return PlanningSnapshot(project_summaries, milestone_summaries, issues)

    def all_projects(self) -> tuple[Project, ...]:
        with self._units.create() as unit:
            return unit.list_projects()

    def all_milestones(self) -> tuple[Milestone, ...]:
        with self._units.create() as unit:
            return unit.list_milestones()

    def all_issues(self) -> tuple[Issue, ...]:
        with self._units.create() as unit:
            return unit.list_issues()

    def now(self) -> Timestamp:
        return self._clock.now()

    def daily_summary(self, current_user: str) -> DailySummary:
        snapshot = self.snapshot()
        upcoming = self._upcoming_milestone(snapshot)
        issues = tuple(
            item
            for item in snapshot.issues
            if item.assignee == current_user
            and item.relations.milestone_id == upcoming.milestone.id
        )
        now = self._clock.now()
        in_progress, overdue, blocked, completed_today = self._daily_groups(issues, now)
        return DailySummary(
            current_user,
            upcoming,
            in_progress,
            overdue,
            blocked,
            self._daily_up_next(issues),
            completed_today,
        )

    def _upcoming_milestone(self, snapshot: PlanningSnapshot) -> MilestoneSummary:
        open_milestones = tuple(
            item
            for item in snapshot.milestones
            if item.milestone.status is MilestoneStatus.OPEN
        )
        if not open_milestones:
            raise ApplicationFailure(
                FailureCategory.NOT_FOUND, "No upcoming milestones found."
            )
        now = self._clock.now().value
        return min(
            open_milestones,
            key=lambda item: (
                item.milestone.due_at is None,
                item.milestone.due_at.value if item.milestone.due_at else now,
                str(item.milestone.name),
            ),
        )

    @staticmethod
    def _in_progress_issues(issues: tuple[Issue, ...]) -> tuple[Issue, ...]:
        return tuple(item for item in issues if item.status is IssueStatus.IN_PROGRESS)

    @staticmethod
    def _overdue_issues(issues: tuple[Issue, ...], now: Timestamp) -> tuple[Issue, ...]:
        return tuple(
            item
            for item in issues
            if item.due_at is not None
            and item.status is not IssueStatus.CLOSED
            and item.due_at < now
        )

    @staticmethod
    def _blocked_issues(issues: tuple[Issue, ...]) -> tuple[Issue, ...]:
        return tuple(item for item in issues if item.status is IssueStatus.BLOCKED)

    @staticmethod
    def _completed_today_issues(
        issues: tuple[Issue, ...], now: Timestamp
    ) -> tuple[Issue, ...]:
        return tuple(
            item
            for item in issues
            if item.status is IssueStatus.CLOSED
            and item.actual_end_at is not None
            and item.actual_end_at.value.date() == now.value.date()
        )

    @classmethod
    def _daily_groups(
        cls, issues: tuple[Issue, ...], now: Timestamp
    ) -> tuple[
        tuple[Issue, ...], tuple[Issue, ...], tuple[Issue, ...], tuple[Issue, ...]
    ]:
        return (
            cls._in_progress_issues(issues),
            cls._overdue_issues(issues, now),
            cls._blocked_issues(issues),
            cls._completed_today_issues(issues, now),
        )

    @staticmethod
    def _daily_up_next(issues: tuple[Issue, ...]) -> tuple[Issue, ...]:
        dependents: dict[EntityId, tuple[EntityId, ...]] = {}
        for item in issues:
            for dependency in item.relations.depends_on:
                dependents[dependency] = (*dependents.get(dependency, ()), item.id)

        def depth(
            identity: EntityId, visiting: frozenset[EntityId] = frozenset()
        ) -> int:
            if identity in visiting:
                return 0
            children = dependents.get(identity, ())
            return (
                0
                if not children
                else 1 + max(depth(child, visiting | {identity}) for child in children)
            )

        candidates = (
            item
            for item in issues
            if item.status is IssueStatus.TODO
            and item.priority.value in {"critical", "high"}
        )
        return tuple(
            sorted(
                candidates,
                key=lambda item: (
                    -depth(item.id),
                    -len(dependents.get(item.id, ())),
                    0 if item.priority.value == "critical" else 1,
                    str(item.id),
                ),
            )[:3]
        )

    def _critical_path_issues(
        self,
        snapshot: PlanningSnapshot,
        milestone: str | None,
        include_closed: bool,
    ) -> tuple[Issue, ...]:
        issues = snapshot.issues
        if milestone is not None:
            selected = self._resolve_milestone(
                tuple(item.milestone for item in snapshot.milestones), milestone
            )
            issues = tuple(
                item for item in issues if item.relations.milestone_id == selected.id
            )
        if not include_closed:
            issues = tuple(
                item for item in issues if item.status is not IssueStatus.CLOSED
            )
        return issues

    def _longest_path(
        self, by_id: dict[EntityId, Issue]
    ) -> tuple[float, tuple[EntityId, ...]]:
        memo: dict[EntityId, tuple[float, tuple[EntityId, ...]]] = {}

        def longest_to(
            identity: EntityId, visiting: frozenset[EntityId] = frozenset()
        ) -> tuple[float, tuple[EntityId, ...]]:
            if identity in memo:
                return memo[identity]
            if identity in visiting:
                raise self._conflict("Dependency graph contains a cycle")
            issue = by_id[identity]
            prior = tuple(
                longest_to(item, visiting | {identity})
                for item in issue.relations.depends_on
                if item in by_id
            )
            best = max(
                prior,
                key=lambda item: (item[0], tuple(map(str, item[1]))),
                default=(0.0, ()),
            )
            result = (best[0] + (issue.estimated_hours or 4.0), (*best[1], identity))
            memo[identity] = result
            return result

        return max(
            (longest_to(identity) for identity in sorted(by_id, key=str)),
            key=lambda item: (item[0], tuple(map(str, item[1]))),
        )

    @staticmethod
    def _critical_path_nodes(
        by_id: dict[EntityId, Issue], path: tuple[EntityId, ...]
    ) -> tuple[CriticalPathNode, ...]:
        return tuple(
            CriticalPathNode(
                identity,
                str(by_id[identity].title),
                by_id[identity].estimated_hours or 4.0,
                tuple(
                    item
                    for item in by_id[identity].relations.depends_on
                    if item in by_id
                ),
            )
            for identity in path
        )

    @staticmethod
    def _blocked_map(
        by_id: dict[EntityId, Issue],
    ) -> dict[EntityId, tuple[EntityId, ...]]:
        blocked: dict[EntityId, tuple[EntityId, ...]] = {}
        for item in by_id.values():
            for dependency in item.relations.depends_on:
                if dependency in by_id:
                    blocked[dependency] = (*blocked.get(dependency, ()), item.id)
        return blocked

    def critical_path(
        self, *, milestone: str | None, include_closed: bool
    ) -> CriticalPathResult:
        snapshot = self.snapshot()
        issues = self._critical_path_issues(snapshot, milestone, include_closed)
        by_id = {item.id: item for item in issues}
        if not by_id:
            return CriticalPathResult((), 0.0, (), ())

        duration, path = self._longest_path(by_id)
        nodes = self._critical_path_nodes(by_id, path)
        blocked = self._blocked_map(by_id)
        return CriticalPathResult(
            nodes,
            duration,
            path,
            tuple(
                (identity, blocked[identity]) for identity in sorted(blocked, key=str)
            ),
            Timestamp(self._clock.now().value + timedelta(hours=duration)),
        )

    def project_is_overdue(self, project: Project) -> bool:
        return (
            project.target_end_at is not None
            and project.status not in {ProjectStatus.COMPLETED, ProjectStatus.CANCELLED}
            and project.target_end_at < self._clock.now()
        )

    def milestone_is_overdue(self, milestone: Milestone) -> bool:
        return (
            milestone.due_at is not None
            and milestone.status is not MilestoneStatus.CLOSED
            and milestone.due_at < self._clock.now()
        )

    def resolve_project_id(self, supplied: str) -> EntityId:
        return self._resolve_project(self.all_projects(), supplied).id

    def resolve_milestone_id(self, supplied: str) -> EntityId:
        return self._resolve_milestone(self.all_milestones(), supplied).id

    def project(
        self, supplied: str, *, include_archived: bool = False
    ) -> ProjectSummary:
        snapshot = self.snapshot()
        matches = tuple(item.project for item in snapshot.projects)
        if include_archived:
            matches = self.all_projects()
        project = self._resolve_project(matches, supplied)
        if project.retention is RetentionState.ARCHIVED and not include_archived:
            raise self._missing("Project", supplied)
        by_id = {item.milestone.id: item for item in snapshot.milestones}
        return self._project_summary(project, by_id)

    def milestone(
        self, supplied: str, *, include_archived: bool = False
    ) -> MilestoneSummary:
        snapshot = self.snapshot()
        matches = tuple(item.milestone for item in snapshot.milestones)
        if include_archived:
            matches = self.all_milestones()
        milestone = self._resolve_milestone(matches, supplied)
        if milestone.retention is RetentionState.ARCHIVED and not include_archived:
            raise self._missing("Milestone", supplied)
        return self._milestone_summary(milestone, snapshot.issues)

    def create_project(self, command: ProjectCreateCommand) -> PlanningMutationResult:
        at = self._clock.now()
        try:
            with self._units.create() as unit:
                projects = unit.list_projects()
                if any(item.name == command.name for item in projects):
                    raise self._conflict(f"Project '{command.name}' already exists")
                project = Project(
                    EntityId.new(),
                    at,
                    at,
                    name=command.name,
                    content=command.content,
                    repository_url=command.repository_url,
                )
                unit.save_project(project)
                return self._commit(unit, project)
        except DomainFailure as error:
            raise self._invalid(error) from error

    def update_project(self, command: ProjectUpdateCommand) -> PlanningMutationResult:
        at = self._clock.now()
        try:
            with self._units.create() as unit:
                project = self._load_project(unit, command.project_id)
                status = command.status or project.status
                changed = project.revise(
                    at=at,
                    name=command.name or project.name,
                    headline=project.headline,
                    content=(
                        command.content
                        if command.content is not None
                        else project.content
                    ),
                    status=status,
                    priority=command.priority or project.priority,
                    owner=command.owner if command.owner is not None else project.owner,
                    estimated_hours=(
                        command.estimated_hours
                        if command.estimated_hours is not None
                        else project.estimated_hours
                    ),
                    repository_url=(
                        command.repository_url
                        if command.repository_url is not None
                        else project.repository_url
                    ),
                )
                if changed == project:
                    return PlanningMutationResult(project)
                unit.save_project(changed)
                return self._commit(unit, changed)
        except DomainFailure as error:
            raise self._invalid(error) from error

    def create_milestone(
        self, command: MilestoneCreateCommand
    ) -> PlanningMutationResult:
        at = self._clock.now()
        try:
            with self._units.create() as unit:
                if any(item.name == command.name for item in unit.list_milestones()):
                    raise self._conflict(f"Milestone '{command.name}' already exists")
                project = self._optional_project(unit, command.project_id)
                milestone = Milestone(
                    EntityId.new(),
                    at,
                    at,
                    name=command.name,
                    content=command.content,
                    due_at=command.due_at,
                    relation=MilestoneRelation(command.project_id),
                )
                unit.save_milestone(milestone)
                if project is not None:
                    unit.save_project(self._link_project(project, milestone.id, at))
                return self._commit(unit, milestone)
        except DomainFailure as error:
            raise self._invalid(error) from error

    def _reproject_milestone(
        self,
        unit: PlanningUnitOfWork,
        milestone_id: EntityId,
        old_project: Project | None,
        new_project: Project | None,
        project_id: EntityId | None,
        at: Timestamp,
    ) -> None:
        if old_project is not None and old_project.id != project_id:
            unit.save_project(self._unlink_project(old_project, milestone_id, at))
        if new_project is not None and (
            old_project is None or new_project.id != old_project.id
        ):
            unit.save_project(self._link_project(new_project, milestone_id, at))

    def update_milestone(
        self, command: MilestoneUpdateCommand
    ) -> PlanningMutationResult:
        at = self._clock.now()
        try:
            with self._units.create() as unit:
                milestone = self._load_milestone(unit, command.milestone_id)
                old_project = self._optional_project(
                    unit, milestone.relation.project_id
                )
                project_id = (
                    command.project_id
                    if command.project_id is not None
                    else milestone.relation.project_id
                )
                new_project = self._optional_project(unit, project_id)
                changed = milestone.revise(
                    at=at,
                    name=command.name or milestone.name,
                    headline=milestone.headline,
                    content=(
                        command.content
                        if command.content is not None
                        else milestone.content
                    ),
                    status=command.status or milestone.status,
                    relation=MilestoneRelation(project_id),
                    due_at=command.due_at
                    if command.due_at is not None
                    else milestone.due_at,
                )
                unit.save_milestone(changed)
                self._reproject_milestone(
                    unit, milestone.id, old_project, new_project, project_id, at
                )
                return self._commit(unit, changed)
        except DomainFailure as error:
            raise self._invalid(error) from error

    def assign_issue(
        self, issue_id: EntityId, milestone_id: EntityId
    ) -> PlanningMutationResult:
        at = self._clock.now()
        with self._units.create() as unit:
            issue = self._load_issue(unit, issue_id)
            self._load_milestone(unit, milestone_id)
            if issue.relations.milestone_id == milestone_id:
                return PlanningMutationResult(issue)
            relations = IssueRelations(
                milestone_id, issue.relations.depends_on, issue.relations.blocks
            )
            changed = issue.revise(
                at=at,
                title=issue.title,
                content=issue.content,
                priority=issue.priority,
                relations=relations,
                assignee=issue.assignee,
                estimated_hours=issue.estimated_hours,
            ).record_event("milestone-assigned", at)
            unit.save_issue(changed)
            return self._commit(unit, changed)

    def close_milestone(
        self, milestone_id: EntityId, *, force: bool
    ) -> PlanningMutationResult:
        at = self._clock.now()
        with self._units.create() as unit:
            milestone = self._load_milestone(unit, milestone_id)
            open_issues = tuple(
                issue
                for issue in unit.list_issues()
                if issue.retention is RetentionState.VISIBLE
                and issue.relations.milestone_id == milestone_id
                and issue.status is not IssueStatus.CLOSED
            )
            if open_issues and not force:
                raise self._conflict(
                    f"Milestone '{milestone.name}' has {len(open_issues)} open issue(s)"
                )
            changed = (
                milestone
                if milestone.status is MilestoneStatus.CLOSED
                else milestone.change_status(MilestoneStatus.CLOSED, at)
            )
            if changed != milestone:
                unit.save_milestone(changed)
                return self._commit(unit, changed)
            return PlanningMutationResult(milestone)

    def close_project(
        self, project_id: EntityId, *, force: bool
    ) -> PlanningMutationResult:
        at = self._clock.now()
        with self._units.create() as unit:
            project = self._load_project(unit, project_id)
            milestones = {item.id: item for item in unit.list_milestones()}
            open_count = sum(
                item.status is not MilestoneStatus.CLOSED
                for item in milestones.values()
                if item.id in project.relations.milestone_ids
                or item.relation.project_id == project.id
            )
            if open_count and not force:
                raise self._conflict(
                    f"Project '{project.name}' has {open_count} open milestone(s)"
                )
            changed = (
                project
                if project.status is ProjectStatus.COMPLETED
                else project.change_status(ProjectStatus.COMPLETED, at)
            )
            if changed != project:
                unit.save_project(changed)
                return self._commit(unit, changed)
            return PlanningMutationResult(project)

    def archive_project(
        self, supplied: str | None, *, all_closed: bool, dry_run: bool, force: bool
    ) -> PlanningBatchResult:
        return self._retention(
            "project",
            supplied,
            all_closed,
            False,
            dry_run,
            force,
            RetentionState.ARCHIVED,
        )

    def restore_project(
        self, supplied: str | None, *, restore_all: bool, dry_run: bool
    ) -> PlanningBatchResult:
        return self._retention(
            "project",
            supplied,
            False,
            restore_all,
            dry_run,
            True,
            RetentionState.VISIBLE,
        )

    def archive_milestone(
        self, supplied: str | None, *, all_closed: bool, dry_run: bool, force: bool
    ) -> PlanningBatchResult:
        return self._retention(
            "milestone",
            supplied,
            all_closed,
            False,
            dry_run,
            force,
            RetentionState.ARCHIVED,
        )

    def restore_milestone(
        self, supplied: str | None, *, restore_all: bool, dry_run: bool
    ) -> PlanningBatchResult:
        return self._retention(
            "milestone",
            supplied,
            False,
            restore_all,
            dry_run,
            True,
            RetentionState.VISIBLE,
        )

    def purge_project(self, project_id: EntityId) -> Project:
        with self._units.create() as unit:
            project = self._load_project(unit, project_id)
            if project.retention is not RetentionState.ARCHIVED:
                raise self._conflict("Project must be archived before deletion")
            inbound = [
                str(item.name)
                for item in unit.list_milestones()
                if item.relation.project_id == project_id
            ]
            if inbound:
                raise self._conflict(
                    f"Cannot purge project; referenced by {', '.join(map(str, inbound))}"
                )
            unit.delete_project(project_id)
            unit.commit()
            return project

    def purge_milestone(self, milestone_id: EntityId) -> Milestone:
        with self._units.create() as unit:
            milestone = self._load_milestone(unit, milestone_id)
            if milestone.retention is not RetentionState.ARCHIVED:
                raise self._conflict("Milestone must be archived before deletion")
            inbound = [
                item.id
                for item in unit.list_issues()
                if item.relations.milestone_id == milestone_id
            ]
            if inbound:
                raise self._conflict(
                    f"Cannot purge milestone; referenced by {', '.join(map(str, inbound))}"
                )
            for project in unit.list_projects():
                if milestone_id in project.relations.milestone_ids:
                    unit.save_project(
                        self._unlink_project(project, milestone_id, self._clock.now())
                    )
            unit.delete_milestone(milestone_id)
            unit.commit()
            return milestone

    def _retention(
        self,
        kind: str,
        supplied: str | None,
        all_closed: bool,
        restore_all: bool,
        dry_run: bool,
        force: bool,
        target: RetentionState,
    ) -> PlanningBatchResult:
        at = self._clock.now()
        try:
            with self._units.create() as unit:
                values: tuple[Project | Milestone, ...] = (
                    tuple(unit.list_projects())
                    if kind == "project"
                    else tuple(unit.list_milestones())
                )
                selected = self._retention_selection(
                    values, kind, supplied, all_closed, restore_all
                )
                self._validate_archive_selection(selected, target, force)
                changed = tuple(
                    item.change_retention(target, at)
                    for item in selected
                    if item.retention is not target
                )
                if not dry_run:
                    self._save_planning_entities(unit, changed)
                    unit.commit()
                return PlanningBatchResult(changed, unit.projection_stale)
        except DomainFailure as error:
            raise self._invalid(error) from error

    def _retention_selection(
        self,
        values: tuple[Project | Milestone, ...],
        kind: str,
        supplied: str | None,
        all_closed: bool,
        restore_all: bool,
    ) -> tuple[Project | Milestone, ...]:
        if restore_all:
            return tuple(
                item for item in values if item.retention is RetentionState.ARCHIVED
            )
        if all_closed:
            return tuple(
                item
                for item in values
                if item.retention is RetentionState.VISIBLE
                and self._planning_entity_complete(item)
            )
        if supplied is None:
            raise self._invalid("Specify an entity or a batch option")
        return (
            self._resolve(
                values,
                supplied,
                "Project" if kind == "project" else "Milestone",
            ),
        )

    def _validate_archive_selection(
        self,
        selected: tuple[Project | Milestone, ...],
        target: RetentionState,
        force: bool,
    ) -> None:
        if target is not RetentionState.ARCHIVED or force:
            return
        if any(not self._planning_entity_complete(item) for item in selected):
            raise self._conflict(
                "Only completed planning entities may be archived without --force"
            )

    @staticmethod
    def _planning_entity_complete(item: Project | Milestone) -> bool:
        if isinstance(item, Project):
            return item.status is ProjectStatus.COMPLETED
        return item.status is MilestoneStatus.CLOSED

    @staticmethod
    def _save_planning_entities(
        unit: PlanningUnitOfWork, values: tuple[Project | Milestone, ...]
    ) -> None:
        for item in values:
            if isinstance(item, Project):
                unit.save_project(item)
            else:
                unit.save_milestone(item)

    @staticmethod
    def _milestone_estimated_remaining(
        assigned: tuple[Issue, ...],
    ) -> tuple[float, float]:
        estimated = sum(item.estimated_hours or 0.0 for item in assigned)
        remaining = sum(
            item.estimated_hours or 0.0
            for item in assigned
            if item.status is not IssueStatus.CLOSED
        )
        return estimated, remaining

    @staticmethod
    def _milestone_progress(assigned: tuple[Issue, ...]) -> float:
        total_weight = sum(item.estimated_hours or 1.0 for item in assigned)
        earned = sum(
            (item.estimated_hours or 1.0)
            * (
                1.0
                if item.status is IssueStatus.CLOSED
                else (item.progress_percentage or 0.0) / 100.0
            )
            for item in assigned
        )
        return earned / total_weight * 100.0 if total_weight else 0.0

    @classmethod
    def _milestone_summary(
        cls, milestone: Milestone, issues: tuple[Issue, ...]
    ) -> MilestoneSummary:
        assigned = tuple(
            item for item in issues if item.relations.milestone_id == milestone.id
        )
        estimated, remaining = cls._milestone_estimated_remaining(assigned)
        progress = cls._milestone_progress(assigned)
        return MilestoneSummary(
            milestone,
            len(assigned),
            sum(item.status is IssueStatus.CLOSED for item in assigned),
            estimated,
            remaining,
            progress,
        )

    @staticmethod
    def _project_linked_milestones(
        project: Project, milestones: dict[EntityId, MilestoneSummary]
    ) -> tuple[MilestoneSummary, ...]:
        return tuple(
            item
            for item in milestones.values()
            if item.milestone.id in project.relations.milestone_ids
            or item.milestone.relation.project_id == project.id
        )

    @staticmethod
    def _project_progress(linked: tuple[MilestoneSummary, ...]) -> float:
        total_weight = sum(item.estimated_hours or 1.0 for item in linked)
        earned = sum(
            (item.estimated_hours or 1.0)
            * (
                1.0
                if item.milestone.status is MilestoneStatus.CLOSED
                else item.progress / 100.0
            )
            for item in linked
        )
        return earned / total_weight * 100.0 if total_weight else 0.0

    @classmethod
    def _project_summary(
        cls, project: Project, milestones: dict[EntityId, MilestoneSummary]
    ) -> ProjectSummary:
        linked = cls._project_linked_milestones(project, milestones)
        progress = cls._project_progress(linked)
        return ProjectSummary(
            project,
            len(linked),
            sum(item.issue_count for item in linked),
            sum(item.closed_count for item in linked),
            sum(item.estimated_hours for item in linked),
            sum(item.remaining_hours for item in linked),
            progress,
        )

    @staticmethod
    def _resolve_project(values: tuple[Project, ...], supplied: str) -> Project:
        return Planning._resolve(values, supplied, "Project")

    @staticmethod
    def _resolve_milestone(values: tuple[Milestone, ...], supplied: str) -> Milestone:
        return Planning._resolve(values, supplied, "Milestone")

    @staticmethod
    def _resolve(values, supplied: str, label: str):
        exact = [
            item
            for item in values
            if str(item.id) == supplied or str(item.name) == supplied
        ]
        if len(exact) == 1:
            return exact[0]
        matches = [item for item in values if str(item.id).startswith(supplied)]
        if not matches:
            raise Planning._missing(label, supplied)
        if len(matches) > 1:
            raise Planning._conflict(
                f"Ambiguous {label.lower()} ID prefix '{supplied}'"
            )
        return matches[0]

    @staticmethod
    def _load_issue(unit: PlanningUnitOfWork, identity: EntityId) -> Issue:
        value = unit.load_issue(identity)
        if value is None:
            raise Planning._missing("Issue", str(identity))
        return value

    @staticmethod
    def _load_milestone(unit: PlanningUnitOfWork, identity: EntityId) -> Milestone:
        value = unit.load_milestone(identity)
        if value is None:
            raise Planning._missing("Milestone", str(identity))
        return value

    @staticmethod
    def _load_project(unit: PlanningUnitOfWork, identity: EntityId) -> Project:
        value = unit.load_project(identity)
        if value is None:
            raise Planning._missing("Project", str(identity))
        return value

    @staticmethod
    def _optional_project(
        unit: PlanningUnitOfWork, identity: EntityId | None
    ) -> Project | None:
        return None if identity is None else Planning._load_project(unit, identity)

    @staticmethod
    def _link_project(project: Project, milestone_id: EntityId, at) -> Project:
        values = project.relations.milestone_ids
        if milestone_id not in values:
            values = (*values, milestone_id)
        return project.reassign(ProjectRelations(values), at)

    @staticmethod
    def _unlink_project(project: Project, milestone_id: EntityId, at) -> Project:
        values = tuple(
            item for item in project.relations.milestone_ids if item != milestone_id
        )
        return project.reassign(ProjectRelations(values), at)

    @staticmethod
    def _commit(unit: PlanningUnitOfWork, aggregate) -> PlanningMutationResult:
        unit.commit()
        return PlanningMutationResult(aggregate, unit.projection_stale)

    @staticmethod
    def _missing(label: str, value: str) -> ApplicationFailure:
        return ApplicationFailure(
            FailureCategory.NOT_FOUND, f"{label} '{value}' was not found"
        )

    @staticmethod
    def _conflict(message: str) -> ApplicationFailure:
        return ApplicationFailure(FailureCategory.CONFLICT, message)

    @staticmethod
    def _invalid(error) -> ApplicationFailure:
        return ApplicationFailure(FailureCategory.INVALID_REQUEST, str(error))
