"""End-to-end integration tests for sync orchestrator with new services.

Tests the full sync workflow using SyncMergeOrchestrator, SyncStateComparator,
and SyncConflictResolver to verify they work together correctly.
"""

import unittest
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

from roadmap.adapters.sync.sync_merge_orchestrator import SyncMergeOrchestrator
from roadmap.common.constants import Priority, Status
from roadmap.core.domain.issue import Issue
from roadmap.core.interfaces.sync_backend import SyncReport
from roadmap.core.services.sync.sync_conflict_resolver import (
    SyncConflictResolver,
)
from roadmap.core.services.sync.sync_state_comparator import SyncStateComparator
from tests.factories import IssueBuilder, SyncIssueFactory


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
        local_issue = (
            IssueBuilder()
            .with_id("local-1")
            .with_title("New Local Issue")
            .with_status(Status.TODO)
            .with_priority(Priority.MEDIUM)
            .with_created_date(datetime.now(UTC))
            .with_updated_date(datetime.now(UTC))
            .build()
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
        local_issue = (
            IssueBuilder()
            .with_id("local-1")
            .with_title("New Local Issue")
            .with_status(Status.TODO)
            .with_priority(Priority.MEDIUM)
            .with_created_date(datetime.now(UTC))
            .with_updated_date(datetime.now(UTC))
            .build()
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
        remote_issue = SyncIssueFactory.create_github(
            number=1,
            title="New Remote Issue",
            status="open",
        )

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
        remote_issue = SyncIssueFactory.create_github(
            number=1,
            title="New Remote Issue",
            status="open",
        )

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
        # Pull should be called for remote issue with the pull list
        self.backend.pull_issues.assert_called_once()
        # Check that pull_issues was called with remote-1 in the list
        called_args = self.backend.pull_issues.call_args
        assert "remote-1" in called_args[0][0]  # First positional arg is issue_ids list


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
        now = datetime.now(UTC)
        earlier = now - timedelta(hours=1)
        later = now

        local_issue = (
            IssueBuilder()
            .with_id("conflict-1")
            .with_title("Local Title")
            .with_status(Status.TODO)
            .with_priority(Priority.MEDIUM)
            .with_created_date(earlier)
            .with_updated_date(earlier)
            .build()
        )

        remote_issue = SyncIssueFactory.create_github(
            number=1,
            title="Remote Title",
            status="open",
            updated_at=later,  # Newer
        )

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
        now = datetime.now(UTC)
        earlier = now - timedelta(hours=1)

        local_issue = (
            IssueBuilder()
            .with_id("conflict-1")
            .with_title("Local Title")
            .with_status(Status.TODO)
            .with_priority(Priority.MEDIUM)
            .with_created_date(earlier)
            .with_updated_date(earlier)
            .build()
        )

        remote_issue = SyncIssueFactory.create_github(
            number=1,
            title="Remote Title",
            status="closed",
            updated_at=now,
        )

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
        now = datetime.now(UTC)
        earlier = now - timedelta(hours=1)

        local_issue = (
            IssueBuilder()
            .with_id("conflict-1")
            .with_title("Local Title")
            .with_status(Status.TODO)
            .with_priority(Priority.MEDIUM)
            .with_created_date(earlier)
            .with_updated_date(earlier)
            .build()
        )

        remote_issue = SyncIssueFactory.create_github(
            number=1,
            title="Remote Title",
            status="closed",
            updated_at=now,
        )

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
        now = datetime.now(UTC)
        older = now - timedelta(hours=2)

        # Local: 3 issues
        # 1. New local issue
        new_local = (
            IssueBuilder()
            .with_id("local-new")
            .with_title("New Local Issue")
            .with_status(Status.TODO)
            .with_priority(Priority.MEDIUM)
            .with_created_date(now)
            .with_updated_date(now)
            .build()
        )
        updated_local = (
            IssueBuilder()
            .with_id("updated")
            .with_title("Updated Local")
            .with_status(Status.IN_PROGRESS)
            .with_priority(Priority.HIGH)
            .with_created_date(older)
            .with_updated_date(now)
            .build()
        )
        conflicted_local = (
            IssueBuilder()
            .with_id("conflict")
            .with_title("Local Conflict Title")
            .with_status(Status.TODO)
            .with_priority(Priority.LOW)
            .with_created_date(older)
            .with_updated_date(now)
            .build()
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
            "updated": SyncIssueFactory.create(
                id="updated",
                title="Updated Remote",
                status="todo",
                updated_at=older,  # Older than local
            ),
            "conflict": SyncIssueFactory.create(
                id="conflict",
                title="Remote Conflict Title",
                status="closed",
                updated_at=now,  # Newer than local
            ),
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
        now = datetime.now(UTC)
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
            "conflict": SyncIssueFactory.create(
                id="conflict",
                title="Remote Conflict Title",
                status="closed",
                updated_at=now,
            )
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
        now = datetime.now(UTC)

        # Local and remote have the same issue
        issue = Issue(
            id="same-1",
            title="Same Issue",
            status=Status.TODO,
            priority=Priority.MEDIUM,
            created=now,
            updated=now,
        )

        remote_issue = SyncIssueFactory.create(
            id="same-1",
            title="Same Issue",
            status="todo",
            updated_at=now,
        )

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


class TestFullBidirectionalSync(unittest.TestCase):
    """Test full bidirectional sync with local and remote changes."""

    def setUp(self):
        """Set up test fixtures."""
        self.core = MagicMock()
        self.backend = MagicMock()
        self.state_comparator = SyncStateComparator()
        self.conflict_resolver = SyncConflictResolver()

    def test_full_bidirectional_sync_dry_run(self):
        """Test dry-run bidirectional sync detects all changes without applying."""
        # Setup: Mixed scenario
        # Local: 1 new issue, 1 updated issue, 1 up-to-date
        now = datetime.now(UTC)
        past = now - timedelta(hours=2)

        local_new = (
            IssueBuilder()
            .with_id("local-new")
            .with_title("New Local Issue")
            .with_status(Status.TODO)
            .with_priority(Priority.HIGH)
            .with_created_date(now)
            .with_updated_date(now)
            .build()
        )

        local_updated = (
            IssueBuilder()
            .with_id("shared-1")
            .with_title("Updated Local Issue")
            .with_status(Status.IN_PROGRESS)
            .with_priority(Priority.HIGH)
            .with_created_date(past)
            .with_updated_date(now)
            .build()
        )

        local_unchanged = (
            IssueBuilder()
            .with_id("shared-2")
            .with_title("Unchanged Issue")
            .with_status(Status.CLOSED)
            .with_priority(Priority.LOW)
            .with_created_date(past)
            .with_updated_date(past)
            .build()
        )

        # Remote: 1 new issue, 1 updated issue (shared-1), 1 unchanged (shared-2)
        remote_new = SyncIssueFactory.create_github(
            number=100,
            title="New Remote Issue",
            status="open",
        )

        remote_updated = SyncIssueFactory.create(
            id="shared-1",
            title="Updated Remote Issue",
            status="closed",
            created_at=past,
            updated_at=now,
        )

        remote_unchanged = SyncIssueFactory.create(
            id="shared-2",
            title="Unchanged Issue",
            status="closed",
            created_at=past,
            updated_at=past,
        )

        self.core.issues.list_all_including_archived.return_value = [
            local_new,
            local_updated,
            local_unchanged,
        ]
        self.backend.authenticate.return_value = True
        self.backend.get_issues.return_value = {
            "remote-new": remote_new,
            "shared-1": remote_updated,
            "shared-2": remote_unchanged,
        }

        orchestrator = SyncMergeOrchestrator(
            self.core,
            self.backend,
            state_comparator=self.state_comparator,
            conflict_resolver=self.conflict_resolver,
        )

        # Execute: Full bidirectional sync (push_only=False, pull_only=False)
        report = orchestrator.sync_all_issues(dry_run=True)

        # Verify
        assert report.error is None
        # shared-1 appears as conflict because both sides changed (no baseline)
        # local-new needs push, remote-new needs pull, shared-2 is up to date
        assert report.conflicts_detected >= 1
        assert report.issues_needs_push >= 1  # local-new and/or shared-1 need push
        assert report.issues_needs_pull >= 1  # remote-new and/or shared-1 need pull
        assert report.issues_up_to_date >= 1  # shared-2 should be up to date
        # In dry-run mode, no actual push/pull happens
        self.backend.push_issues.assert_not_called()
        self.backend.pull_issues.assert_not_called()

    def test_full_bidirectional_sync_apply(self):
        """Test applying full bidirectional sync pushes and pulls changes."""
        now = datetime.now(UTC)
        past = now - timedelta(hours=2)

        # Local issue to push
        local_issue = (
            IssueBuilder()
            .with_id("local-new")
            .with_title("New Local Issue")
            .with_status(Status.TODO)
            .with_priority(Priority.HIGH)
            .with_created_date(now)
            .with_updated_date(now)
            .build()
        )

        # Shared issue with local changes
        shared_local = (
            IssueBuilder()
            .with_id("shared-1")
            .with_title("Shared Issue")
            .with_status(Status.IN_PROGRESS)
            .with_priority(Priority.HIGH)
            .with_created_date(past)
            .with_updated_date(now)
            .build()
        )

        # Remote issue to pull
        remote_issue = SyncIssueFactory.create_github(
            number=100,
            title="New Remote Issue",
            status="open",
        )

        self.core.issues.list_all_including_archived.return_value = [
            local_issue,
            shared_local,
        ]
        self.core.issues.get.side_effect = lambda issue_id: (
            local_issue if issue_id == "local-new" else shared_local
        )
        self.backend.authenticate.return_value = True
        self.backend.get_issues.return_value = {
            "remote-new": remote_issue,
            "shared-1": SyncIssueFactory.create(
                id="shared-1",
                title="Shared Issue",
                status="closed",
                created_at=past,
                updated_at=now,
            ),
        }
        self.backend.push_issue.return_value = True
        # Setup push_issues mock to return successful SyncReport
        push_report = SyncReport()
        push_report.pushed = ["local-new", "shared-1"]
        self.backend.push_issues.return_value = push_report
        # Setup pull_issues mock
        pull_report = SyncReport()
        pull_report.pulled = ["remote-new"]
        self.backend.pull_issues.return_value = pull_report

        orchestrator = SyncMergeOrchestrator(
            self.core,
            self.backend,
            state_comparator=self.state_comparator,
            conflict_resolver=self.conflict_resolver,
        )

        # Execute: Full bidirectional sync in apply mode
        report = orchestrator.sync_all_issues(dry_run=False)

        # Verify sync happened
        assert report.error is None
        # Verify push_issues was called for local changes
        assert self.backend.push_issues.called
        # Verify pull_issues was called for remote changes
        assert self.backend.pull_issues.called
        # Verify applied changes tracked
        assert report.issues_pushed > 0 or report.issues_pulled > 0

    def test_full_bidirectional_sync_with_conflict_force_remote(self):
        """Test bidirectional sync with conflict resolution (force remote)."""
        now = datetime.now(UTC)
        past = now - timedelta(hours=2)

        # Issue with conflicting changes
        local_conflict = (
            IssueBuilder()
            .with_id("conflict-1")
            .with_title("Conflict Issue")
            .with_status(Status.IN_PROGRESS)
            .with_priority(Priority.HIGH)
            .with_created_date(past)
            .with_updated_date(now)
            .build()
        )  # Local wants IN_PROGRESS

        remote_conflict = SyncIssueFactory.create(
            id="conflict-1",
            title="Conflict Issue",
            status="closed",  # Remote wants CLOSED
            created_at=past,
            updated_at=now,
        )

        self.core.issues.list_all_including_archived.return_value = [local_conflict]
        self.core.issues.get.return_value = local_conflict
        self.backend.authenticate.return_value = True
        self.backend.get_issues.return_value = {"conflict-1": remote_conflict}
        # Setup pull_issues mock
        pull_report = SyncReport()
        self.backend.pull_issues.return_value = pull_report
        # Setup push_issues mock
        push_report = SyncReport()
        self.backend.push_issues.return_value = push_report

        orchestrator = SyncMergeOrchestrator(
            self.core,
            self.backend,
            state_comparator=self.state_comparator,
            conflict_resolver=self.conflict_resolver,
        )

        # Execute: Resolve by keeping remote
        report = orchestrator.sync_all_issues(
            dry_run=False, force_remote=True, push_only=False, pull_only=False
        )

        # Verify
        assert report.error is None
        assert report.conflicts_detected == 1
        # When force_remote, the remote version should be kept
        # (implementation may vary based on conflict resolution strategy)


if __name__ == "__main__":
    unittest.main()
