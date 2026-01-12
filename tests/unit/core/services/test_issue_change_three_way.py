"""Tests for three-way IssueChange functionality."""

from datetime import datetime, timezone

import pytest

from roadmap.common.constants import Status
from roadmap.core.domain.issue import Issue
from roadmap.core.models.sync_state import IssueBaseState
from roadmap.core.services.sync.sync_report import IssueChange


@pytest.fixture
def baseline_state():
    """Create a baseline state."""
    return IssueBaseState(
        id="issue-1",
        title="Test Issue",
        status=Status.TODO,
        assignee="alice",
        milestone="v1.0",
        headline="Original description",
        labels=["bug"],
    )


@pytest.fixture
def local_issue():
    """Create a local issue."""
    return Issue(
        id="issue-1",
        title="Test Issue",
        status=Status.IN_PROGRESS,
        assignee="alice",
        milestone="v1.0",
        content="Original description",
        labels=["bug"],
        updated=datetime.now(timezone.utc),
    )


@pytest.fixture
def remote_issue():
    """Create a remote issue dict."""
    return {
        "id": "issue-1",
        "title": "Test Issue",
        "status": Status.CLOSED,
        "assignee": "bob",
        "milestone": "v1.0",
        "description": "Original description",
        "labels": ["bug"],
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


class TestIssueChangeThreeWay:
    """Test three-way conflict detection in IssueChange."""

    def test_creates_with_three_way_states(
        self, baseline_state, local_issue, remote_issue
    ):
        """Should create IssueChange with all three states."""
        change = IssueChange(
            issue_id="issue-1",
            title="Test Issue",
            baseline_state=baseline_state,
            local_state=local_issue,
            remote_state=remote_issue,
        )

        assert change.baseline_state is not None
        assert change.local_state is not None
        assert change.remote_state is not None

    def test_identifies_three_way_conflict(
        self, baseline_state, local_issue, remote_issue
    ):
        """Should identify when both local and remote changed."""
        change = IssueChange(
            issue_id="issue-1",
            title="Test Issue",
            baseline_state=baseline_state,
            local_state=local_issue,
            remote_state=remote_issue,
            local_changes={"status": Status.IN_PROGRESS},
            remote_changes={"status": Status.CLOSED, "assignee": "bob"},
            conflict_type="both_changed",
            has_conflict=True,
        )

        assert change.is_three_way_conflict()
        assert not change.is_local_only_change()
        assert not change.is_remote_only_change()

    def test_identifies_local_only_change(
        self, baseline_state, local_issue, remote_issue
    ):
        """Should identify when only local changed."""
        change = IssueChange(
            issue_id="issue-1",
            title="Test Issue",
            baseline_state=baseline_state,
            local_state=local_issue,
            remote_state=remote_issue,
            local_changes={"status": Status.IN_PROGRESS},
            remote_changes={},
            conflict_type="local_only",
            has_conflict=False,
        )

        assert not change.is_three_way_conflict()
        assert change.is_local_only_change()
        assert not change.is_remote_only_change()

    def test_identifies_remote_only_change(
        self, baseline_state, local_issue, remote_issue
    ):
        """Should identify when only remote changed."""
        change = IssueChange(
            issue_id="issue-1",
            title="Test Issue",
            baseline_state=baseline_state,
            local_state=local_issue,
            remote_state=remote_issue,
            local_changes={},
            remote_changes={"assignee": "bob"},
            conflict_type="remote_only",
            has_conflict=False,
        )

        assert not change.is_three_way_conflict()
        assert not change.is_local_only_change()
        assert change.is_remote_only_change()

    def test_identifies_no_change(self, baseline_state, local_issue, remote_issue):
        """Should identify when nothing changed."""
        change = IssueChange(
            issue_id="issue-1",
            title="Test Issue",
            baseline_state=baseline_state,
            local_state=local_issue,
            remote_state=remote_issue,
            local_changes={},
            remote_changes={},
            conflict_type="no_change",
            has_conflict=False,
        )

        assert not change.is_three_way_conflict()
        assert not change.is_local_only_change()
        assert not change.is_remote_only_change()

    def test_conflict_description_includes_three_way_context(
        self, baseline_state, local_issue, remote_issue
    ):
        """Should include baseline context in conflict description."""
        change = IssueChange(
            issue_id="issue-1",
            title="Test Issue",
            baseline_state=baseline_state,
            local_state=local_issue,
            remote_state=remote_issue,
            local_changes={"status": Status.IN_PROGRESS},
            remote_changes={"status": Status.CLOSED},
            conflict_type="both_changed",
            has_conflict=True,
        )

        description = change.get_conflict_description()
        assert "Baseline" in description
        assert "Local" in description
        assert "Remote" in description

    def test_handles_missing_baseline(self):
        """Should handle missing baseline gracefully."""
        change = IssueChange(
            issue_id="issue-1",
            title="Test Issue",
            baseline_state=None,
            local_state=None,
            remote_state={"id": "issue-1", "status": "TODO"},
            local_changes={},
            remote_changes={"status": "TODO"},
            conflict_type="remote_only",
        )

        assert change.is_remote_only_change()

    def test_backward_compatibility_fields(
        self, baseline_state, local_issue, remote_issue
    ):
        """Should support legacy github_changes and last_sync_time fields."""
        last_sync = datetime.now(timezone.utc)
        change = IssueChange(
            issue_id="issue-1",
            title="Test Issue",
            baseline_state=baseline_state,
            local_state=local_issue,
            remote_state=remote_issue,
            github_changes={"status": "DONE"},
            last_sync_time=last_sync,
        )

        assert change.github_changes == {"status": "DONE"}
        assert change.last_sync_time == last_sync
