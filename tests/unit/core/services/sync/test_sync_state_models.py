"""Tests for sync_state models: IssueBaseState and SyncState."""

from datetime import UTC, datetime

import pytest

from roadmap.core.services.sync.sync_state import IssueBaseState, SyncState


class TestIssueBaseState:
    """Tests for IssueBaseState dataclass."""

    def test_issue_base_state_initialization_required_fields(self):
        """IssueBaseState should initialize with required id and status."""
        issue = IssueBaseState(id="issue-1", status="open")
        assert issue.id == "issue-1"
        assert issue.status == "open"
        assert issue.assignee is None
        assert issue.labels == []
        assert issue.description == ""
        assert issue.title == ""
        assert issue.priority == 0
        assert issue.blocked_by == []
        assert issue.blocks == []
        assert issue.created_at is None
        assert issue.updated_at is None
        assert issue.archived is False
        assert issue.custom_fields == {}

    def test_issue_base_state_with_all_fields(self):
        """IssueBaseState should initialize with all provided fields."""
        now = datetime.now(UTC)
        issue = IssueBaseState(
            id="issue-1",
            status="in-progress",
            assignee="alice",
            labels=["bug", "high-priority"],
            description="A test issue",
            title="Test Issue",
            priority=1,
            blocked_by=["issue-2"],
            blocks=["issue-3"],
            created_at=now,
            updated_at=now,
            archived=False,
            custom_fields={"team": "backend"},
        )
        assert issue.id == "issue-1"
        assert issue.status == "in-progress"
        assert issue.assignee == "alice"
        assert issue.labels == ["bug", "high-priority"]
        assert issue.description == "A test issue"
        assert issue.title == "Test Issue"
        assert issue.priority == 1
        assert issue.blocked_by == ["issue-2"]
        assert issue.blocks == ["issue-3"]
        assert issue.created_at == now
        assert issue.updated_at == now
        assert issue.archived is False
        assert issue.custom_fields == {"team": "backend"}

    def test_issue_base_state_to_dict(self):
        """to_dict should convert IssueBaseState to dictionary."""
        now = datetime.now(UTC)
        issue = IssueBaseState(
            id="issue-1",
            status="closed",
            assignee="bob",
            labels=["feature"],
            description="Feature description",
            title="Feature Title",
            priority=2,
            blocked_by=["issue-4"],
            blocks=["issue-5"],
            created_at=now,
            updated_at=now,
            archived=True,
            custom_fields={"version": "1.0"},
        )
        result = issue.to_dict()
        assert result == {
            "id": "issue-1",
            "status": "closed",
            "assignee": "bob",
            "labels": ["feature"],
            "description": "Feature description",
            "title": "Feature Title",
            "priority": 2,
            "blocked_by": ["issue-4"],
            "blocks": ["issue-5"],
            "created_at": now,
            "updated_at": now,
            "archived": True,
            "custom_fields": {"version": "1.0"},
        }

    def test_issue_base_state_to_dict_with_minimal_fields(self):
        """to_dict should work with minimal field initialization."""
        issue = IssueBaseState(id="issue-1", status="open")
        result = issue.to_dict()
        assert result["id"] == "issue-1"
        assert result["status"] == "open"
        assert result["assignee"] is None
        assert result["labels"] == []
        assert result["description"] == ""
        assert result["title"] == ""
        assert result["priority"] == 0
        assert result["blocked_by"] == []
        assert result["blocks"] == []
        assert result["created_at"] is None
        assert result["updated_at"] is None
        assert result["archived"] is False
        assert result["custom_fields"] == {}

    def test_issue_base_state_from_dict(self):
        """from_dict should create IssueBaseState from dictionary."""
        now = datetime.now(UTC)
        data = {
            "id": "issue-1",
            "status": "pending",
            "assignee": "charlie",
            "labels": ["documentation"],
            "description": "Update docs",
            "title": "Docs Update",
            "priority": 0,
            "blocked_by": ["issue-6"],
            "blocks": [],
            "created_at": now,
            "updated_at": now,
            "archived": False,
            "custom_fields": {"epic": "phase-2"},
        }
        issue = IssueBaseState.from_dict(data)
        assert issue.id == "issue-1"
        assert issue.status == "pending"
        assert issue.assignee == "charlie"
        assert issue.labels == ["documentation"]
        assert issue.description == "Update docs"
        assert issue.title == "Docs Update"
        assert issue.priority == 0
        assert issue.blocked_by == ["issue-6"]
        assert issue.blocks == []
        assert issue.created_at == now
        assert issue.updated_at == now
        assert issue.archived is False
        assert issue.custom_fields == {"epic": "phase-2"}

    def test_issue_base_state_roundtrip_to_dict_from_dict(self):
        """to_dict and from_dict should preserve all data in roundtrip."""
        now = datetime.now(UTC)
        original = IssueBaseState(
            id="issue-100",
            status="resolved",
            assignee="diana",
            labels=["critical", "security"],
            description="Security fix needed",
            title="Security Issue",
            priority=3,
            blocked_by=["issue-50"],
            blocks=["issue-60", "issue-70"],
            created_at=now,
            updated_at=now,
            archived=True,
            custom_fields={"severity": "high", "cve": "CVE-2024-001"},
        )
        dict_form = original.to_dict()
        restored = IssueBaseState.from_dict(dict_form)
        assert restored.id == original.id
        assert restored.status == original.status
        assert restored.assignee == original.assignee
        assert restored.labels == original.labels
        assert restored.description == original.description
        assert restored.title == original.title
        assert restored.priority == original.priority
        assert restored.blocked_by == original.blocked_by
        assert restored.blocks == original.blocks
        assert restored.created_at == original.created_at
        assert restored.updated_at == original.updated_at
        assert restored.archived == original.archived
        assert restored.custom_fields == original.custom_fields

    def test_issue_base_state_with_empty_lists_and_dicts(self):
        """IssueBaseState should handle empty lists and dicts correctly."""
        issue = IssueBaseState(
            id="issue-1",
            status="open",
            labels=[],
            blocked_by=[],
            blocks=[],
            custom_fields={},
        )
        result = issue.to_dict()
        assert result["labels"] == []
        assert result["blocked_by"] == []
        assert result["blocks"] == []
        assert result["custom_fields"] == {}

    def test_issue_base_state_from_dict_with_minimal_data(self):
        """from_dict should handle minimal required data."""
        data = {"id": "issue-1", "status": "open"}
        issue = IssueBaseState.from_dict(data)
        assert issue.id == "issue-1"
        assert issue.status == "open"


