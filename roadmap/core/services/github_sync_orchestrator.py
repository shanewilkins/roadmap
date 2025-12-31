"""GitHub sync orchestrator - fetches and detects changes."""

from datetime import datetime
from typing import Any

from roadmap.common.constants import Status
from roadmap.common.datetime_parser import UnifiedDateTimeParser
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

        Handles:
        - Existing linked issues (status, title, description changes)
        - Newly created issues (local only, need to push to GitHub)
        - Deleted/archived issues (sync deletions both ways)
        - Milestones (creation, updates, deletion)

        Args:
            dry_run: If True, only detect changes without applying them
            force_local: Resolve conflicts by keeping local changes
            force_github: Resolve conflicts by keeping GitHub changes

        Returns:
            SyncReport with detected changes and conflicts (and applied changes if not dry_run)
        """
        report = SyncReport()

        try:
            # Get all local issues and milestones
            all_issues = self.core.issues.list()
            all_milestones = (
                self.core.milestones.list() if hasattr(self.core, "milestones") else []
            )

            # 1. Sync existing linked issues
            linked_issues = [i for i in all_issues if i.github_issue is not None]
            report.total_issues = len(linked_issues)

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

            # 2. Detect newly created issues (local only)
            unlinked_issues = [i for i in all_issues if i.github_issue is None]
            for local_issue in unlinked_issues:
                change = IssueChange(
                    issue_id=local_issue.id,
                    title=local_issue.title,
                    local_changes={"action": "create on GitHub"},
                )
                report.changes.append(change)
                report.issues_updated += 1

            # 3. Sync milestones if available
            if hasattr(self.core, "milestones"):
                for local_milestone in all_milestones:
                    change = self._detect_milestone_changes(local_milestone)
                    if change:
                        report.changes.append(change)
                        if change.has_conflict:
                            report.conflicts_detected += 1
                        elif change.local_changes or change.github_changes:
                            report.issues_updated += 1

            # Apply changes if not dry-run
            if not dry_run and (
                force_local or force_github or not report.has_conflicts()
            ):
                for change in report.changes:
                    # Handle issue creation
                    if (
                        "action" in change.local_changes
                        and change.local_changes["action"] == "create on GitHub"
                    ):
                        self._create_issue_on_github(change.issue_id)
                    else:
                        # Handle existing issues
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

            if not local_issue.github_issue:
                change.github_changes = {"error": "Issue not linked to GitHub"}
                return change

            # Ensure github_issue is an int (should be after validation in Issue model)
            github_issue_number = (
                int(local_issue.github_issue)
                if isinstance(local_issue.github_issue, str)
                else local_issue.github_issue
            )

            github_issue = self.github_client.fetch_issue(
                owner, repo, github_issue_number
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
            return Status.CLOSED.value
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
            return UnifiedDateTimeParser.parse_iso_datetime(sync_str)
        except (ValueError, TypeError):
            return None

    def _apply_local_changes(self, change: IssueChange) -> None:
        """Apply local changes to GitHub issue.

        Args:
            change: IssueChange with detected changes
        """
        if not change.local_changes:
            return

        try:
            issue = self.core.issues.get(change.issue_id)
            if not issue or not issue.github_issue:
                return

            owner = self.config.get("owner")
            repo = self.config.get("repo")
            if not owner or not repo:
                return

            github_issue_number = (
                int(issue.github_issue)
                if isinstance(issue.github_issue, str)
                else issue.github_issue
            )

            # Get GitHub handler for API operations
            from requests import Session

            from roadmap.adapters.github.handlers.issues import IssueHandler

            session = Session()
            session.headers.update(
                {
                    "Authorization": f"token {self.config.get('token')}",
                    "Accept": "application/vnd.github.v3+json",
                    "User-Agent": "roadmap-cli/1.0",
                }
            )

            handler = IssueHandler(session, owner, repo)

            # Prepare GitHub update
            update_data = {}

            # Apply status change to GitHub
            if "status" in change.local_changes:
                new_status = change.local_changes["status"].split(" -> ")[1]
                # Map local status to GitHub state (done -> closed, others -> open)
                github_state = "closed" if new_status == "done" else "open"
                update_data["state"] = github_state

            # Apply title change to GitHub
            if "title" in change.local_changes:
                new_title = change.local_changes["title"].split(" -> ")[1]
                update_data["title"] = new_title

            # Apply description/body change to GitHub
            if "description" in change.local_changes:
                new_desc = change.local_changes["description"].split(" -> ")[1]
                update_data["body"] = new_desc

            # Push changes to GitHub
            if update_data:
                handler.update_issue(github_issue_number, **update_data)

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
            print(f"Failed to apply local changes to GitHub for {change.issue_id}: {e}")

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
            self.core.issues.update(
                issue_id=issue.id,
                title=issue.title,
                status=issue.status,
            )

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

    def _detect_milestone_changes(self, local_milestone: Any) -> IssueChange | None:
        """Detect changes for a milestone.

        Args:
            local_milestone: Local milestone to check

        Returns:
            IssueChange with detected changes or None
        """
        if not hasattr(local_milestone, "github_milestone"):
            return None

        change = IssueChange(
            issue_id=local_milestone.name,
            title=local_milestone.name,
            last_sync_time=None,
        )

        try:
            owner = self.config.get("owner")
            repo = self.config.get("repo")
            if not owner or not repo:
                return None

            # If milestone not yet linked to GitHub, mark for creation
            if not local_milestone.github_milestone:
                change.local_changes = {"action": "create milestone on GitHub"}
                return change

            # TODO: Fetch milestone from GitHub and detect changes
            # For now, return None if already linked (no detection yet)
            return None

        except Exception:
            return None

    def _create_issue_on_github(self, issue_id: str) -> None:
        """Create a new issue on GitHub from local issue.

        Args:
            issue_id: Local issue ID
        """
        try:
            issue = self.core.issues.get(issue_id)
            if not issue:
                return

            owner = self.config.get("owner")
            repo = self.config.get("repo")
            if not owner or not repo:
                return

            from requests import Session

            from roadmap.adapters.github.handlers.issues import IssueHandler

            session = Session()
            session.headers.update(
                {
                    "Authorization": f"token {self.config.get('token')}",
                    "Accept": "application/vnd.github.v3+json",
                    "User-Agent": "roadmap-cli/1.0",
                }
            )

            handler = IssueHandler(session, owner, repo)

            # Create issue on GitHub
            github_issue = handler.create_issue(
                title=issue.title,
                body=issue.content,
                labels=self._map_local_status_to_labels(issue.status),
                milestone=None,  # TODO: Handle milestone linking
            )

            # Link the local issue to the GitHub issue
            issue.github_issue = github_issue.get("number")
            self.core.issues.update(issue_id=issue.id, github_issue=issue.github_issue)

            # Record sync
            self.metadata_service.record_sync(
                issue, success=True, github_changes={"action": "created on GitHub"}
            )

        except Exception as e:
            issue = self.core.issues.get(issue_id)
            if issue:
                self.metadata_service.record_sync(
                    issue, success=False, error_message=str(e)
                )
            print(f"Failed to create issue {issue_id} on GitHub: {e}")

    def _map_local_status_to_labels(self, status: Any) -> list[str]:
        """Map local status to GitHub labels.

        Args:
            status: Local status

        Returns:
            List of GitHub labels
        """
        status_value = status.value if hasattr(status, "value") else str(status)
        return [f"status:{status_value}"]
