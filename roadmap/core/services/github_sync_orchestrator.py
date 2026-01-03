"""GitHub sync orchestrator - fetches and detects changes."""

from datetime import datetime
from typing import Any

from roadmap.common.constants import Status
from roadmap.common.datetime_parser import UnifiedDateTimeParser
from roadmap.core.domain import Issue
from roadmap.core.services.github_conflict_detector import GitHubConflictDetector
from roadmap.core.services.github_entity_classifier import GitHubEntityClassifier
from roadmap.core.services.github_issue_client import GitHubIssueClient
from roadmap.core.services.helpers import (
    extract_issue_status_update,
    extract_milestone_status_update,
    parse_status_change,
)
from roadmap.core.services.sync.conflict_resolver import ConflictResolver
from roadmap.core.services.sync.three_way_merger import ThreeWayMerger
from roadmap.core.services.sync_metadata_service import SyncMetadataService
from roadmap.core.services.sync_report import IssueChange, SyncReport
from roadmap.core.services.sync_state_manager import SyncStateManager
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
        self.entity_classifier = GitHubEntityClassifier()
        self.three_way_merger = ThreeWayMerger()
        self.conflict_resolver = ConflictResolver()
        self.state_manager = SyncStateManager(core.roadmap_dir)
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
            # Load all issues and milestones
            all_issues = self.core.issues.list()
            all_milestones = self._load_milestones()

            # Classify into active/archived
            active_issues, archived_issues = self.entity_classifier.separate_by_state(
                all_issues
            )
            active_milestones, archived_milestones = (
                self.entity_classifier.separate_by_state(all_milestones)
            )

            # Detect changes for active issues and milestones
            self._detect_and_report_linked_issues(report, active_issues)
            self._detect_and_report_unlinked_issues(report, active_issues)
            self._detect_and_report_archived_issues(report, archived_issues)
            self._detect_and_report_milestones(report, active_milestones)
            self._detect_and_report_archived_milestones(report, archived_milestones)

            # Apply changes if not dry-run
            if not dry_run and (
                force_local or force_github or not report.has_conflicts()
            ):
                self._apply_all_changes(
                    report, force_local=force_local, force_github=force_github
                )

        except Exception as e:
            report.error = str(e)

        return report

    def push_local_changes(
        self, dry_run: bool = True, force_github: bool = False
    ) -> SyncReport:
        """Push local changes to GitHub (PUSH Phase).

        Detects which issues changed locally (using git diff), then pushes
        those changes to GitHub API. Handles conflicts that GitHub might report.

        Args:
            dry_run: If True, only detect changes without applying them
            force_github: If True, overwrite GitHub changes with local versions

        Returns:
            SyncReport with push results
        """
        report = SyncReport()

        try:
            # Get list of locally changed issue IDs
            git_coordinator = getattr(self.core, "git_coordinator", None)
            if not git_coordinator:
                report.error = "Git coordinator not available"
                return report

            changed_issue_ids = git_coordinator.get_local_changes()
            if not changed_issue_ids:
                report.issues_up_to_date = 1  # Everything is in sync
                return report

            # For each changed issue, fetch it and push to GitHub
            for issue_id in changed_issue_ids:
                try:
                    local_issue = self.core.issues.get(issue_id)
                    if not local_issue:
                        continue

                    # If not linked to GitHub, we'd need to create it (separate action)
                    if not local_issue.github_issue:
                        report.changes.append(
                            IssueChange(
                                issue_id=issue_id,
                                title=local_issue.title,
                                local_changes={"action": "create on GitHub"},
                            )
                        )
                        report.issues_updated += 1
                        continue

                    # Fetch current GitHub state
                    owner = self.config.get("owner")
                    repo = self.config.get("repo")
                    if not owner or not repo:
                        continue

                    github_issue_number = (
                        int(local_issue.github_issue)
                        if isinstance(local_issue.github_issue, str)
                        else local_issue.github_issue
                    )

                    github_issue = self.github_client.fetch_issue(
                        owner, repo, github_issue_number
                    )
                    if not github_issue:
                        # Issue was deleted on GitHub
                        report.changes.append(
                            IssueChange(
                                issue_id=issue_id,
                                title=local_issue.title,
                                github_changes={"issue": "deleted on GitHub"},
                            )
                        )
                        continue

                    # Detect what changed locally
                    local_changes = self._detect_local_changes(local_issue)
                    if not local_changes:
                        report.issues_up_to_date += 1
                        continue

                    # Create change record
                    change = IssueChange(
                        issue_id=issue_id,
                        title=local_issue.title,
                        local_changes=local_changes,
                    )

                    # If not dry-run, push to GitHub
                    if not dry_run:
                        self._push_issue_to_github(change, local_issue, github_issue)

                    report.changes.append(change)
                    report.issues_updated += 1

                except Exception as e:
                    report.changes.append(
                        IssueChange(
                            issue_id=issue_id,
                            title=local_issue.title if local_issue else issue_id,
                            github_changes={"error": f"Push failed: {str(e)}"},
                        )
                    )

        except Exception as e:
            report.error = str(e)

        return report

    def _push_issue_to_github(
        self, change: IssueChange, local_issue: Issue, github_issue: dict[str, Any]
    ) -> None:
        """Push a local issue's changes to GitHub.

        Args:
            change: IssueChange record to update
            local_issue: Local issue with changes
            github_issue: Current GitHub issue state
        """
        try:
            owner = self.config.get("owner")
            repo = self.config.get("repo")
            if not owner or not repo:
                change.github_changes = {
                    "error": "GitHub config incomplete (owner/repo required)"
                }
                return

            # Record what would be pushed (placeholder implementation)
            # Full implementation requires GitHub API update methods

            # Track title change
            if local_issue.title != github_issue.get("title"):
                change.github_changes["title"] = "would be updated"

            # Track description change
            if local_issue.content != github_issue.get("body"):
                change.github_changes["description"] = "would be updated"

            # Track status change
            local_status = (
                local_issue.status.value if local_issue.status else "unknown"
            )
            github_status = self._map_github_status(github_issue)
            if local_status != github_status:
                github_state = (
                    "closed"
                    if local_status in ("closed", "completed")
                    else "open"
                )
                change.github_changes[
                    "status"
                ] = f"would be updated to {github_state}"

        except Exception as e:
            change.github_changes = {"error": f"Push failed: {str(e)}"}

    def _load_milestones(self) -> list[Any]:
        """Load all milestones if available.

        Returns:
            List of milestones, or empty list if not available
        """
        all_milestones = []
        if hasattr(self.core, "milestones"):
            try:
                milestone_list = self.core.milestones.list()
                if milestone_list and hasattr(milestone_list, "__iter__"):
                    all_milestones = list(milestone_list)
            except (AttributeError, TypeError):
                pass
        return all_milestones

    def _detect_and_report_linked_issues(
        self, report: SyncReport, active_issues: list[Issue]
    ) -> None:
        """Detect and report changes for linked issues.

        Args:
            report: SyncReport to update
            active_issues: List of active issues
        """
        linked_issues = [i for i in active_issues if i.github_issue is not None]
        report.total_issues = len(linked_issues)

        for local_issue in linked_issues:
            change = self._detect_issue_changes(local_issue)
            report.changes.append(change)
            self._update_report_counters(report, change)

    def _detect_and_report_unlinked_issues(
        self, report: SyncReport, active_issues: list[Issue]
    ) -> None:
        """Detect and report new issues not yet linked to GitHub.

        Args:
            report: SyncReport to update
            active_issues: List of active issues
        """
        unlinked_issues = [i for i in active_issues if i.github_issue is None]

        for local_issue in unlinked_issues:
            change = IssueChange(
                issue_id=local_issue.id,
                title=local_issue.title,
                local_changes={"action": "create on GitHub"},
            )
            report.changes.append(change)
            report.issues_updated += 1

    def _detect_and_report_archived_issues(
        self, report: SyncReport, archived_issues: list[Issue]
    ) -> None:
        """Detect and report archived issues to sync.

        Args:
            report: SyncReport to update
            archived_issues: List of archived issues
        """
        for archived_issue in archived_issues:
            if archived_issue.github_issue is not None:
                change = IssueChange(
                    issue_id=archived_issue.id,
                    title=archived_issue.title,
                    local_changes={
                        "action": "archive",
                        "archived": "archived locally",
                    },
                )
                report.changes.append(change)
                report.issues_updated += 1

    def _detect_and_report_milestones(
        self, report: SyncReport, active_milestones: list[Any]
    ) -> None:
        """Detect and report changes for active milestones.

        Args:
            report: SyncReport to update
            active_milestones: List of active milestones
        """
        for local_milestone in active_milestones:
            change = self._detect_milestone_changes(local_milestone)
            if change:
                report.changes.append(change)
                self._update_report_counters(report, change)

    def _detect_and_report_archived_milestones(
        self, report: SyncReport, archived_milestones: list[Any]
    ) -> None:
        """Detect and report archived milestones to sync.

        Args:
            report: SyncReport to update
            archived_milestones: List of archived milestones
        """
        for archived_milestone in archived_milestones:
            if archived_milestone.github_milestone is not None:
                change = IssueChange(
                    issue_id=archived_milestone.name,
                    title=archived_milestone.name,
                    local_changes={
                        "action": "archive",
                        "archived": "archived locally",
                    },
                )
                report.changes.append(change)
                report.issues_updated += 1

    def _update_report_counters(self, report: SyncReport, change: IssueChange) -> None:
        """Update sync report counters based on change.

        Args:
            report: SyncReport to update
            change: Detected change
        """
        if change.has_conflict:
            report.conflicts_detected += 1
        elif change.local_changes or change.github_changes:
            report.issues_updated += 1
        else:
            report.issues_up_to_date += 1

    def _apply_all_changes(
        self,
        report: SyncReport,
        force_local: bool = False,
        force_github: bool = False,
    ) -> None:
        """Apply all detected changes to local and GitHub.

        Args:
            report: SyncReport containing detected changes
            force_local: If True, resolve conflicts by keeping local
            force_github: If True, resolve conflicts by keeping GitHub
        """
        for change in report.changes:
            # Determine if this is an issue or milestone
            is_milestone = self._is_milestone_change(change)

            if is_milestone:
                self._apply_milestone_change(
                    change, force_local=force_local, force_github=force_github
                )
            else:
                self._apply_issue_change(
                    change, force_local=force_local, force_github=force_github
                )

    def _is_milestone_change(self, change: IssueChange) -> bool:
        """Determine if change is for a milestone or issue.

        Args:
            change: Change to check

        Returns:
            True if milestone change, False if issue change
        """
        # Try to get as issue
        issue_obj = self.core.issues.get(change.issue_id)
        if issue_obj is not None:
            return False

        # Try as milestone
        if hasattr(self.core, "milestones"):
            try:
                milestone_obj = self.core.milestones.get(change.issue_id)
                return milestone_obj is not None and hasattr(milestone_obj, "name")
            except (AttributeError, TypeError):
                pass

        return False

    def _apply_milestone_change(
        self,
        change: IssueChange,
        force_local: bool = False,
        force_github: bool = False,
    ) -> None:
        """Apply changes to a milestone.

        Args:
            change: Change to apply
            force_local: If True, prioritize local changes
            force_github: If True, prioritize GitHub changes
        """
        if "action" in change.local_changes:
            action = change.local_changes["action"]
            if action == "archive":
                self._apply_archived_milestone_to_github(change.issue_id)
            elif action == "restore":
                self._apply_restored_milestone_to_github(change.issue_id)
            elif action == "create_milestone":
                self._create_milestone_on_github(change.issue_id)
        else:
            # Handle milestone updates
            if change.github_changes and not (change.has_conflict and force_local):
                self._apply_github_milestone_changes(change)
            if change.local_changes and not (change.has_conflict and force_github):
                self._apply_local_milestone_changes(change)

    def _apply_issue_change(
        self,
        change: IssueChange,
        force_local: bool = False,
        force_github: bool = False,
    ) -> None:
        """Apply changes to an issue.

        Args:
            change: Change to apply
            force_local: If True, prioritize local changes
            force_github: If True, prioritize GitHub changes
        """
        if "action" in change.local_changes:
            action = change.local_changes["action"]
            if action == "archive":
                self._apply_archived_issue_to_github(change.issue_id)
            elif action == "restore":
                self._apply_restored_issue_to_github(change.issue_id)
            elif action == "create on GitHub":
                self._create_issue_on_github(change.issue_id)
        else:
            # Handle issue updates
            if change.github_changes and not (change.has_conflict and force_local):
                self._apply_github_changes(change)
            if change.local_changes and not (change.has_conflict and force_github):
                self._apply_local_changes(change)

    def _detect_issue_changes(self, local_issue: Issue) -> IssueChange:
        """Detect what has changed for a single issue using three-way merge.

        Uses the three-way merge algorithm (base vs local vs remote) to intelligently
        determine whether changes conflict or can be auto-resolved.

        Args:
            local_issue: Local issue to check

        Returns:
            IssueChange with detected changes and conflict status
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

            # Ensure github_issue is an int
            github_issue_number = (
                int(local_issue.github_issue)
                if isinstance(local_issue.github_issue, str)
                else local_issue.github_issue
            )

            # Fetch the remote GitHub issue
            github_issue = self.github_client.fetch_issue(
                owner, repo, github_issue_number
            )
            if not github_issue:
                # GitHub issue was deleted
                change.github_changes = {"issue": "deleted on GitHub"}
                return change

            # Load the base state (last agreed-upon state from .sync-state.json)
            sync_state = self.state_manager.load_sync_state()
            base_state = None
            if sync_state and local_issue.id in sync_state.issues:
                base_state = sync_state.issues[local_issue.id]

            # Perform three-way merge for each field
            merged_issue, flagged_conflicts = self._merge_issue_fields(
                local_issue, github_issue, base_state
            )

            # Set change details
            if flagged_conflicts:
                change.has_conflict = True
                change.flagged_conflicts = flagged_conflicts
            else:
                change.has_conflict = False

            # Compare to detect what actually changed
            local_changes = self._detect_local_changes(local_issue)
            github_changes = self._detect_github_changes(local_issue, github_issue)

            if local_changes:
                change.local_changes = local_changes
            if github_changes:
                change.github_changes = github_changes

        except Exception as e:
            change.github_changes = {"error": f"Failed to fetch: {str(e)}"}

        return change

    def _merge_issue_fields(
        self, local_issue: Issue, github_issue: dict[str, Any], base_state: Any
    ) -> tuple[Issue, dict[str, Any]]:
        """Merge issue fields using three-way merge logic.

        Args:
            local_issue: Current local issue
            github_issue: Current GitHub issue state
            base_state: Last agreed-upon state (from sync-state.json)

        Returns:
            (merged_issue, flagged_conflicts)
            where flagged_conflicts is a dict of fields that need manual review
        """
        # For fields we track, perform three-way merge
        fields_to_merge = ["status", "assignee", "milestone", "labels", "description"]
        flagged_conflicts = {}

        for field in fields_to_merge:
            # Get values from each source
            base_val = getattr(base_state, field, None) if base_state else None
            local_val = self._get_issue_field(local_issue, field)
            remote_val = self._get_github_field(github_issue, field)

            # Perform three-way merge
            merge_result = self.three_way_merger.merge_field(
                field, base_val, local_val, remote_val
            )

            # If clean, the merge result is the value to use
            # If conflict, apply conflict resolver
            if merge_result.is_conflict():
                resolved_val, is_flagged = self.conflict_resolver.resolve_conflict(
                    field, base_val, local_val, remote_val
                )
                if is_flagged:
                    flagged_conflicts[field] = {
                        "base": base_val,
                        "local": local_val,
                        "remote": remote_val,
                        "reason": merge_result.reason,
                    }

        return local_issue, flagged_conflicts

    def _get_issue_field(self, issue: Issue, field: str) -> Any:
        """Get a field value from an Issue object.

        Args:
            issue: Issue to get field from
            field: Field name

        Returns:
            Field value or None
        """
        if field == "status":
            return issue.status.value if issue.status else None
        elif field == "assignee":
            return issue.assignee
        elif field == "milestone":
            return issue.milestone if hasattr(issue, "milestone") else None
        elif field == "labels":
            return issue.labels or []
        elif field == "description":
            return issue.content or ""
        else:
            return getattr(issue, field, None)

    def _get_github_field(self, github_issue: dict[str, Any], field: str) -> Any:
        """Get a field value from a GitHub issue dict.

        Args:
            github_issue: GitHub issue dict from API
            field: Field name

        Returns:
            Field value or None
        """
        if field == "status":
            return self._map_github_status(github_issue)
        elif field == "assignee":
            assignee_obj = github_issue.get("assignee")
            return assignee_obj.get("login") if assignee_obj else None
        elif field == "milestone":
            milestone_obj = github_issue.get("milestone")
            return milestone_obj.get("title") if milestone_obj else None
        elif field == "labels":
            labels_obj = github_issue.get("labels", [])
            return [
                label.get("name") if isinstance(label, dict) else str(label)
                for label in labels_obj
            ]
        elif field == "description":
            return github_issue.get("body", "")
        else:
            return github_issue.get(field)

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

        # Check archived status changes
        # If issue is closed/completed locally, mark for closure on GitHub
        if issue.status.value in ("closed", "completed"):
            changes["archived"] = "archived locally"

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

    def _get_issue_handler(self, owner: str, repo: str) -> Any:
        """Create and return a GitHub issue handler.

        Args:
            owner: Repository owner
            repo: Repository name

        Returns:
            IssueHandler instance
        """
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
        return IssueHandler(session, owner, repo)

    def _get_milestone_handler(self, owner: str, repo: str) -> Any:
        """Create and return a GitHub milestone handler.

        Args:
            owner: Repository owner
            repo: Repository name

        Returns:
            MilestoneHandler instance
        """
        from requests import Session

        from roadmap.adapters.github.handlers.milestones import MilestoneHandler

        session = Session()
        session.headers.update(
            {
                "Authorization": f"token {self.config.get('token')}",
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "roadmap-cli/1.0",
            }
        )
        return MilestoneHandler(session, owner, repo)

    def _get_owner_repo(self) -> tuple[str, str] | None:
        """Extract and validate owner and repo from config.

        Returns:
            Tuple of (owner, repo) or None if either is missing
        """
        owner = self.config.get("owner")
        repo = self.config.get("repo")
        if not owner or not repo:
            return None
        return (owner, repo)

    def _extract_status_update(self, status_change: str) -> dict[str, Any] | None:
        """Extract and validate status update from change string.

        Args:
            status_change: Change string in format "old -> new"

        Returns:
            Dict with 'github_state' and 'status_enum', or None if invalid
        """
        return extract_issue_status_update(status_change)

    def _extract_milestone_status_update(
        self, status_change: str
    ) -> dict[str, Any] | None:
        """Extract and validate milestone status update from change string.

        Args:
            status_change: Change string in format "old -> new"

        Returns:
            Dict with 'github_state' and 'status_enum', or None if invalid
        """
        return extract_milestone_status_update(status_change)

    def _parse_status_change(self, change_str: str) -> str | None:
        """Parse and validate change string in format 'old -> new'.

        Args:
            change_str: Change string in format "old -> new"

        Returns:
            The new status string, or None if format is invalid
        """
        return parse_status_change(change_str)

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
            handler = self._get_issue_handler(owner, repo)

            # Prepare GitHub update
            update_data = {}

            # Apply status change to GitHub and locally
            if "status" in change.local_changes:
                status_update = self._extract_status_update(
                    change.local_changes["status"]
                )
                if status_update:
                    update_data["state"] = status_update["github_state"]
                    issue.status = status_update["status_enum"]

            # Apply title change to GitHub and locally
            if "title" in change.local_changes:
                new_title = change.local_changes["title"].split(" -> ")[1]
                update_data["title"] = new_title
                issue.title = new_title

            # Apply description/body change to GitHub and locally
            if "description" in change.local_changes:
                new_desc = change.local_changes["description"].split(" -> ")[1]
                update_data["body"] = new_desc
                issue.content = new_desc

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
        if not hasattr(local_milestone, "name"):
            return None

        change = IssueChange(
            issue_id=local_milestone.name,
            title=local_milestone.name,
            last_sync_time=None,
        )

        try:
            owner_repo = self._get_owner_repo()
            if not owner_repo:
                return None
            owner, repo = owner_repo

            # If milestone not yet linked to GitHub, mark for creation
            if not hasattr(local_milestone, "github_milestone") or (
                not local_milestone.github_milestone
            ):
                change.local_changes = {"action": "create_milestone"}
                return change

            # Milestone exists on GitHub - detect local changes
            handler = self._get_milestone_handler(owner, repo)

            # Fetch milestone from GitHub
            gh_milestone = handler.get_milestone(local_milestone.github_milestone)

            # Compare fields to detect changes
            changes = {}

            if local_milestone.name != gh_milestone.get("title"):
                changes["title"] = (
                    f"{gh_milestone.get('title')} -> {local_milestone.name}"
                )

            if local_milestone.description != gh_milestone.get("description", ""):
                changes["description"] = (
                    f"{gh_milestone.get('description', '')} -> "
                    f"{local_milestone.description}"
                )

            # Map local status to GitHub state
            local_state = (
                "closed" if local_milestone.status.value == "closed" else "open"
            )
            gh_state = gh_milestone.get("state", "open")
            if local_state != gh_state:
                changes["status"] = f"{gh_state} -> {local_state}"

            if changes:
                change.local_changes = changes
                return change

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

            handler = self._get_issue_handler(owner, repo)

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

    def _create_milestone_on_github(self, milestone_name: str) -> None:
        """Create a new milestone on GitHub from local milestone.

        Args:
            milestone_name: Local milestone name
        """
        try:
            milestone = self.core.milestones.get(milestone_name)
            if not milestone:
                return

            owner_repo = self._get_owner_repo()
            if not owner_repo:
                return
            owner, repo = owner_repo

            handler = self._get_milestone_handler(owner, repo)

            # Create milestone on GitHub
            github_milestone = handler.create_milestone(
                title=milestone.name,
                description=milestone.description,
                due_date=milestone.due_date,
                state="closed" if milestone.status.value == "closed" else "open",
            )

            # Link the local milestone to the GitHub milestone
            milestone.github_milestone = github_milestone.get("number")
            # Note: Milestone link will be persisted on next save

        except Exception as e:
            print(f"Failed to create milestone {milestone_name} on GitHub: {e}")

    def _apply_local_milestone_changes(self, change: IssueChange) -> None:
        """Apply local milestone changes to GitHub.

        Args:
            change: IssueChange with detected changes
        """
        if not change.local_changes:
            return

        try:
            milestone = self.core.milestones.get(change.issue_id)
            if not milestone:
                return

            # Handle milestone creation
            if change.local_changes.get("action") == "create_milestone":
                self._create_milestone_on_github(change.issue_id)
                return

            # Handle milestone updates
            if not milestone.github_milestone:
                return

            owner = self.config.get("owner")
            repo = self.config.get("repo")
            if not owner or not repo:
                return

            handler = self._get_milestone_handler(owner, repo)

            # Prepare milestone update
            update_data = {}

            # Apply title change
            if "title" in change.local_changes:
                new_title = change.local_changes["title"].split(" -> ")[1]
                update_data["title"] = new_title
                milestone.name = new_title

            # Apply description change
            if "description" in change.local_changes:
                new_desc = change.local_changes["description"].split(" -> ")[1]
                update_data["description"] = new_desc
                milestone.description = new_desc

            # Apply status change
            if "status" in change.local_changes:
                status_update = self._extract_milestone_status_update(
                    change.local_changes["status"]
                )
                if status_update:
                    update_data["state"] = status_update["github_state"]
                    milestone.status = status_update["status_enum"]

            # Push changes to GitHub
            if update_data:
                handler.update_milestone(milestone.github_milestone, **update_data)

        except Exception as e:
            print(
                f"Failed to apply local changes to GitHub for milestone "
                f"{change.issue_id}: {e}"
            )

    def _apply_github_milestone_changes(self, change: IssueChange) -> None:
        """Apply GitHub milestone changes locally.

        Args:
            change: IssueChange with detected changes from GitHub
        """
        if not change.github_changes:
            return

        try:
            milestone = self.core.milestones.get(change.issue_id)
            if not milestone:
                return

            # Apply title change from GitHub
            if "title" in change.github_changes:
                new_title = change.github_changes["title"].split(" -> ")[1]
                milestone.name = new_title

            # Apply description change from GitHub
            if "description" in change.github_changes:
                new_desc = change.github_changes["description"].split(" -> ")[1]
                milestone.description = new_desc

            # Apply status change from GitHub
            if "status" in change.github_changes:
                new_status = change.github_changes["status"].split(" -> ")[1]
                from roadmap.common.constants import MilestoneStatus

                try:
                    milestone.status = MilestoneStatus(new_status)
                except (ValueError, KeyError):
                    pass

        except Exception as e:
            print(f"Failed to apply GitHub changes to milestone {change.issue_id}: {e}")

    def _apply_archived_issue_to_github(self, issue_id: str) -> None:
        """Archive an issue on GitHub when archived locally.

        Args:
            issue_id: Local issue ID
        """
        try:
            issue = self.core.issues.get(issue_id)
            if not issue or not issue.github_issue:
                return

            owner_repo = self._get_owner_repo()
            if not owner_repo:
                return
            owner, repo = owner_repo

            handler = self._get_issue_handler(owner, repo)

            # Close the issue on GitHub (GitHub doesn't have archive, closest is closed + label)
            github_issue_number = (
                int(issue.github_issue)
                if isinstance(issue.github_issue, str)
                else issue.github_issue
            )

            handler.update_issue(github_issue_number, state="closed")

            # Record successful sync in metadata
            self.metadata_service.record_sync(
                issue, success=True, github_changes={"archived": "closed on GitHub"}
            )

        except Exception as e:
            issue = self.core.issues.get(issue_id)
            if issue:
                self.metadata_service.record_sync(
                    issue, success=False, error_message=str(e)
                )
            print(f"Failed to archive issue {issue_id} on GitHub: {e}")

    def _apply_restored_issue_to_github(self, issue_id: str) -> None:
        """Restore (unarchive) an issue on GitHub when restored locally.

        Args:
            issue_id: Local issue ID
        """
        try:
            issue = self.core.issues.get(issue_id)
            if not issue or not issue.github_issue:
                return

            owner_repo = self._get_owner_repo()
            if not owner_repo:
                return
            owner, repo = owner_repo

            handler = self._get_issue_handler(owner, repo)

            # Reopen the issue on GitHub
            github_issue_number = (
                int(issue.github_issue)
                if isinstance(issue.github_issue, str)
                else issue.github_issue
            )

            handler.update_issue(github_issue_number, state="open")

            # Record successful sync in metadata
            self.metadata_service.record_sync(
                issue, success=True, github_changes={"restored": "reopened on GitHub"}
            )

        except Exception as e:
            issue = self.core.issues.get(issue_id)
            if issue:
                self.metadata_service.record_sync(
                    issue, success=False, error_message=str(e)
                )
            print(f"Failed to restore issue {issue_id} on GitHub: {e}")

    def _apply_archived_milestone_to_github(self, milestone_name: str) -> None:
        """Archive a milestone on GitHub when archived locally.

        Args:
            milestone_name: Local milestone name
        """
        try:
            milestone = self.core.milestones.get(milestone_name)
            if not milestone or not milestone.github_milestone:
                return

            owner_repo = self._get_owner_repo()
            if not owner_repo:
                return
            owner, repo = owner_repo

            handler = self._get_milestone_handler(owner, repo)

            # Close the milestone on GitHub (GitHub closest equivalent to archive)
            handler.update_milestone(milestone.github_milestone, state="closed")

        except Exception as e:
            print(f"Failed to archive milestone {milestone_name} on GitHub: {e}")

    def _apply_restored_milestone_to_github(self, milestone_name: str) -> None:
        """Restore (unarchive) a milestone on GitHub when restored locally.

        Args:
            milestone_name: Local milestone name
        """
        try:
            milestone = self.core.milestones.get(milestone_name)
            if not milestone or not milestone.github_milestone:
                return

            owner_repo = self._get_owner_repo()
            if not owner_repo:
                return
            owner, repo = owner_repo

            handler = self._get_milestone_handler(owner, repo)

            # Reopen the milestone on GitHub
            handler.update_milestone(milestone.github_milestone, state="open")

        except Exception as e:
            print(f"Failed to restore milestone {milestone_name} on GitHub: {e}")
