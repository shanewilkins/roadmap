"""GitHub sync orchestrator - fetches and detects changes."""

from datetime import datetime
from typing import Any

from roadmap.common.constants import Status
from roadmap.core.domain import Issue
from roadmap.core.services.github_conflict_detector import GitHubConflictDetector
from roadmap.core.services.github_issue_client import GitHubIssueClient
from roadmap.core.services.sync_metadata_service import SyncMetadataService
from roadmap.core.services.sync_report import IssueChange, SyncReport
from roadmap.infrastructure.core import RoadmapCore


class GitHubSyncOrchestrator:
    """Orchestrates fetching GitHub issues and detecting changes."""

    def __init__(self, core: RoadmapCore, config: dict[str, Any] | None = None):
        """Initialize orchestrator with core services.

        Args:
            core: RoadmapCore instance with access to issues and GitHub services
            config: GitHub config dict with token, owner, repo
        """
        self.core = core
        self.config = config or {}
        token = self.config.get("token")
        self.github_client = GitHubIssueClient(token)
        self.metadata_service = SyncMetadataService(core)
        if hasattr(core, "github_service"):
            self.conflict_detector = GitHubConflictDetector(core.github_service)
        else:
            self.conflict_detector = None

    def sync_all_linked_issues(
        self,
        dry_run: bool = True,
        force_local: bool = False,
        force_github: bool = False,
    ) -> SyncReport:
        """Fetch and detect changes for all linked issues, optionally apply them.

        Args:
            dry_run: If True, only detect changes without applying them
            force_local: Resolve conflicts by keeping local changes
            force_github: Resolve conflicts by keeping GitHub changes

        Returns:
            SyncReport with detected changes and conflicts (and applied changes if not dry_run)
        """
        report = SyncReport()

        try:
            # Get all local issues linked to GitHub
            all_issues = self.core.issues.list()
            linked_issues = [i for i in all_issues if i.github_issue is not None]

            report.total_issues = len(linked_issues)

            if not linked_issues:
                report.issues_up_to_date = 0
                return report

            # Fetch current state from GitHub for each linked issue
            for local_issue in linked_issues:
                change = self._detect_issue_changes(local_issue)
                report.changes.append(change)

                # Update counters
                if change.has_conflict:
                    report.conflicts_detected += 1
                elif change.local_changes or change.github_changes:
                    report.issues_updated += 1
                else:
                    report.issues_up_to_date += 1

            # Apply changes if not dry-run
            if not dry_run and (
                force_local or force_github or not report.has_conflicts()
            ):
                for change in report.changes:
                    if change.github_changes and not (
                        change.has_conflict and force_local
                    ):
                        self._apply_github_changes(change)
                    if change.local_changes and not (
                        change.has_conflict and force_github
                    ):
                        self._apply_local_changes(change)

        except Exception as e:
            report.error = str(e)

        return report

    def _detect_issue_changes(self, local_issue: Issue) -> IssueChange:
        """Detect what has changed for a single issue.

        Args:
            local_issue: Local issue to check

        Returns:
            IssueChange with detected changes
        """
        change = IssueChange(
            issue_id=local_issue.id,
            title=local_issue.title,
            last_sync_time=self._get_last_sync_time(local_issue),
        )

        try:
            # Fetch current GitHub issue
            owner = self.config.get("owner")
            repo = self.config.get("repo")
            if not owner or not repo:
                change.github_changes = {
                    "error": "GitHub config incomplete (owner/repo required)"
                }
                return change

            github_issue = self.github_client.fetch_issue(
                owner, repo, local_issue.github_issue
            )
            if not github_issue:
                # GitHub issue was deleted
                change.github_changes = {"issue": "deleted on GitHub"}
                return change

            # Detect local changes
            change.local_changes = self._detect_local_changes(local_issue)

            # Detect GitHub changes
            change.github_changes = self._detect_github_changes(
                local_issue, github_issue
            )

            # Check for conflicts
            if change.local_changes and change.github_changes and change.last_sync_time:
                change.has_conflict = True

        except Exception as e:
            change.github_changes = {"error": f"Failed to fetch: {str(e)}"}

        return change

    def _detect_local_changes(self, issue: Issue) -> dict[str, Any]:
        """Detect what has changed locally since last sync.

        Args:
            issue: Local issue to check

        Returns:
            Dict of field changes
        """
        changes = {}

        # Check if sync metadata exists
        if not hasattr(issue, "github_sync_metadata") or not issue.github_sync_metadata:
            return changes

        # For now, just check status changes
        # This will be enhanced when we add full metadata tracking
        return changes

    def _detect_github_changes(
        self, local_issue: Issue, github_issue: dict[str, Any]
    ) -> dict[str, Any]:
        """Detect what has changed on GitHub since last sync.

        Args:
            local_issue: Local issue for comparison
            github_issue: Current GitHub issue state

        Returns:
            Dict of field changes
        """
        changes = {}

        # Map GitHub status to local status
        github_status = self._map_github_status(github_issue)

        # Check status changes
        if local_issue.status.value != github_status:
            changes["status"] = f"{local_issue.status.value} -> {github_status}"

        # Check title changes
        github_title = github_issue.get("title", "")
        if local_issue.title != github_title:
            changes["title"] = f"{local_issue.title} -> {github_title}"

        # Check description changes
        github_body = github_issue.get("body", "")
        if local_issue.content != github_body:
            changes["description"] = "changed"

        return changes

    def _map_github_status(self, github_issue: dict[str, Any]) -> str:
        """Map GitHub issue state to local status.

        Args:
            github_issue: GitHub issue dict

        Returns:
            Local status value
        """
        github_state = github_issue.get("state", "open")

        if github_state == "closed":
            return Status.DONE.value
        elif github_issue.get("state_reason") == "not_planned":
            return Status.BLOCKED.value
        else:
            # Open issues map to todo for now
            # Could check labels for in-progress, review, etc.
            return Status.TODO.value

    def _get_last_sync_time(self, issue: Issue) -> datetime | None:
        """Get last sync time from issue metadata.

        Args:
            issue: Issue to check

        Returns:
            Last sync datetime or None
        """
        if not hasattr(issue, "github_sync_metadata"):
            return None

        metadata = getattr(issue, "github_sync_metadata", {})
        if not metadata or "last_sync" not in metadata:
            return None

        try:
            sync_str = metadata["last_sync"]
            return datetime.fromisoformat(sync_str)
        except (ValueError, TypeError):
            return None

    def _apply_local_changes(self, change: IssueChange) -> None:
        """Apply local changes to an issue from GitHub.

        Args:
            change: IssueChange with detected changes
        """
        if not change.local_changes:
            return

        try:
            issue = self.core.issues.get(change.issue_id)
            if not issue:
                return

            # Apply status change
            if "status" in change.local_changes:
                new_status = change.local_changes["status"].split(" -> ")[1]
                # Map string to Status enum
                from roadmap.common.constants import Status

                try:
                    issue.status = Status(new_status)
                except (ValueError, KeyError):
                    pass

            # Apply title change
            if "title" in change.local_changes:
                issue.title = change.local_changes["title"].split(" -> ")[1]

            # Apply description change
            if "description" in change.local_changes:
                # Just mark as synced, actual content would be updated via GitHub client
                pass

            # Persist the changes
            from roadmap.core.services.params import IssueUpdateServiceParams

            update_params = IssueUpdateServiceParams(
                id=issue.id,
                title=issue.title if hasattr(issue, "title") else None,
                status=issue.status if hasattr(issue, "status") else None,
            )
            self.core.issues.update_issue(update_params)

            # Record successful sync in metadata
            self.metadata_service.record_sync(
                issue, success=True, github_changes=change.local_changes
            )

        except Exception as e:
            # Record failed sync in metadata
            issue = self.core.issues.get(change.issue_id)
            if issue:
                self.metadata_service.record_sync(
                    issue, success=False, error_message=str(e)
                )
            # Log but don't fail entire sync
            print(f"Failed to apply local changes to {change.issue_id}: {e}")

    def _apply_github_changes(self, change: IssueChange) -> None:
        """Apply GitHub changes to local issue.

        Args:
            change: IssueChange with detected changes
        """
        if not change.github_changes:
            return

        try:
            issue = self.core.issues.get(change.issue_id)
            if not issue:
                return

            # Apply status change from GitHub
            if "status" in change.github_changes:
                new_status = change.github_changes["status"].split(" -> ")[1]
                # Map string to Status enum
                from roadmap.common.constants import Status

                try:
                    issue.status = Status(new_status)
                except (ValueError, KeyError):
                    pass

            # Apply title change from GitHub
            if "title" in change.github_changes:
                issue.title = change.github_changes["title"].split(" -> ")[1]

            # Apply description change from GitHub
            if "description" in change.github_changes:
                # Just mark as synced, actual content would be updated via GitHub client
                pass

            # Persist the changes
            from roadmap.core.services.params import IssueUpdateServiceParams

            update_params = IssueUpdateServiceParams(
                id=issue.id,
                title=issue.title if hasattr(issue, "title") else None,
                status=issue.status if hasattr(issue, "status") else None,
            )
            self.core.issues.update_issue(update_params)

            # Record successful sync in metadata
            self.metadata_service.record_sync(
                issue, success=True, local_changes=change.github_changes
            )

        except Exception as e:
            # Record failed sync in metadata
            issue = self.core.issues.get(change.issue_id)
            if issue:
                self.metadata_service.record_sync(
                    issue, success=False, error_message=str(e)
                )
            # Log but don't fail entire sync
            print(f"Failed to apply GitHub changes to {change.issue_id}: {e}")
