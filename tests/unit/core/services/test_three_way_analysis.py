"""Tests for SyncStateComparator three-way merge analysis.

Tests the new three-way analysis methods that produce IssueChange objects
with complete baseline context for proper conflict understanding.
"""

from datetime import datetime, timezone

import pytest

from roadmap.common.constants import Status
from roadmap.core.domain.issue import Issue
from roadmap.core.models.sync_state import IssueBaseState
from roadmap.core.services.sync_state_comparator import SyncStateComparator


class TestThreeWayAnalysis:
    """Test three-way merge analysis with baseline context."""

    @pytest.fixture
    def comparator(self):
        """Create a comparator instance."""
        return SyncStateComparator()

    @pytest.fixture
    def baseline_state(self):
        """Create a baseline state."""
        return IssueBaseState(
            id="issue-1",
            status="todo",
            title="Original Title",
            assignee="alice",
            milestone="v1.0",
            headline="Original description",
            content="Original description",
            labels=["bug"],
            updated_at=datetime.now(timezone.utc),
        )

    @pytest.fixture
    def local_issue(self):
        """Create a local issue that changed from baseline."""
        return Issue(
            id="issue-1",
            title="Original Title",
            status=Status.IN_PROGRESS,
            assignee="alice",
            milestone="v1.0",
            content="Original description",
            labels=["bug"],
            updated=datetime.now(timezone.utc),
        )

    @pytest.fixture
    def remote_issue(self):
        """Create a remote issue that changed from baseline."""
        return {
            "id": "issue-1",
            "title": "Original Title",
            "status": Status.CLOSED,
            "assignee": "bob",
            "milestone": "v1.0",
            "description": "Original description",
            "labels": ["bug"],
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

    def test_analyze_three_way_both_changed(
        self, comparator, baseline_state, local_issue, remote_issue
    ):
        """Test three-way analysis when both local and remote changed."""
        changes = comparator.analyze_three_way(
            local={"issue-1": local_issue},
            remote={"issue-1": remote_issue},
            baseline={"issue-1": baseline_state},
        )

        assert len(changes) == 1
        change = changes[0]
        assert change.issue_id == "issue-1"
        assert change.baseline_state == baseline_state
        assert change.local_state == local_issue
        assert change.remote_state == remote_issue
        assert change.conflict_type == "both_changed"
        assert change.has_conflict is True
        assert "status" in change.local_changes
        assert "status" in change.remote_changes
        assert change.is_three_way_conflict()

    def test_analyze_three_way_local_only_changed(self, comparator, baseline_state):
        """Test three-way analysis when only local changed."""
        local_issue = Issue(
            id="issue-1",
            title="Original Title",
            status=Status.IN_PROGRESS,  # Changed from TODO
            assignee="alice",
            milestone="v1.0",
            content="Original description",
            labels=["bug"],
            updated=datetime.now(timezone.utc),
        )

        remote_issue = {
            "id": "issue-1",
            "title": "Original Title",
            "status": "todo",  # Same as baseline
            "assignee": "alice",
            "milestone": "v1.0",
            "description": "Original description",
            "labels": ["bug"],
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        changes = comparator.analyze_three_way(
            local={"issue-1": local_issue},
            remote={"issue-1": remote_issue},
            baseline={"issue-1": baseline_state},
        )

        assert len(changes) == 1
        change = changes[0]
        assert change.conflict_type == "local_only"
        assert change.has_conflict is False
        assert "status" in change.local_changes
        assert not change.remote_changes
        assert change.is_local_only_change()

    def test_analyze_three_way_remote_only_changed(self, comparator, baseline_state):
        """Test three-way analysis when only remote changed."""
        local_issue = Issue(
            id="issue-1",
            title="Original Title",
            status=Status.TODO,  # Same as baseline
            assignee="alice",
            milestone="v1.0",
            content="Original description",
            labels=["bug"],
            updated=datetime.now(timezone.utc),
        )

        remote_issue = {
            "id": "issue-1",
            "title": "Original Title",
            "status": "closed",  # Changed from baseline
            "assignee": "bob",
            "milestone": "v1.0",
            "description": "Original description",
            "labels": ["bug"],
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        changes = comparator.analyze_three_way(
            local={"issue-1": local_issue},
            remote={"issue-1": remote_issue},
            baseline={"issue-1": baseline_state},
        )

        assert len(changes) == 1
        change = changes[0]
        assert change.conflict_type == "remote_only"
        assert change.has_conflict is False
        assert not change.local_changes
        assert "status" in change.remote_changes
        assert change.is_remote_only_change()

    def test_analyze_three_way_no_changes(self, comparator, baseline_state):
        """Test three-way analysis when nothing changed."""
        local_issue = Issue(
            id="issue-1",
            title="Original Title",
            status=Status.TODO,
            assignee="alice",
            milestone="v1.0",
            content="Original description",
            labels=["bug"],
            updated=datetime.now(timezone.utc),
        )

        remote_issue = {
            "id": "issue-1",
            "title": "Original Title",
            "status": "todo",
            "assignee": "alice",
            "milestone": "v1.0",
            "description": "Original description",
            "labels": ["bug"],
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        changes = comparator.analyze_three_way(
            local={"issue-1": local_issue},
            remote={"issue-1": remote_issue},
            baseline={"issue-1": baseline_state},
        )

        assert len(changes) == 1
        change = changes[0]
        assert change.conflict_type == "no_change"
        assert change.has_conflict is False
        assert not change.local_changes
        assert not change.remote_changes

    def test_analyze_three_way_new_local_issue(self, comparator):
        """Test three-way analysis for new local issue (not in baseline or remote)."""
        local_issue = Issue(
            id="issue-2",
            title="New Issue",
            status=Status.TODO,
            assignee="alice",
            updated=datetime.now(timezone.utc),
        )

        changes = comparator.analyze_three_way(
            local={"issue-2": local_issue},
            remote={},
            baseline={},
        )

        assert len(changes) == 1
        change = changes[0]
        assert change.issue_id == "issue-2"
        assert change.conflict_type == "local_only"
        assert "_new" in change.local_changes

    def test_analyze_three_way_new_remote_issue(self, comparator):
        """Test three-way analysis for new remote issue (not in baseline or local)."""
        remote_issue = {
            "id": "issue-3",
            "title": "New Remote Issue",
            "status": "todo",
            "assignee": "bob",
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        changes = comparator.analyze_three_way(
            local={},
            remote={"issue-3": remote_issue},
            baseline={},
        )

        assert len(changes) == 1
        change = changes[0]
        assert change.issue_id == "issue-3"
        assert change.conflict_type == "remote_only"
        assert "_new" in change.remote_changes

    def test_analyze_three_way_multiple_issues(
        self, comparator, baseline_state, local_issue, remote_issue
    ):
        """Test three-way analysis with multiple issues."""
        # Issue 2: local only changed
        local_issue_2 = Issue(
            id="issue-2",
            title="Issue 2",
            status=Status.IN_PROGRESS,
            assignee="charlie",
            updated=datetime.now(timezone.utc),
        )

        baseline_state_2 = IssueBaseState(
            id="issue-2",
            status="todo",
            title="Issue 2",
            assignee="charlie",
        )

        changes = comparator.analyze_three_way(
            local={"issue-1": local_issue, "issue-2": local_issue_2},
            remote={"issue-1": remote_issue},
            baseline={"issue-1": baseline_state, "issue-2": baseline_state_2},
        )

        assert len(changes) == 2
        issue_1_change = next(c for c in changes if c.issue_id == "issue-1")
        issue_2_change = next(c for c in changes if c.issue_id == "issue-2")

        assert issue_1_change.conflict_type == "both_changed"
        assert issue_2_change.conflict_type == "local_only"

    def test_analyze_three_way_with_no_baseline(self, comparator):
        """Test three-way analysis when baseline is None (first sync)."""
        local_issue = Issue(
            id="issue-1",
            title="New Issue",
            status=Status.TODO,
            assignee="alice",
            updated=datetime.now(timezone.utc),
        )

        remote_issue = {
            "id": "issue-1",
            "title": "New Issue",
            "status": "closed",
            "assignee": "bob",
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        changes = comparator.analyze_three_way(
            local={"issue-1": local_issue},
            remote={"issue-1": remote_issue},
            baseline=None,
        )

        assert len(changes) == 1
        change = changes[0]
        # Both marked as new since no baseline
        assert "_new" in change.local_changes
        assert "_new" in change.remote_changes
        assert change.conflict_type == "both_changed"

    def test_analyze_three_way_deleted_locally(self, comparator, baseline_state):
        """Test three-way analysis when issue deleted locally but exists remotely."""
        remote_issue = {
            "id": "issue-1",
            "title": "Original Title",
            "status": "todo",
            "assignee": "alice",
            "description": "Original description",
            "labels": ["bug"],  # Same as baseline
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        changes = comparator.analyze_three_way(
            local={},  # Deleted locally
            remote={"issue-1": remote_issue},
            baseline={"issue-1": baseline_state},
        )

        assert len(changes) == 1
        change = changes[0]
        assert change.issue_id == "issue-1"
        assert change.local_state is None
        assert not change.local_changes  # No local changes (was deleted)
        assert not change.remote_changes  # Remote unchanged from baseline

    def test_analyze_three_way_labels_comparison(self, comparator):
        """Test three-way analysis correctly compares label arrays."""
        baseline_state = IssueBaseState(
            id="issue-1",
            status="todo",
            title="Test",
            labels=["bug", "feature"],
        )

        local_issue = Issue(
            id="issue-1",
            title="Test",
            status=Status.TODO,
            labels=["bug", "feature"],  # Same but different order
            updated=datetime.now(timezone.utc),
        )

        remote_issue = {
            "id": "issue-1",
            "title": "Test",
            "status": "todo",
            "labels": ["feature", "bug"],  # Different order
        }

        changes = comparator.analyze_three_way(
            local={"issue-1": local_issue},
            remote={"issue-1": remote_issue},
            baseline={"issue-1": baseline_state},
        )

        assert len(changes) == 1
        change = changes[0]
        # Should be no change since sorted labels are same
        assert not change.local_changes
        assert not change.remote_changes
        assert change.conflict_type == "no_change"
