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
            "headline": "",
            "content": "",
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
        assert retrieved.assignee == "team-lead"
        assert len(retrieved.labels) == 3
        assert len(retrieved.blocked_by) == 2
        assert len(retrieved.blocks) == 3
        assert len(retrieved.custom_fields) == 4
        assert retrieved.custom_fields["story_points"] == "13"


class TestSyncStateUnhappyPaths:
    """Tests for unhappy paths and error conditions."""

    def test_three_way_merge_scenario_no_conflict(self):
        """Three sources should track diverging states without conflict."""
        now = datetime.now(UTC)
        state = SyncState()

        # Simulate three-way merge: base → local + remote
        base = IssueBaseState(
            id="issue-1",
            status="open",
            title="Original",
            assignee="alice",
        )
        local = IssueBaseState(
            id="issue-1",
            status="in-progress",  # Local modified
            title="Original",
            assignee="alice",
            updated_at=now,
        )
        remote = IssueBaseState(
            id="issue-1",
            status="open",  # Remote unchanged
            title="Original",
            assignee="bob",  # Remote modified
            updated_at=now,
        )

        state.add_issue("base", base)
        state.add_issue("local", local)
        state.add_issue("remote", remote)

        # All three should be stored independently
        base_issue = state.get_issue("base", "issue-1")
        assert base_issue is not None and base_issue.status == "open"
        local_issue = state.get_issue("local", "issue-1")
        assert local_issue is not None and local_issue.status == "in-progress"
        remote_issue = state.get_issue("remote", "issue-1")
        assert remote_issue is not None and remote_issue.assignee == "bob"

    def test_three_way_merge_scenario_both_sides_deleted(self):
        """When both sides delete same issue, track both deletions."""
        state = SyncState()

        # Start with issue in all three
        issue = IssueBaseState(id="issue-1", status="open")
        state.add_issue("base", issue)
        state.add_issue("local", issue)
        state.add_issue("remote", issue)

        # Both sides delete it
        state.mark_deleted("local", "issue-1")
        state.mark_deleted("remote", "issue-1")

        # Issue should be removed from both local and remote
        assert state.get_issue("local", "issue-1") is None
        assert state.get_issue("remote", "issue-1") is None

        # But deletion should be tracked
        assert "issue-1" in state.local_deleted_ids
        assert "issue-1" in state.remote_deleted_ids

        # Base should still have it (represents agreed-upon state from last sync)
        assert state.get_issue("base", "issue-1") is not None

    def test_three_way_merge_scenario_one_side_deleted(self):
        """When only one side deletes, it should be tracked separately."""
        state = SyncState()

        issue = IssueBaseState(id="issue-1", status="open")
        state.add_issue("base", issue)
        state.add_issue("local", issue)
        state.add_issue("remote", issue)

        # Only local deletes
        state.mark_deleted("local", "issue-1")

        # Local should show deletion
        assert "issue-1" in state.local_deleted_ids
        assert state.get_issue("local", "issue-1") is None

        # Remote should still have it (divergence!)
        assert state.get_issue("remote", "issue-1") is not None
        assert "issue-1" not in state.remote_deleted_ids

    def test_sync_state_inconsistent_sources_allowed(self):
        """SyncState should allow storing inconsistent state across sources."""
        state = SyncState()

        # Same ID with completely different states
        local_issue = IssueBaseState(
            id="issue-1",
            status="closed",
            assignee="alice",
            title="Fixed in local",
        )
        remote_issue = IssueBaseState(
            id="issue-1",
            status="open",
            assignee="bob",
            title="Still open remotely",
        )

        state.add_issue("local", local_issue)
        state.add_issue("remote", remote_issue)

        # Both should coexist
        local_result = state.get_issue("local", "issue-1")
        assert local_result is not None and local_result.status == "closed"
        remote_result = state.get_issue("remote", "issue-1")
        assert remote_result is not None and remote_result.status == "open"

    def test_mark_deleted_removes_from_correct_source_only(self):
        """Deleting from one source should not affect others."""
        issue = IssueBaseState(id="issue-1", status="open")
        state = SyncState()

        # Add to all three sources
        state.add_issue("local", issue)
        state.add_issue("remote", issue)
        state.add_issue("base", issue)

        # Delete from local only
        state.mark_deleted("local", "issue-1")

        # Verify state
        assert state.get_issue("local", "issue-1") is None
        assert state.get_issue("remote", "issue-1") is not None
        assert state.get_issue("base", "issue-1") is not None

    def test_deleted_ids_independent_across_sources(self):
        """Deletion tracking should be separate per source."""
        state = SyncState()

        issue1 = IssueBaseState(id="issue-1", status="open")
        issue2 = IssueBaseState(id="issue-2", status="open")

        state.add_issue("local", issue1)
        state.add_issue("local", issue2)
        state.add_issue("remote", issue1)
        state.add_issue("remote", issue2)

        # Delete different issues from each source
        state.mark_deleted("local", "issue-1")
        state.mark_deleted("remote", "issue-2")

        # Verify tracking
        assert "issue-1" in state.local_deleted_ids
        assert "issue-1" not in state.remote_deleted_ids
        assert "issue-2" not in state.local_deleted_ids
        assert "issue-2" in state.remote_deleted_ids

    def test_sync_progress_flag_lifecycle(self):
        """sync_in_progress flag should control sync state transitions."""
        state = SyncState()

        # Initially not syncing
        assert state.sync_in_progress is False
        assert state.last_sync_time is None

        # Simulate starting sync
        state.sync_in_progress = True
        assert state.sync_in_progress is True
        assert state.last_sync_time is None  # Not updated yet

        # Complete sync
        state.mark_synced()
        assert state.sync_in_progress is False
        assert state.last_sync_time is not None

    def test_mark_synced_called_during_sync_in_progress(self):
        """mark_synced should reset flag regardless of previous state."""
        state = SyncState()
        state.sync_in_progress = True

        state.mark_synced()

        # Flag should be reset
        assert state.sync_in_progress is False
        # Time should be set
        assert state.last_sync_time is not None

    def test_sync_state_with_deleted_but_still_tracked_issue(self):
        """Issue can be deleted but still tracked in deletion set."""
        state = SyncState()
        issue = IssueBaseState(id="issue-1", status="open")

        state.add_issue("local", issue)
        assert "issue-1" not in state.local_deleted_ids

        # Delete it
        state.mark_deleted("local", "issue-1")

        # Now it should be tracked as deleted
        assert "issue-1" in state.local_deleted_ids
        # But removed from active issues
        assert state.get_issue("local", "issue-1") is None

    def test_re_add_deleted_issue_clears_deletion_flag(self):
        """Adding a deleted issue back should allow undelete scenarios."""
        state = SyncState()
        issue = IssueBaseState(id="issue-1", status="open")

        state.add_issue("local", issue)
        state.mark_deleted("local", "issue-1")
        assert "issue-1" in state.local_deleted_ids

        # Re-add the issue
        state.add_issue("local", issue)

        # Issue is back but deletion flag persists (for history)
        assert state.get_issue("local", "issue-1") is not None
        assert "issue-1" in state.local_deleted_ids  # Still marked as deleted

    def test_get_issue_dict_reflects_current_state(self):
        """get_issue_dict should only include current issues, not deleted ones."""
        state = SyncState()
        issue1 = IssueBaseState(id="issue-1", status="open")
        issue2 = IssueBaseState(id="issue-2", status="open")

        state.add_issue("local", issue1)
        state.add_issue("local", issue2)

        # Get dict before deletion
        dict_before = state.get_issue_dict("local")
        assert len(dict_before) == 2

        # Delete one
        state.mark_deleted("local", "issue-1")

        # Get dict after deletion
        dict_after = state.get_issue_dict("local")
        assert len(dict_after) == 1
        assert "issue-1" not in dict_after
        assert "issue-2" in dict_after

    def test_operations_on_nonexistent_issue_idempotent(self):
        """Operations on non-existent issues should be safe."""
        state = SyncState()

        # Getting non-existent issue
        result = state.get_issue("local", "nonexistent")
        assert result is None

        # Deleting non-existent issue should not crash
        state.mark_deleted("local", "nonexistent")
        assert "nonexistent" in state.local_deleted_ids

        # Getting issue_dict should work even with deleted non-existent
        dict_result = state.get_issue_dict("local")
        assert dict_result == {}

    def test_issue_state_independence_across_sources(self):
        """Modifying issue in one source should not affect others."""
        state = SyncState()

        issue1_v1 = IssueBaseState(
            id="issue-1",
            status="open",
            title="Version 1",
        )
        issue1_v2 = IssueBaseState(
            id="issue-1",
            status="closed",
            title="Version 2",
        )

        state.add_issue("local", issue1_v1)
        state.add_issue("remote", issue1_v2)

        # They should remain independent
        local_v1 = state.get_issue("local", "issue-1")
        assert local_v1 is not None and local_v1.title == "Version 1"
        remote_v1 = state.get_issue("remote", "issue-1")
        assert remote_v1 is not None and remote_v1.title == "Version 2"

        # Updating local should not affect remote
        updated = IssueBaseState(
            id="issue-1",
            status="in-progress",
            title="Version 3",
        )
        state.add_issue("local", updated)

        local_v3 = state.get_issue("local", "issue-1")
        assert local_v3 is not None and local_v3.title == "Version 3"
        remote_v2 = state.get_issue("remote", "issue-1")
        assert remote_v2 is not None and remote_v2.title == "Version 2"

    def test_large_scale_issue_tracking(self):
        """SyncState should efficiently handle many issues."""
        state = SyncState()

        # Add many issues
        for i in range(1000):
            issue = IssueBaseState(id=f"issue-{i}", status="open")
            state.add_issue("local", issue)

        assert len(state.local_issues) == 1000
        assert len(state.get_issue_dict("local")) == 1000

        # Delete half of them
        for i in range(0, 1000, 2):
            state.mark_deleted("local", f"issue-{i}")

        assert len(state.local_deleted_ids) == 500
        assert len(state.get_issue_dict("local")) == 500

    def test_sync_state_with_circular_dependencies(self):
        """SyncState should handle circular blocking relationships."""
        state = SyncState()

        # Create circular dependency: A blocks B, B blocks A
        issue_a = IssueBaseState(
            id="issue-a",
            status="blocked",
            blocks=["issue-b"],
            blocked_by=["issue-b"],
        )
        issue_b = IssueBaseState(
            id="issue-b",
            status="blocked",
            blocks=["issue-a"],
            blocked_by=["issue-a"],
        )

        state.add_issue("local", issue_a)
        state.add_issue("local", issue_b)

        # Should be stored without issue
        retrieved_a = state.get_issue("local", "issue-a")
        assert retrieved_a is not None and "issue-b" in retrieved_a.blocks
        assert retrieved_a is not None and "issue-b" in retrieved_a.blocked_by
