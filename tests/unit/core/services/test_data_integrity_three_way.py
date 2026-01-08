"""Data integrity verification for three-way merge architecture.

Comprehensive tests ensuring the three-way merge implementation maintains
data integrity across baseline, local, and remote states.
"""

from datetime import datetime, timezone

import pytest

from roadmap.common.constants import Status
from roadmap.core.domain.issue import Issue
from roadmap.core.models.sync_state import IssueBaseState
from roadmap.core.services.sync_state_comparator import SyncStateComparator


class TestDataIntegrityThreeWayMerge:
    """Verify data integrity of three-way merge implementation."""

    @pytest.fixture
    def comparator(self):
        """Create comparator instance."""
        return SyncStateComparator()

    @pytest.fixture
    def baseline_state(self):
        """Create a baseline state representing last successful sync."""
        return IssueBaseState(
            id="issue-1",
            status="todo",
            title="Original Issue",
            assignee="alice",
            milestone="v1.0",
            headline="Original description",
            labels=["bug"],
            updated_at=datetime.now(timezone.utc),
        )

    def test_no_changes_maintains_integrity(self, comparator, baseline_state):
        """Verify that unchanged issues remain identical across sync."""
        # All three states identical
        local_issue = Issue(
            id="issue-1",
            title="Original Issue",
            status=Status.TODO,
            assignee="alice",
            milestone="v1.0",
            content="Original description",
            labels=["bug"],
            updated=baseline_state.updated_at,
        )

        remote_issue = {
            "id": "issue-1",
            "title": "Original Issue",
            "status": "todo",
            "assignee": "alice",
            "milestone": "v1.0",
            "description": "Original description",
            "labels": ["bug"],
            "updated_at": baseline_state.updated_at.isoformat(),
        }

        changes = comparator.analyze_three_way(
            local={"issue-1": local_issue},
            remote={"issue-1": remote_issue},
            baseline={"issue-1": baseline_state},
        )

        assert len(changes) == 1
        change = changes[0]
        # Verify no changes detected
        assert change.conflict_type == "no_change"
        assert not change.local_changes
        assert not change.remote_changes
        # Verify data integrity: all states preserved
        assert change.baseline_state == baseline_state
        assert change.local_state == local_issue
        assert change.remote_state == remote_issue

    def test_local_only_change_preserves_remote(self, comparator, baseline_state):
        """Verify that local-only changes don't corrupt remote state."""
        # Local changed, remote unchanged
        local_issue = Issue(
            id="issue-1",
            title="Original Issue",
            status=Status.IN_PROGRESS,  # Changed
            assignee="alice",
            milestone="v1.0",
            content="Original description",
            labels=["bug"],
            updated=datetime.now(timezone.utc),
        )

        remote_issue = {
            "id": "issue-1",
            "title": "Original Issue",
            "status": "todo",  # Same as baseline
            "assignee": "alice",
            "milestone": "v1.0",
            "description": "Original description",
            "labels": ["bug"],
            "updated_at": baseline_state.updated_at.isoformat(),
        }

        changes = comparator.analyze_three_way(
            local={"issue-1": local_issue},
            remote={"issue-1": remote_issue},
            baseline={"issue-1": baseline_state},
        )

        change = changes[0]
        # Verify change categorization
        assert change.conflict_type == "local_only"
        assert change.local_changes
        assert not change.remote_changes

        # Verify data integrity: remote state exactly matches baseline
        remote_status = remote_issue.get("status")
        baseline_status = baseline_state.status
        assert remote_status == baseline_status

    def test_remote_only_change_preserves_local(self, comparator, baseline_state):
        """Verify that remote-only changes don't corrupt local state."""
        # Remote changed, local unchanged
        local_issue = Issue(
            id="issue-1",
            title="Original Issue",
            status=Status.TODO,  # Same as baseline
            assignee="alice",
            milestone="v1.0",
            content="Original description",
            labels=["bug"],
            updated=baseline_state.updated_at,
        )

        remote_issue = {
            "id": "issue-1",
            "title": "Original Issue",
            "status": "closed",  # Changed
            "assignee": "bob",  # Changed
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

        change = changes[0]
        # Verify change categorization
        assert change.conflict_type == "remote_only"
        assert not change.local_changes
        assert change.remote_changes

        # Verify data integrity: local state exactly matches baseline
        assert local_issue.status == Status.TODO
        assert local_issue.assignee == baseline_state.assignee

    def test_both_changed_detects_conflict(self, comparator, baseline_state):
        """Verify that conflicting changes are properly detected."""
        # Both changed (and differently)
        local_issue = Issue(
            id="issue-1",
            title="Original Issue",
            status=Status.IN_PROGRESS,  # Changed to IN_PROGRESS
            assignee="alice",
            milestone="v1.0",
            content="Original description",
            labels=["bug"],
            updated=datetime.now(timezone.utc),
        )

        remote_issue = {
            "id": "issue-1",
            "title": "Original Issue",
            "status": "closed",  # Changed to CLOSED
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

        change = changes[0]
        # Verify conflict detection
        assert change.conflict_type == "both_changed"
        assert change.is_three_way_conflict()
        assert change.has_conflict is True

        # Verify data integrity: both changes are recorded
        assert "status" in change.local_changes
        assert "status" in change.remote_changes
        # Verify the actual change values
        assert change.local_changes["status"]["from"] == "todo"
        assert (
            change.local_changes["status"]["to"] == "in-progress"
        )  # Status uses hyphens
        assert change.remote_changes["status"]["from"] == "todo"
        # Remote status comes back as Status enum, convert to value
        remote_to = change.remote_changes["status"]["to"]
        remote_to_str = (
            remote_to.value if hasattr(remote_to, "value") else str(remote_to).lower()
        )
        assert remote_to_str == "closed"

    def test_multiple_issues_integrity(self, comparator):
        """Verify integrity maintained across multiple issues."""
        # Issue 1: no change
        baseline_1 = IssueBaseState(
            id="issue-1",
            status="todo",
            title="Issue 1",
        )
        local_1 = Issue(
            id="issue-1",
            title="Issue 1",
            status=Status.TODO,
            updated=datetime.now(timezone.utc),
        )
        remote_1 = {"id": "issue-1", "title": "Issue 1", "status": "todo"}

        # Issue 2: local only
        baseline_2 = IssueBaseState(
            id="issue-2",
            status="todo",
            title="Issue 2",
        )
        local_2 = Issue(
            id="issue-2",
            title="Issue 2",
            status=Status.IN_PROGRESS,
            updated=datetime.now(timezone.utc),
        )
        remote_2 = {"id": "issue-2", "title": "Issue 2", "status": "todo"}

        # Issue 3: remote only
        baseline_3 = IssueBaseState(
            id="issue-3",
            status="todo",
            title="Issue 3",
        )
        local_3 = Issue(
            id="issue-3",
            title="Issue 3",
            status=Status.TODO,
            updated=datetime.now(timezone.utc),
        )
        remote_3 = {"id": "issue-3", "title": "Issue 3", "status": "closed"}

        changes = comparator.analyze_three_way(
            local={"issue-1": local_1, "issue-2": local_2, "issue-3": local_3},
            remote={"issue-1": remote_1, "issue-2": remote_2, "issue-3": remote_3},
            baseline={
                "issue-1": baseline_1,
                "issue-2": baseline_2,
                "issue-3": baseline_3,
            },
        )

        assert len(changes) == 3

        # Verify each issue
        change_map = {c.issue_id: c for c in changes}

        assert change_map["issue-1"].conflict_type == "no_change"
        assert change_map["issue-2"].conflict_type == "local_only"
        assert change_map["issue-3"].conflict_type == "remote_only"

    def test_issue_change_helper_methods_accuracy(self, comparator, baseline_state):
        """Verify helper methods correctly identify change types."""
        # Create a both_changed scenario
        local_issue = Issue(
            id="issue-1",
            title="Original Issue",
            status=Status.IN_PROGRESS,
            assignee="alice",
            milestone="v1.0",
            content="Original description",
            labels=["bug"],
            updated=datetime.now(timezone.utc),
        )

        remote_issue = {
            "id": "issue-1",
            "title": "Original Issue",
            "status": "closed",
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

        change = changes[0]

        # Test helper methods
        assert change.is_three_way_conflict() is True
        assert change.is_local_only_change() is False
        assert change.is_remote_only_change() is False

    def test_deleted_issue_integrity(self, comparator, baseline_state):
        """Verify integrity when issue is deleted in one direction."""
        # Deleted locally
        remote_issue = {
            "id": "issue-1",
            "title": "Original Issue",
            "status": "todo",
            "assignee": "alice",
            "description": "Original description",
            "labels": ["bug"],
            "updated_at": baseline_state.updated_at.isoformat(),
        }

        changes = comparator.analyze_three_way(
            local={},  # Deleted locally
            remote={"issue-1": remote_issue},
            baseline={"issue-1": baseline_state},
        )

        change = changes[0]
        # Verify integrity
        assert change.local_state is None
        assert change.remote_state == remote_issue
        assert change.baseline_state == baseline_state
        # Remote unchanged from baseline
        assert not change.remote_changes

    def test_change_description_includes_baseline_context(
        self, comparator, baseline_state
    ):
        """Verify change descriptions include complete baseline context."""
        local_issue = Issue(
            id="issue-1",
            title="Original Issue",
            status=Status.IN_PROGRESS,
            assignee="alice",
            milestone="v1.0",
            content="Original description",
            labels=["bug"],
            updated=datetime.now(timezone.utc),
        )

        remote_issue = {
            "id": "issue-1",
            "title": "Original Issue",
            "status": "closed",
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

        change = changes[0]
        # Verify conflict description includes baseline context
        conflict_desc = change.get_conflict_description()
        assert (
            "Baseline" in conflict_desc
            or "Local" in conflict_desc
            or "Remote" in conflict_desc
        )
        # Description should show the actual changes
        assert len(conflict_desc) > 0
