"""Helper functions for GitHub backend synchronization operations."""

from datetime import UTC, datetime
from typing import Any

from structlog import get_logger

logger = get_logger()


class GitHubBackendHelpers:
    """Helper methods for GitHub backend synchronization."""

    def __init__(self, core, remote_link_repo=None):
        """Initialize GitHubBackendHelpers.

        Args:
            core: Core roadmap instance.
            remote_link_repo: Optional remote link repository.
        """
        self.core = core
        self.remote_link_repo = remote_link_repo

    def _parse_timestamp(self, timestamp_str: str | None) -> "datetime | None":
        if not timestamp_str:
            return None
        try:
            if isinstance(timestamp_str, str):
                if timestamp_str.endswith("Z"):
                    timestamp_str = timestamp_str[:-1] + "+00:00"
                return datetime.fromisoformat(timestamp_str)
            return timestamp_str
        except (ValueError, AttributeError):
            return None

    def _dict_to_sync_issue(self, issue_dict: dict[str, Any]):
        from roadmap.core.models.sync_models import SyncIssue

        issue_id = issue_dict.get("id", issue_dict.get("number", ""))
        return SyncIssue(
            id=str(issue_id),
            title=issue_dict.get("title", ""),
            status=issue_dict.get("state", "open"),
            headline=issue_dict.get("body", ""),
            assignee=issue_dict.get("assignee"),
            milestone=issue_dict.get("milestone"),
            labels=issue_dict.get("labels", []),
            created_at=issue_dict.get("created_at"),
            updated_at=issue_dict.get("updated_at"),
            backend_name="github",
            backend_id=str(issue_dict.get("number", "")),
            remote_ids={"github": str(issue_dict.get("number", ""))},
            raw_response=issue_dict,
        )

    def _convert_sync_to_issue(self, issue_id: str, sync_issue):
        from roadmap.core.domain.issue import (
            Issue,
            IssueType,
            Priority,
            Status,
        )

        github_state = sync_issue.status or "open"
        status_map = {"open": Status.TODO, "closed": Status.CLOSED}
        status = status_map.get(github_state, Status.TODO)

        priority = Priority.MEDIUM

        created = sync_issue.created_at or datetime.now(UTC)
        updated = sync_issue.updated_at or datetime.now(UTC)

        labels = sync_issue.labels or []
        assignee = sync_issue.assignee
        milestone = sync_issue.milestone
        content = sync_issue.headline or ""

        if sync_issue.remote_ids:
            remote_ids: dict[str, str | int] = sync_issue.remote_ids
        else:
            remote_ids = (
                {"github": str(sync_issue.backend_id)} if sync_issue.backend_id else {}
            )

        return Issue(
            id=issue_id,
            title=sync_issue.title or "Untitled",
            content=content,
            status=status,
            priority=priority,
            issue_type=IssueType.FEATURE,
            labels=labels,
            assignee=assignee,
            milestone=milestone,
            created=created,
            updated=updated,
            remote_ids=remote_ids,
        )

    def _convert_github_to_issue(self, issue_id: str, remote_data: dict[str, Any]):
        from roadmap.core.domain.issue import (
            Issue,
            IssueType,
            Priority,
            Status,
        )

        github_state = remote_data.get("state", "open")
        status_map = {"open": Status.TODO, "closed": Status.CLOSED}
        status = status_map.get(github_state, Status.TODO)

        priority = Priority.MEDIUM

        created_at_str = remote_data.get("created_at")
        created = self._parse_timestamp(created_at_str) or datetime.now(UTC)

        updated_at_str = remote_data.get("updated_at")
        updated = self._parse_timestamp(updated_at_str) or datetime.now(UTC)

        labels = []
        if "labels" in remote_data:
            labels_data = remote_data.get("labels", [])
            if isinstance(labels_data, list):
                labels = (
                    [
                        label["name"] if isinstance(label, dict) else str(label)
                        for label in labels_data
                    ]
                    if labels_data
                    else []
                )

        assignee = None
        assignees = remote_data.get("assignees", [])
        if assignees and isinstance(assignees, list):
            first_assignee = assignees[0]
            assignee = (
                first_assignee.get("login")
                if isinstance(first_assignee, dict)
                else str(first_assignee)
            )
        elif "assignee" in remote_data and remote_data["assignee"]:
            assignee_data = remote_data["assignee"]
            assignee = (
                assignee_data.get("login")
                if isinstance(assignee_data, dict)
                else str(assignee_data)
            )

        milestone = None
        milestone_data = remote_data.get("milestone")
        if milestone_data:
            milestone = (
                milestone_data.get("title")
                if isinstance(milestone_data, dict)
                else str(milestone_data)
            )

        issue = Issue(
            id=issue_id,
            title=remote_data.get("title", ""),
            status=status,
            priority=priority,
            issue_type=IssueType.OTHER,
            created=created,
            updated=updated,
            milestone=milestone,
            assignee=assignee,
            labels=labels,
            content=remote_data.get("body") or "",
        )

        return issue

    def _find_matching_local_issue(
        self, title: str, github_issue_number: str | int | None
    ):
        matching_local_issue = None

        for local_issue in self.core.issues.list():
            remote_github_id = (
                local_issue.remote_ids.get("github") if local_issue.remote_ids else None
            )
            try:
                if (
                    remote_github_id
                    and github_issue_number is not None
                    and str(remote_github_id) == str(github_issue_number)
                ):
                    matching_local_issue = local_issue
                    logger.debug(
                        "github_pull_found_existing_by_github_number",
                        github_number=github_issue_number,
                        local_id=local_issue.id,
                    )
                    break
            except Exception:
                continue

        if not matching_local_issue:
            from roadmap.adapters.sync.services import SyncLinkingService

            matching_local_issue = SyncLinkingService.find_duplicate_by_title(
                title, "github", self.core
            )
            if matching_local_issue:
                logger.debug(
                    "github_pull_found_matching_by_title",
                    github_number=github_issue_number,
                    local_id=matching_local_issue.id,
                    title=title,
                )

        return matching_local_issue

    def _apply_or_create_local_issue(
        self,
        issue_id: str,
        matching_local_issue,
        updates: dict,
        github_issue_number: str | int | None,
        remote_issue=None,
    ) -> None:
        from roadmap.adapters.sync.services import (
            IssuePersistenceService,
            SyncLinkingService,
        )

        if matching_local_issue:
            self.core.issues.update(matching_local_issue.id, **updates)

            if github_issue_number is not None:
                IssuePersistenceService.update_issue_with_remote_id(
                    matching_local_issue, "github", github_issue_number
                )
                IssuePersistenceService.save_issue(matching_local_issue, self.core)
                SyncLinkingService.link_issue_in_database(
                    self.remote_link_repo,
                    matching_local_issue.id,
                    "github",
                    github_issue_number,
                )

            logger.debug(
                "github_pull_issue_updated",
                github_number=github_issue_number,
                local_id=matching_local_issue.id,
            )

        elif self.core.issues.get(issue_id):
            self.core.issues.update(issue_id, **updates)

            if github_issue_number is not None:
                local_issue = self.core.issues.get(issue_id)
                if local_issue:
                    IssuePersistenceService.update_issue_with_remote_id(
                        local_issue, "github", github_issue_number
                    )
                    IssuePersistenceService.save_issue(local_issue, self.core)
                    SyncLinkingService.link_issue_in_database(
                        self.remote_link_repo, issue_id, "github", github_issue_number
                    )

            logger.debug("github_pull_issue_updated", issue_id=issue_id)

        else:
            if remote_issue is not None:
                issue_obj = self._convert_sync_to_issue(issue_id, remote_issue)
            else:
                from roadmap.core.domain.issue import (
                    Issue as DomainIssue,
                )
                from roadmap.core.domain.issue import (
                    IssueType,
                    Priority,
                    Status,
                )

                issue_obj = DomainIssue(
                    id=issue_id,
                    title=updates.get("title") or "Untitled",
                    content=updates.get("content") or "",
                    status=updates.get("status") or Status.TODO,
                    priority=Priority.MEDIUM,
                    issue_type=IssueType.FEATURE,
                    labels=updates.get("labels", []),
                    assignee=updates.get("assignee"),
                    milestone=updates.get("milestone"),
                )

            status_val = getattr(issue_obj, "status", None) or Status.TODO
            priority_val = getattr(issue_obj, "priority", None) or Priority.MEDIUM
            issue_type_val = getattr(issue_obj, "issue_type", None) or IssueType.FEATURE
            labels_val = getattr(issue_obj, "labels", []) or []
            assignee_val = getattr(issue_obj, "assignee", None)
            milestone_val = getattr(issue_obj, "milestone", None)

            created_issue = self.core.issues.create(
                title=issue_obj.title,
                status=status_val,
                priority=priority_val,
                assignee=assignee_val,
                milestone=milestone_val,
                issue_type=issue_type_val,
                labels=labels_val,
            )

            if created_issue and github_issue_number is not None:
                IssuePersistenceService.update_issue_with_remote_id(
                    created_issue, "github", str(github_issue_number)
                )
                IssuePersistenceService.save_issue(created_issue, self.core)
                SyncLinkingService.link_issue_in_database(
                    self.remote_link_repo,
                    created_issue.id,
                    "github",
                    github_issue_number,
                )

            logger.debug(
                "github_pull_issue_created",
                github_number=github_issue_number,
                local_id=created_issue.id if created_issue else "unknown",
            )
