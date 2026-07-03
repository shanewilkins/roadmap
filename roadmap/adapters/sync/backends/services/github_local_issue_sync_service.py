"""Local issue persistence and remote-link synchronization helpers."""

from __future__ import annotations

from typing import Any

from structlog import get_logger

logger = get_logger()


class GitHubLocalIssueSyncService:
    """Handles local DB persistence and GitHub remote-link associations."""

    def __init__(self, backend: Any):
        """Initialize the local issue sync service for a backend instance."""
        self.backend = backend

    def persist_issue_before_linking(self, issue: Any, issue_id: str) -> bool:
        """Persist issue to database before linking to GitHub."""
        if not hasattr(self.backend, "core") or not self.backend.core:
            return True

        try:
            issue_repo = self.backend.core.db.get_issue_repository()
            existing = issue_repo.get(issue_id)

            if not existing:
                issue_data = {
                    "id": issue_id,
                    "title": issue.title,
                    "headline": getattr(issue, "headline", ""),
                    "description": issue.content or "",
                    "status": str(issue.status),
                    "priority": str(issue.priority),
                    "issue_type": str(issue.type) if hasattr(issue, "type") else "task",
                    "assignee": issue.assignee,
                    "estimate_hours": issue.estimated_hours
                    if hasattr(issue, "estimated_hours")
                    else None,
                    "due_date": None,
                    "project_id": None,
                }
                issue_repo.create(issue_data)
                logger.info(
                    "persisted_issue_for_linking",
                    issue_id=issue_id,
                    title=issue.title,
                )
        except Exception as e:
            logger.warning(
                "failed_to_persist_issue_before_linking",
                issue_id=issue_id,
                error=str(e),
                severity="operational",
            )

        return True

    def link_issue_to_github(
        self, issue_uuid: str, github_number: int
    ) -> tuple[bool, str | None]:
        """Link issue to GitHub in database."""
        if not hasattr(self.backend, "core") or not self.backend.core:
            return True, None

        try:
            self.backend.core.db.remote_links.link_issue(
                issue_uuid=issue_uuid,
                backend_name="github",
                remote_id=str(github_number),
            )
            logger.info(
                "github_issue_linked",
                issue_id=issue_uuid,
                github_number=github_number,
            )
            return True, None
        except Exception as e:
            logger.warning(
                "github_issue_link_failed",
                issue_id=issue_uuid,
                github_number=github_number,
                error=str(e),
                severity="operational",
            )
            return False, str(e)

    def get_project_id_for_synced_issue(self) -> str | None:
        """Get default project ID for synced issues."""
        if not hasattr(self.backend, "core") or not self.backend.core:
            return None

        try:
            projects = list(self.backend.core.projects.list())
            return projects[0].id if projects else None
        except Exception as e:
            logger.warning(
                "failed_to_get_projects_for_issue",
                error=str(e),
                severity="operational",
            )
            return None

    def resolve_local_issue_id(
        self, github_id: str | int | None, local_issue: Any
    ) -> str:
        """Resolve local issue ID from remote link mapping when available."""
        if github_id is None:
            return local_issue.id

        if not hasattr(self.backend, "core") or not self.backend.core:
            return local_issue.id

        try:
            issue_uuid = self.backend.core.db.remote_links.get_issue_uuid(
                backend_name="github", remote_id=github_id
            )
            if issue_uuid:
                return issue_uuid
        except Exception as e:
            logger.warning(
                "github_remote_link_lookup_failed",
                github_number=github_id,
                error=str(e),
                severity="operational",
            )

        return local_issue.id

    def create_or_update_issue_locally(
        self, sync_issue: Any, local_issue: Any, github_id: str | int | None
    ) -> str | None:
        """Create or update issue in local database."""
        if not hasattr(self.backend, "core") or not self.backend.core:
            return local_issue.id

        issue_repo = self.backend.core.db.get_issue_repository()
        local_issue_id = self.resolve_local_issue_id(github_id, local_issue)
        existing = issue_repo.get(local_issue_id)
        project_id = (
            existing.get("project_id")
            if existing
            else self.get_project_id_for_synced_issue()
        )

        if existing:
            updates = {
                "title": local_issue.title,
                "headline": local_issue.headline,
                "description": local_issue.content or "",
                "status": str(local_issue.status),
                "priority": str(local_issue.priority),
                "issue_type": str(local_issue.issue_type),
                "assignee": local_issue.assignee,
                "estimate_hours": local_issue.estimated_hours,
                "due_date": None,
            }
            if project_id:
                updates["project_id"] = project_id

            issue_repo.update(local_issue_id, updates)
            logger.info(
                "github_issue_updated_locally",
                issue_id=local_issue_id,
                github_number=github_id,
                title=local_issue.title,
            )
        else:
            issue_data = {
                "id": local_issue_id,
                "title": local_issue.title,
                "headline": local_issue.headline,
                "description": local_issue.content or "",
                "status": str(local_issue.status),
                "priority": str(local_issue.priority),
                "issue_type": str(local_issue.issue_type),
                "project_id": project_id,
                "assignee": local_issue.assignee,
                "estimate_hours": local_issue.estimated_hours,
                "due_date": None,
            }
            issue_repo.create(issue_data)
            logger.info(
                "github_issue_created_locally",
                issue_id=local_issue_id,
                github_number=github_id,
                title=local_issue.title,
            )

        return local_issue_id

    def link_pulled_issue_locally(
        self, local_issue_id: str | None, github_id: str | int | None
    ) -> bool:
        """Link pulled issue to GitHub in local database."""
        if not hasattr(self.backend, "core") or not self.backend.core:
            return True

        if not local_issue_id or github_id is None:
            logger.warning(
                "github_issue_link_skipped_missing_ids",
                issue_id=local_issue_id,
                github_number=github_id,
                severity="data_error",
            )
            return True

        try:
            self.backend.core.db.remote_links.link_issue(
                issue_uuid=local_issue_id,
                backend_name="github",
                remote_id=str(github_id),
            )
            logger.info(
                "github_issue_linked_locally",
                issue_id=local_issue_id,
                github_number=github_id,
            )
            return True
        except Exception as e:
            logger.warning(
                "github_issue_link_failed",
                issue_id=local_issue_id,
                github_number=github_id,
                error=str(e),
                severity="operational",
            )
            return True
