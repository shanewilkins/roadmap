"""End-to-end integration tests for sync orchestrator with new services.

Tests the full sync workflow using SyncMergeOrchestrator, SyncStateComparator,
and SyncConflictResolver to verify they work together correctly.
"""

import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

from roadmap.adapters.sync.sync_merge_orchestrator import SyncMergeOrchestrator
from roadmap.common.constants import Priority, Status
from roadmap.core.domain.issue import Issue
from roadmap.core.interfaces.sync_backend import SyncReport
from roadmap.core.services.sync_conflict_resolver import (
    SyncConflictResolver,
)
from roadmap.core.services.sync_state_comparator import SyncStateComparator


class TestSyncEnd2EndNewLocalIssues(unittest.TestCase):
    """Test syncing when there are new local issues to push."""

    def setUp(self):
        """Set up test fixtures."""
        self.core = MagicMock()
        self.backend = MagicMock()
        self.state_comparator = SyncStateComparator()
        self.conflict_resolver = SyncConflictResolver()

    def test_sync_new_local_issue_dry_run(self):
        """Test dry-run mode detects new local issues without applying changes."""
        # Setup: 1 local issue, no remote issues
        local_issue = Issue(
            id="local-1",
            title="New Local Issue",
            status=Status.TODO,
            priority=Priority.MEDIUM,
            created=datetime.now(timezone.utc),
            updated=datetime.now(timezone.utc),
        )

        self.core.issues.list_all_including_archived.return_value = [local_issue]
        self.backend.authenticate.return_value = True
        self.backend.get_issues.return_value = {}  # No remote issues

        orchestrator = SyncMergeOrchestrator(
            self.core,
            self.backend,
            state_comparator=self.state_comparator,
            conflict_resolver=self.conflict_resolver,
        )

        # Execute
        report = orchestrator.sync_all_issues(dry_run=True)

        # Verify
        assert report.error is None
        assert report.issues_needs_push == 1  # 1 issue to push
        assert report.conflicts_detected == 0
        self.backend.push_issue.assert_not_called()  # Dry run - no actual push

    def test_sync_new_local_issue_apply(self):
        """Test applying changes pushes new local issues."""
        # Setup: 1 local issue, no remote issues
        local_issue = Issue(
            id="local-1",
            title="New Local Issue",
            status=Status.TODO,
            priority=Priority.MEDIUM,
            created=datetime.now(timezone.utc),
            updated=datetime.now(timezone.utc),
        )

        self.core.issues.list_all_including_archived.return_value = [local_issue]
        self.core.issues.get.return_value = local_issue
        self.backend.authenticate.return_value = True
        self.backend.get_issues.return_value = {}
        self.backend.push_issue.return_value = True

        orchestrator = SyncMergeOrchestrator(
            self.core,
            self.backend,
            state_comparator=self.state_comparator,
            conflict_resolver=self.conflict_resolver,
        )

        # Execute
        report = orchestrator.sync_all_issues(dry_run=False)

        # Verify
        assert report.error is None
        # After push, the issue should be up-to-date (not needing push)
        # The report shows current state, not what was pushed
        assert report.issues_up_to_date == 1
        assert report.issues_needs_push == 0
        assert report.issues_pushed == 1
        self.backend.push_issue.assert_called_once_with(local_issue)