class TestSyncState:
    """Tests for SyncState dataclass."""

    def test_sync_state_initialization_empty(self):
        """SyncState should initialize with empty defaults."""
        state = SyncState()
        assert state.local_issues == {}
        assert state.remote_issues == {}
        assert state.base_issues == {}
        assert state.last_sync_time is None
        assert state.sync_in_progress is False
        assert state.local_deleted_ids == set()
        assert state.remote_deleted_ids == set()

    def test_sync_state_get_issue_dict_local_empty(self):
        """get_issue_dict should return empty dict for local when no issues."""
        state = SyncState()
        result = state.get_issue_dict("local")
        assert result == {}

    def test_sync_state_get_issue_dict_remote_empty(self):
        """get_issue_dict should return empty dict for remote when no issues."""
        state = SyncState()
        result = state.get_issue_dict("remote")
        assert result == {}

    def test_sync_state_get_issue_dict_base_empty(self):
        """get_issue_dict should return empty dict for base when no issues."""
        state = SyncState()
        result = state.get_issue_dict("base")
        assert result == {}

    def test_sync_state_get_issue_dict_invalid_source(self):
        """get_issue_dict should raise ValueError for invalid source."""
        state = SyncState()
        with pytest.raises(ValueError, match="Unknown source: invalid"):
            state.get_issue_dict("invalid")

    def test_sync_state_get_issue_dict_local_with_issues(self):
        """get_issue_dict should return dict of issue dicts for local."""
        state = SyncState()
        issue1 = IssueBaseState(id="issue-1", status="open", title="First")
        issue2 = IssueBaseState(id="issue-2", status="closed", title="Second")
        state.local_issues = {"issue-1": issue1, "issue-2": issue2}
        result = state.get_issue_dict("local")
        assert len(result) == 2
        assert result["issue-1"]["id"] == "issue-1"
        assert result["issue-1"]["status"] == "open"
        assert result["issue-1"]["title"] == "First"
        assert result["issue-2"]["id"] == "issue-2"
        assert result["issue-2"]["status"] == "closed"
        assert result["issue-2"]["title"] == "Second"

    def test_sync_state_get_issue_dict_remote_with_issues(self):
        """get_issue_dict should return dict of issue dicts for remote."""
        state = SyncState()
        issue1 = IssueBaseState(id="remote-1", status="in-progress")
        state.remote_issues = {"remote-1": issue1}
        result = state.get_issue_dict("remote")
        assert len(result) == 1
        assert result["remote-1"]["id"] == "remote-1"

    def test_sync_state_get_issue_dict_base_with_issues(self):
        """get_issue_dict should return dict of issue dicts for base."""
        state = SyncState()
        issue1 = IssueBaseState(id="base-1", status="pending")
        state.base_issues = {"base-1": issue1}
        result = state.get_issue_dict("base")
        assert len(result) == 1
        assert result["base-1"]["id"] == "base-1"

    def test_sync_state_add_issue_local(self):
        """add_issue should add issue to local source."""
        state = SyncState()
        issue = IssueBaseState(id="issue-1", status="open")
        state.add_issue("local", issue)
        assert "issue-1" in state.local_issues
        assert state.local_issues["issue-1"] == issue

    def test_sync_state_add_issue_remote(self):
        """add_issue should add issue to remote source."""
        state = SyncState()
        issue = IssueBaseState(id="issue-1", status="open")
        state.add_issue("remote", issue)
        assert "issue-1" in state.remote_issues
        assert state.remote_issues["issue-1"] == issue

    def test_sync_state_add_issue_base(self):
        """add_issue should add issue to base source."""
        state = SyncState()
        issue = IssueBaseState(id="issue-1", status="open")
        state.add_issue("base", issue)
        assert "issue-1" in state.base_issues
        assert state.base_issues["issue-1"] == issue

    def test_sync_state_add_issue_invalid_source(self):
        """add_issue should raise ValueError for invalid source."""
        state = SyncState()
        issue = IssueBaseState(id="issue-1", status="open")
        with pytest.raises(ValueError, match="Unknown source: invalid"):
            state.add_issue("invalid", issue)

    def test_sync_state_add_issue_overwrites_existing(self):
        """add_issue should overwrite existing issue with same id."""
        state = SyncState()
        issue1 = IssueBaseState(id="issue-1", status="open", title="First")
        issue2 = IssueBaseState(id="issue-1", status="closed", title="Second")
        state.add_issue("local", issue1)
        state.add_issue("local", issue2)
        assert state.local_issues["issue-1"].title == "Second"
        assert state.local_issues["issue-1"].status == "closed"

    def test_sync_state_get_issue_local(self):
        """get_issue should retrieve issue from local source."""
        state = SyncState()
        issue = IssueBaseState(id="issue-1", status="open")
        state.local_issues["issue-1"] = issue
        result = state.get_issue("local", "issue-1")
        assert result == issue

    def test_sync_state_get_issue_remote(self):
        """get_issue should retrieve issue from remote source."""
        state = SyncState()
        issue = IssueBaseState(id="issue-1", status="open")
        state.remote_issues["issue-1"] = issue
        result = state.get_issue("remote", "issue-1")
        assert result == issue

    def test_sync_state_get_issue_base(self):
        """get_issue should retrieve issue from base source."""
        state = SyncState()
        issue = IssueBaseState(id="issue-1", status="open")
        state.base_issues["issue-1"] = issue
        result = state.get_issue("base", "issue-1")
        assert result == issue

    def test_sync_state_get_issue_nonexistent(self):
        """get_issue should return None for non-existent issue."""
        state = SyncState()
        result = state.get_issue("local", "nonexistent")
        assert result is None

    def test_sync_state_get_issue_invalid_source(self):
        """get_issue should raise ValueError for invalid source."""
        state = SyncState()
        with pytest.raises(ValueError, match="Unknown source: invalid"):
            state.get_issue("invalid", "issue-1")

    def test_sync_state_mark_deleted_local(self):
        """mark_deleted should remove issue from local and track deletion."""
        state = SyncState()
        issue = IssueBaseState(id="issue-1", status="open")
        state.local_issues["issue-1"] = issue
        state.mark_deleted("local", "issue-1")
        assert "issue-1" not in state.local_issues
        assert "issue-1" in state.local_deleted_ids

    def test_sync_state_mark_deleted_remote(self):
        """mark_deleted should remove issue from remote and track deletion."""
        state = SyncState()
        issue = IssueBaseState(id="issue-1", status="open")
        state.remote_issues["issue-1"] = issue
        state.mark_deleted("remote", "issue-1")
        assert "issue-1" not in state.remote_issues
        assert "issue-1" in state.remote_deleted_ids

    def test_sync_state_mark_deleted_nonexistent_issue(self):
        """mark_deleted should still track deletion even if issue not present."""
        state = SyncState()
        state.mark_deleted("local", "nonexistent")
        assert "nonexistent" in state.local_deleted_ids

    def test_sync_state_mark_deleted_invalid_source(self):
        """mark_deleted should raise ValueError for invalid source."""
        state = SyncState()
        with pytest.raises(ValueError, match="Unknown source: invalid"):
            state.mark_deleted("invalid", "issue-1")

    def test_sync_state_mark_deleted_cannot_delete_base(self):
        """mark_deleted should raise ValueError when trying to delete from base."""
        state = SyncState()
        with pytest.raises(ValueError, match="Unknown source: base"):
            state.mark_deleted("base", "issue-1")

    def test_sync_state_mark_synced(self):
        """mark_synced should set sync_in_progress to False and set last_sync_time."""
        state = SyncState()
        state.sync_in_progress = True
        before = datetime.now(UTC)
        state.mark_synced()
        after = datetime.now(UTC)
        assert state.sync_in_progress is False
        assert state.last_sync_time is not None
        assert before <= state.last_sync_time <= after

    def test_sync_state_mark_synced_multiple_times(self):
        """mark_synced should update last_sync_time each time it's called."""
        state = SyncState()
        state.mark_synced()
        first_sync_time = state.last_sync_time
        assert first_sync_time is not None
        state.mark_synced()
        second_sync_time = state.last_sync_time
        assert second_sync_time is not None
        assert first_sync_time != second_sync_time
        assert second_sync_time > first_sync_time

    def test_sync_state_multiple_operations(self):
        """SyncState should handle complex sequences of operations."""
        state = SyncState()

        # Add issues to different sources
        issue1 = IssueBaseState(id="issue-1", status="open", title="Local")
        issue2 = IssueBaseState(id="issue-2", status="open", title="Remote")
        issue3 = IssueBaseState(id="issue-3", status="open", title="Base")

        state.add_issue("local", issue1)
        state.add_issue("remote", issue2)
        state.add_issue("base", issue3)

        # Verify all were added
        assert len(state.local_issues) == 1
        assert len(state.remote_issues) == 1
        assert len(state.base_issues) == 1

        # Mark one as deleted
        state.mark_deleted("local", "issue-1")
        assert len(state.local_issues) == 0
        assert "issue-1" in state.local_deleted_ids

        # Get remaining issues
        assert state.get_issue("remote", "issue-2") is not None
        assert state.get_issue("base", "issue-3") is not None

        # Mark sync complete
        state.mark_synced()
        assert state.sync_in_progress is False
        assert state.last_sync_time is not None

    def test_sync_state_with_complex_issue_data(self):
        """SyncState should handle complex issue data correctly."""
        now = datetime.now(UTC)
        state = SyncState()

        complex_issue = IssueBaseState(
            id="complex-issue",
            status="blocked",
            assignee="team-lead",
            labels=["urgent", "backend", "database"],
            description="Complex issue with many dependencies",
            title="Database Schema Migration",
            priority=2,
            blocked_by=["issue-100", "issue-101"],
            blocks=["issue-200", "issue-201", "issue-202"],
            created_at=now,
            updated_at=now,
            archived=False,
            custom_fields={
                "epic": "infrastructure",
                "story_points": "13",
                "department": "backend",
                "impact": "high",
            },
        )

        state.add_issue("local", complex_issue)
        retrieved = state.get_issue("local", "complex-issue")

        assert retrieved is not None
