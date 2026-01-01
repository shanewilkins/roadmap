"""Generic sync orchestrator that works with any sync backend.

This orchestrator provides the high-level sync logic (detecting changes,
reporting conflicts, etc.) and delegates backend-specific operations
to SyncBackendInterface implementations.
"""

from datetime import datetime

from roadmap.core.domain import Issue
from roadmap.core.interfaces.sync_backend import SyncBackendInterface
from roadmap.core.services.sync_report import IssueChange, SyncReport
from roadmap.infrastructure.core import RoadmapCore


class GenericSyncOrchestrator:
    """Orchestrates sync using a pluggable backend implementation."""

    def __init__(self, core: RoadmapCore, backend: SyncBackendInterface):
        """Initialize orchestrator with core services and backend.

        Args:
            core: RoadmapCore instance with access to issues
            backend: SyncBackendInterface implementation (GitHub, vanilla Git, etc.)
        """
        self.core = core
        self.backend = backend

    def sync_all_issues(
        self,
        dry_run: bool = True,
        force_local: bool = False,
        force_remote: bool = False,
    ) -> SyncReport:
        """Sync all issues using the configured backend.

        Args:
            dry_run: If True, only detect changes without applying them
            force_local: Resolve conflicts by keeping local changes
            force_remote: Resolve conflicts by keeping remote changes

        Returns:
            SyncReport with detected changes and conflicts
        """
        report = SyncReport()

        try:
            # 1. Authenticate with backend
            if not self.backend.authenticate():
                report.error = "Backend authentication failed"
                return report

            # 2. Get remote issues
            remote_issues = self.backend.get_issues()
            if remote_issues is None:
                report.error = "Failed to fetch remote issues"
                return report

            # 3. Get local issues
            local_issues = self.core.issues.list()
            if not local_issues:
                local_issues = []

            # 4. Detect changes for each local issue
            for local_issue in local_issues:
                change = self._detect_issue_changes(
                    local_issue, remote_issues, force_local, force_remote
                )
                report.changes.append(change)

                if change.has_conflict:
                    report.conflicts_detected += 1
                elif change.local_changes or change.github_changes:
                    report.issues_updated += 1
                else:
                    report.issues_up_to_date += 1

            # 5. Apply changes if not dry-run
            if not dry_run and not report.has_conflicts():
                report = self._apply_changes(report)

            return report

        except Exception as e:
            report.error = str(e)
            return report

    def _detect_issue_changes(
        self,
        local_issue: Issue,
        remote_issues: dict,
        force_local: bool = False,
        force_remote: bool = False,
    ) -> IssueChange:
        """Detect what has changed for a single issue.

        Args:
            local_issue: Local issue to check
            remote_issues: Remote issues dict from backend
            force_local: If True, prefer local changes in conflicts
            force_remote: If True, prefer remote changes in conflicts

        Returns:
            IssueChange with detected changes
        """
        change = IssueChange(
            issue_id=local_issue.id,
            title=local_issue.title,
            last_sync_time=self._get_last_sync_time(local_issue),
        )

        # Check if issue exists remotely
        remote_issue = remote_issues.get(local_issue.id)

        if not remote_issue:
            # Issue is only local - needs to be pushed
            change.local_changes = {"action": "create"}
            return change

        # Compare local and remote versions
        local_changes = self._detect_local_changes(local_issue, remote_issue)
        remote_changes = self._detect_remote_changes(local_issue, remote_issue)

        change.local_changes = local_changes
        change.github_changes = remote_changes

        # Detect conflicts
        if local_changes and remote_changes:
            change.has_conflict = True

        return change

    def _detect_local_changes(self, local_issue: Issue, remote_issue: dict) -> dict:
        """Detect changes made locally since last sync.

        Args:
            local_issue: Local issue object
            remote_issue: Remote issue dict

        Returns:
            Dict describing local changes, or empty dict if no changes
        """
        changes = {}

        # Check title
        if local_issue.title != remote_issue.get("title"):
            changes["title"] = f"{remote_issue.get('title')} -> {local_issue.title}"

        # Check status
        local_status = str(local_issue.status.value)
        remote_status = remote_issue.get("status")
        if local_status != remote_status:
            changes["status"] = f"{remote_status} -> {local_status}"

        # Check description
        if getattr(local_issue, "description", None) != remote_issue.get("description"):
            local_desc = getattr(local_issue, "description", "")
            changes["description"] = (
                f"{remote_issue.get('description')} -> {local_desc}"
            )

        return changes

    def _detect_remote_changes(self, local_issue: Issue, remote_issue: dict) -> dict:
        """Detect changes made on remote since last sync.

        Args:
            local_issue: Local issue object
            remote_issue: Remote issue dict

        Returns:
            Dict describing remote changes, or empty dict if no changes
        """
        changes = {}

        # Check title
        if remote_issue.get("title") != local_issue.title:
            changes["title"] = f"{local_issue.title} -> {remote_issue.get('title')}"

        # Check status
        local_status = str(local_issue.status.value)
        remote_status = remote_issue.get("status")
        if remote_status != local_status:
            changes["status"] = f"{local_status} -> {remote_status}"

        # Check description
        local_desc = getattr(local_issue, "description", "")
        if remote_issue.get("description") != local_desc:
            changes["description"] = (
                f"{local_desc} -> {remote_issue.get('description')}"
            )

        return changes

    def _get_last_sync_time(self, issue: Issue) -> datetime | None:
        """Get the last sync timestamp for an issue.

        Args:
            issue: Issue to check

        Returns:
            Last sync timestamp, or None if never synced
        """
        if hasattr(issue, "last_synced_at"):
            return getattr(issue, "last_synced_at", None)
        return None

    def _apply_changes(self, report: SyncReport) -> SyncReport:
        """Apply detected changes using the backend.

        Args:
            report: SyncReport with detected changes

        Returns:
            Updated SyncReport with applied changes
        """
        issues_to_push = [
            self.core.issues.get(change.issue_id)
            for change in report.changes
            if change.local_changes and change.issue_id
        ]

        if issues_to_push:
            # Filter out None values
            issues_to_push = [i for i in issues_to_push if i]

            if len(issues_to_push) == 1:
                # Single issue push
                success = self.backend.push_issue(issues_to_push[0])
                if not success:
                    report.error = "Failed to push issue"
            else:
                # Batch push
                push_report = self.backend.push_issues(issues_to_push)
                if push_report and push_report.errors:
                    report.error = f"Push failed: {push_report.errors}"

        return report