class TestSyncEnd2EndNewRemoteIssues(unittest.TestCase):
    """Test syncing when there are new remote issues to pull."""

    def setUp(self):
        """Set up test fixtures."""
        self.core = MagicMock()
        self.backend = MagicMock()
        self.state_comparator = SyncStateComparator()
        self.conflict_resolver = SyncConflictResolver()

    def test_sync_new_remote_issue_dry_run(self):
        """Test dry-run mode detects new remote issues without applying changes."""
        # Setup: no local issues, 1 remote issue
        remote_issue = {
            "id": "remote-1",
            "title": "New Remote Issue",
            "status": "TODO",
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        self.core.issues.list_all_including_archived.return_value = []
        self.backend.authenticate.return_value = True
        self.backend.get_issues.return_value = {"remote-1": remote_issue}

        orchestrator = SyncMergeOrchestrator(
            self.core,
            self.backend,
            state_comparator=self.state_comparator,
            conflict_resolver=self.conflict_resolver,
        )

        # Execute
        report = orchestrator.sync_all_issues(dry_run=True)

        # Verify
        assert report.error is None
        assert report.conflicts_detected == 0
        self.backend.pull_issue.assert_not_called()  # Dry run - no actual pull

    def test_sync_new_remote_issue_apply(self):
        """Test applying changes pulls new remote issues."""
        # Setup: no local issues, 1 remote issue
        remote_issue = {
            "id": "remote-1",
            "title": "New Remote Issue",
            "status": "TODO",
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        self.core.issues.list_all_including_archived.return_value = []
        self.backend.authenticate.return_value = True
        self.backend.get_issues.return_value = {"remote-1": remote_issue}
        self.backend.pull_issue.return_value = True

        orchestrator = SyncMergeOrchestrator(
            self.core,
            self.backend,
            state_comparator=self.state_comparator,
            conflict_resolver=self.conflict_resolver,
        )

        # Execute
        report = orchestrator.sync_all_issues(dry_run=False)

        # Verify
        assert report.error is None
        assert report.conflicts_detected == 0
        # Pull should be called for remote issue
        self.backend.pull_issue.assert_called()


class TestSyncEnd2EndConflicts(unittest.TestCase):
    """Test syncing when there are conflicts between local and remote."""

    def setUp(self):
        """Set up test fixtures."""
        self.core = MagicMock()
        self.backend = MagicMock()
        self.state_comparator = SyncStateComparator()
        self.conflict_resolver = SyncConflictResolver()

    def test_sync_conflict_auto_merge_remote_newer(self):
        """Test auto-merge chooses remote when it's newer."""
        # Setup: conflicting issue, remote is newer
        now = datetime.now(timezone.utc)
        earlier = now - timedelta(hours=1)
        later = now

        local_issue = Issue(
            id="conflict-1",
            title="Local Title",
            status=Status.TODO,
            priority=Priority.MEDIUM,
            created=earlier,
            updated=earlier,  # Older
        )

        remote_issue = {
            "id": "conflict-1",
            "title": "Remote Title",
            "status": "TODO",
            "updated_at": later.isoformat(),  # Newer
        }

        self.core.issues.list_all_including_archived.return_value = [local_issue]
        self.core.issues.get.return_value = local_issue
        self.backend.authenticate.return_value = True
        self.backend.get_issues.return_value = {"conflict-1": remote_issue}
        self.backend.push_issue.return_value = True

        orchestrator = SyncMergeOrchestrator(
            self.core,
            self.backend,
            state_comparator=self.state_comparator,
            conflict_resolver=self.conflict_resolver,
        )

        # Execute - auto merge should prefer remote (newer)
        report = orchestrator.sync_all_issues(dry_run=False)

        # Verify
        assert report.error is None
        assert report.conflicts_detected == 1

    def test_sync_conflict_force_local(self):
        """Test force_local resolution keeps local changes."""
        # Setup: conflicting issue
        now = datetime.now(timezone.utc)
        earlier = now - timedelta(hours=1)

        local_issue = Issue(
            id="conflict-1",
            title="Local Title",
            status=Status.TODO,
            priority=Priority.MEDIUM,
            created=earlier,
            updated=earlier,
        )

        remote_issue = {
            "id": "conflict-1",
            "title": "Remote Title",
            "status": "closed",
            "priority": "medium",
            "updated_at": now.isoformat(),
        }

        self.core.issues.list_all_including_archived.return_value = [local_issue]
        self.core.issues.get.return_value = local_issue
        self.backend.authenticate.return_value = True
        self.backend.get_issues.return_value = {"conflict-1": remote_issue}
        self.backend.push_issue.return_value = True

        orchestrator = SyncMergeOrchestrator(
            self.core,
            self.backend,
            state_comparator=self.state_comparator,
            conflict_resolver=self.conflict_resolver,
        )

        # Execute with force_local
        report = orchestrator.sync_all_issues(
            dry_run=False, force_local=True, force_remote=False
        )

        # Verify
        assert report.error is None
        assert report.conflicts_detected == 1
        # With force_local, should push the local version
        self.backend.push_issue.assert_called_once_with(local_issue)

    def test_sync_conflict_force_remote(self):
        """Test force_remote resolution keeps remote changes."""
        # Setup: conflicting issue
        now = datetime.now(timezone.utc)
        earlier = now - timedelta(hours=1)

        local_issue = Issue(
            id="conflict-1",
            title="Local Title",
            status=Status.TODO,
            priority=Priority.MEDIUM,
            created=earlier,
            updated=earlier,
        )

        remote_issue = {
            "id": "conflict-1",
            "title": "Remote Title",
            "status": "closed",
            "priority": "medium",
            "updated_at": now.isoformat(),
        }

        self.core.issues.list_all_including_archived.return_value = [local_issue]
        self.backend.authenticate.return_value = True
        self.backend.get_issues.return_value = {"conflict-1": remote_issue}
        self.backend.pull_issue.return_value = True

        orchestrator = SyncMergeOrchestrator(
            self.core,
            self.backend,
            state_comparator=self.state_comparator,
            conflict_resolver=self.conflict_resolver,
        )

        # Execute with force_remote
        report = orchestrator.sync_all_issues(
            dry_run=False, force_local=False, force_remote=True
        )

        # Verify
        assert report.error is None
        assert report.conflicts_detected == 1


class TestSyncEnd2EndMixedScenarios(unittest.TestCase):
    """Test syncing with mixed scenarios (new, updates, conflicts)."""

    def setUp(self):
        """Set up test fixtures."""
        self.core = MagicMock()
        self.backend = MagicMock()
        self.state_comparator = SyncStateComparator()
        self.conflict_resolver = SyncConflictResolver()

    def test_sync_mixed_scenario_dry_run(self):
        """Test dry-run with multiple issue types."""
        now = datetime.now(timezone.utc)
        earlier = now - timedelta(hours=1)
        older = now - timedelta(hours=2)

        # Local: 3 issues
        # 1. New local issue
        new_local = Issue(
            id="local-new",
            title="New Local Issue",
            status=Status.TODO,
            priority=Priority.MEDIUM,
            created=now,
            updated=now,
        )

        # 2. Updated local issue (newer than remote)
        updated_local = Issue(
            id="updated",
            title="Updated Local",
            status=Status.IN_PROGRESS,
            priority=Priority.HIGH,
            created=older,
            updated=now,
        )

        # 3. Conflicting issue (both changed)
        conflicted_local = Issue(
            id="conflict",
            title="Local Conflict Title",
            status=Status.TODO,
            priority=Priority.LOW,
            created=older,
            updated=earlier,
        )

        self.core.issues.list_all_including_archived.return_value = [
            new_local,
            updated_local,
            conflicted_local,
        ]
        self.backend.authenticate.return_value = True

        # Remote: 2 issues
        # 1. Updated local issue (older version)
        # 2. Conflicting issue (different version)
        remote_issues = {
            "updated": {
                "id": "updated",
                "title": "Updated Remote",
                "status": "todo",
                "priority": "high",
                "updated_at": older.isoformat(),  # Older than local
            },
            "conflict": {
                "id": "conflict",
                "title": "Remote Conflict Title",
                "status": "closed",
                "priority": "low",
                "updated_at": now.isoformat(),  # Newer than local
            },
        }

        self.backend.get_issues.return_value = remote_issues

        orchestrator = SyncMergeOrchestrator(
            self.core,
            self.backend,
            state_comparator=self.state_comparator,
            conflict_resolver=self.conflict_resolver,
        )

        # Execute
        report = orchestrator.sync_all_issues(dry_run=True)

        # Verify
        assert report.error is None
        assert (
            report.conflicts_detected == 2
        )  # Both "updated" and "conflict" have conflicts
        assert report.issues_needs_push >= 1  # At least the new local issue
        assert not self.backend.push_issue.called
        assert not self.backend.pull_issue.called

    def test_sync_mixed_scenario_apply(self):
        """Test applying mixed scenario changes."""
        now = datetime.now(timezone.utc)
        earlier = now - timedelta(hours=1)
        older = now - timedelta(hours=2)

        # Local: 2 issues
        new_local = Issue(
            id="local-new",
            title="New Local Issue",
            status=Status.TODO,
            priority=Priority.MEDIUM,
            created=now,
            updated=now,
        )

        conflicted_local = Issue(
            id="conflict",
            title="Local Conflict Title",
            status=Status.TODO,
            priority=Priority.LOW,
            created=older,
            updated=earlier,
        )

        self.core.issues.list_all_including_archived.return_value = [
            new_local,
            conflicted_local,
        ]
        self.core.issues.get.return_value = None  # Will be called but we'll set it up

        def get_side_effect(issue_id):
            if issue_id == "local-new":
                return new_local
            elif issue_id == "conflict":
                return conflicted_local
            return None

        self.core.issues.get.side_effect = get_side_effect
        self.backend.authenticate.return_value = True

        # Remote: 1 issue (conflicting)
        remote_issues = {
            "conflict": {
                "id": "conflict",
                "title": "Remote Conflict Title",
                "status": "closed",
                "priority": "low",
                "updated_at": now.isoformat(),
            }
        }

        self.backend.get_issues.return_value = remote_issues

        # Create a proper SyncReport mock for push_issues
        push_report = SyncReport()
        push_report.pushed = ["local-new", "conflict"]
        push_report.errors = {}
        self.backend.push_issues.return_value = push_report
        self.backend.pull_issue.return_value = True

        orchestrator = SyncMergeOrchestrator(
            self.core,
            self.backend,
            state_comparator=self.state_comparator,
            conflict_resolver=self.conflict_resolver,
        )

        # Execute with force_remote to resolve conflict
        report = orchestrator.sync_all_issues(
            dry_run=False, force_local=False, force_remote=True
        )

        # Verify
        assert report.error is None
        assert report.conflicts_detected == 1


class TestSyncEnd2EndAuthenticationFailure(unittest.TestCase):
    """Test sync behavior when authentication fails."""

    def setUp(self):
        """Set up test fixtures."""
        self.core = MagicMock()
        self.backend = MagicMock()
        self.state_comparator = SyncStateComparator()
        self.conflict_resolver = SyncConflictResolver()

    def test_sync_authentication_failure_returns_error(self):
        """Test that auth failure is reported without raising exceptions."""
        self.core.issues.list_all_including_archived.return_value = []
        self.backend.authenticate.return_value = False

        orchestrator = SyncMergeOrchestrator(
            self.core,
            self.backend,
            state_comparator=self.state_comparator,
            conflict_resolver=self.conflict_resolver,
        )

        # Execute
        report = orchestrator.sync_all_issues(dry_run=True)

        # Verify
        assert report.error == "Backend authentication failed"
        assert report.conflicts_detected == 0
        self.backend.get_issues.assert_not_called()


class TestSyncEnd2EndRemoteFailure(unittest.TestCase):
    """Test sync behavior when fetching remote issues fails."""

    def setUp(self):
        """Set up test fixtures."""
        self.core = MagicMock()
        self.backend = MagicMock()
        self.state_comparator = SyncStateComparator()
        self.conflict_resolver = SyncConflictResolver()

    def test_sync_remote_fetch_failure_returns_error(self):
        """Test that remote fetch failure is reported."""
        self.core.issues.list_all_including_archived.return_value = []
        self.backend.authenticate.return_value = True
        self.backend.get_issues.return_value = None  # Failure

        orchestrator = SyncMergeOrchestrator(
            self.core,
            self.backend,
            state_comparator=self.state_comparator,
            conflict_resolver=self.conflict_resolver,
        )

        # Execute
        report = orchestrator.sync_all_issues(dry_run=True)

        # Verify
        assert report.error == "Failed to fetch remote issues"
        assert report.conflicts_detected == 0


class TestSyncEnd2EndUpToDate(unittest.TestCase):
    """Test sync when everything is already up-to-date."""

    def setUp(self):
        """Set up test fixtures."""
        self.core = MagicMock()
        self.backend = MagicMock()
        self.state_comparator = SyncStateComparator()
        self.conflict_resolver = SyncConflictResolver()

    def test_sync_everything_up_to_date(self):
        """Test sync with no changes needed."""
        now = datetime.now(timezone.utc)

        # Local and remote have the same issue
        issue = Issue(
            id="same-1",
            title="Same Issue",
            status=Status.TODO,
            priority=Priority.MEDIUM,
            created=now,
            updated=now,
        )

        remote_issue = {
            "id": "same-1",
            "title": "Same Issue",
            "status": "todo",
            "priority": "medium",
            "updated_at": now.isoformat(),
        }

        self.core.issues.list_all_including_archived.return_value = [issue]
        self.backend.authenticate.return_value = True
        self.backend.get_issues.return_value = {"same-1": remote_issue}

        orchestrator = SyncMergeOrchestrator(
            self.core,
            self.backend,
            state_comparator=self.state_comparator,
            conflict_resolver=self.conflict_resolver,
        )

        # Execute
        report = orchestrator.sync_all_issues(dry_run=True)

        # Verify
        assert report.error is None
        assert report.conflicts_detected == 0
        assert report.issues_up_to_date >= 1  # At least 1 should be up to date
        assert report.issues_needs_push == 0 and report.issues_needs_pull == 0


if __name__ == "__main__":
    unittest.main()
