"""Helper functions for GitHub backend synchronization operations."""

from datetime import UTC, datetime
from typing import Any

from structlog import get_logger

from roadmap.common.logging import log_error_with_context

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
        status_map = {
            "open": Status.TODO,
            "closed": Status.CLOSED,
            "todo": Status.TODO,
        }
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

        created = self._parse_timestamp(remote_data.get("created_at")) or datetime.now(
            UTC
        )
        updated = self._parse_timestamp(remote_data.get("updated_at")) or datetime.now(
            UTC
        )

        labels = self._extract_labels(remote_data)
        assignee = self._extract_assignee(remote_data)
        milestone = self._extract_milestone_title(remote_data)

        issue = Issue(
            id=issue_id,
            title=remote_data.get("title", ""),
            status=status,
            priority=Priority.MEDIUM,
            issue_type=IssueType.OTHER,
            created=created,
            updated=updated,
            milestone=milestone,
            assignee=assignee,
            labels=labels,
            content=remote_data.get("body") or "",
        )

        return issue

    def _extract_labels(self, remote_data: dict[str, Any]) -> list[str]:
        labels_data = remote_data.get("labels", [])
        if not isinstance(labels_data, list):
            return []
        return [
            label["name"] if isinstance(label, dict) else str(label)
            for label in labels_data
        ]

    def _extract_assignee(self, remote_data: dict[str, Any]) -> str | None:
        assignees = remote_data.get("assignees", [])
        if isinstance(assignees, list) and assignees:
            first_assignee = assignees[0]
            return (
                first_assignee.get("login")
                if isinstance(first_assignee, dict)
                else str(first_assignee)
            )

        assignee_data = remote_data.get("assignee")
        if not assignee_data:
            return None
        return (
            assignee_data.get("login")
            if isinstance(assignee_data, dict)
            else str(assignee_data)
        )

    def _extract_milestone_title(self, remote_data: dict[str, Any]) -> str | None:
        milestone_data = remote_data.get("milestone")
        if not milestone_data:
            return None
        return (
            milestone_data.get("title")
            if isinstance(milestone_data, dict)
            else str(milestone_data)
        )

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

    def _persist_remote_link(
        self,
        issue,
        github_issue_number: str | int | None,
        persist_svc,
        link_svc,
    ) -> None:
        """Persist the GitHub remote link for an issue."""
        if issue is None or github_issue_number is None:
            return
        persist_svc.update_issue_with_remote_id(
            issue, "github", str(github_issue_number)
        )
        persist_svc.save_issue(issue, self.core)
        link_svc.link_issue_in_database(
            self.remote_link_repo, issue.id, "github", github_issue_number
        )

    def _update_matched_issue(
        self,
        matching_local_issue,
        updates: dict,
        github_issue_number,
        persist_svc,
        link_svc,
    ) -> None:
        """Update an issue found by title/remote-id match."""
        self.core.issues.update(matching_local_issue.id, **updates)
        self._persist_remote_link(
            matching_local_issue, github_issue_number, persist_svc, link_svc
        )
        logger.debug(
            "github_pull_issue_updated",
            github_number=github_issue_number,
            local_id=matching_local_issue.id,
        )

    def _update_issue_by_id(
        self, issue_id: str, updates: dict, github_issue_number, persist_svc, link_svc
    ) -> None:
        """Update an issue found by its local ID."""
        self.core.issues.update(issue_id, **updates)
        local_issue = self.core.issues.get(issue_id)
        self._persist_remote_link(
            local_issue, github_issue_number, persist_svc, link_svc
        )
        logger.debug("github_pull_issue_updated", issue_id=issue_id)

    def _build_domain_issue_fallback(self, issue_id: str, updates: dict):
        """Construct a minimal DomainIssue from raw updates when no remote object exists."""
        from roadmap.core.domain.issue import (
            Issue as DomainIssue,
        )
        from roadmap.core.domain.issue import (
            IssueType,
            Priority,
            Status,
        )

        return DomainIssue(
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

    def _create_new_local_issue(
        self,
        issue_id: str,
        updates: dict,
        remote_issue,
        github_issue_number,
        persist_svc,
        link_svc,
    ) -> None:
        """Create a new local issue from a remote issue or raw updates."""
        from roadmap.core.domain.issue import IssueType, Priority, Status

        issue_obj = (
            self._convert_sync_to_issue(issue_id, remote_issue)
            if remote_issue is not None
            else self._build_domain_issue_fallback(issue_id, updates)
        )

        created_issue = self.core.issues.create(
            title=issue_obj.title,
            status=getattr(issue_obj, "status", None) or Status.TODO,
            priority=getattr(issue_obj, "priority", None) or Priority.MEDIUM,
            assignee=getattr(issue_obj, "assignee", None),
            milestone=getattr(issue_obj, "milestone", None),
            issue_type=getattr(issue_obj, "issue_type", None) or IssueType.FEATURE,
            labels=getattr(issue_obj, "labels", []) or [],
            content=issue_obj.content or updates.get("description") or "",
        )

        self._persist_remote_link(
            created_issue, github_issue_number, persist_svc, link_svc
        )
        logger.debug(
            "github_pull_issue_created",
            github_number=github_issue_number,
            local_id=created_issue.id if created_issue else "unknown",
        )

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

        try:
            if matching_local_issue:
                self._update_matched_issue(
                    matching_local_issue,
                    updates,
                    github_issue_number,
                    IssuePersistenceService,
                    SyncLinkingService,
                )
            elif self.core.issues.get(issue_id):
                self._update_issue_by_id(
                    issue_id,
                    updates,
                    github_issue_number,
                    IssuePersistenceService,
                    SyncLinkingService,
                )
            else:
                self._create_new_local_issue(
                    issue_id,
                    updates,
                    remote_issue,
                    github_issue_number,
                    IssuePersistenceService,
                    SyncLinkingService,
                )
        except Exception as e:
            log_error_with_context(
                e,
                operation="pull_apply_or_create",
                entity_type="Issue",
                entity_id=str(issue_id),
                include_traceback=True,
            )
            raise
