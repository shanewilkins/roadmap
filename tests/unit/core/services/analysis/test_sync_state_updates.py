"""Tests for sync state updates after push operations."""

from pathlib import Path

import pytest

from roadmap.common.constants import Status
from roadmap.core.services.sync.sync_state_manager import SyncStateManager
from tests.fixtures.issue_factory import IssueFactory


@pytest.mark.skip(
    reason="Deprecated file-based state persistence - using DB approach instead"
)
class TestSyncStateUpdates:
    """Test that sync state is properly updated after push operations."""

    @pytest.fixture
    def temp_roadmap_dir(self):
        """Create a temporary roadmap directory."""
        with temp_dir_context() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def state_manager(self, temp_roadmap_dir):
        """Create a state manager with temp directory."""
        return SyncStateManager(temp_roadmap_dir)

    @pytest.fixture
    def sample_issue(self):
        """Create a sample issue for testing."""
        return IssueFactory.create(
            id="test-1",
            title="Test Issue",
            content="Test content",
            status=Status.TODO,
            milestone=None,
            assignee="test-user",
            labels=["test"],
        )

    def test_save_base_state_creates_state_file(
        self, state_manager, sample_issue, temp_roadmap_dir
    ):
        """Test that save_base_state creates the state file."""
        state_file = temp_roadmap_dir / ".sync-state.json"
        assert not state_file.exists()

        success = state_manager.save_base_state(sample_issue)

        assert success
        assert state_file.exists()

    def test_save_base_state_updates_existing_state(
        self, state_manager, sample_issue, temp_roadmap_dir
    ):
        """Test that save_base_state updates existing state."""
        # First save
        state_manager.save_base_state(sample_issue)

        # Create a different issue
        issue2 = IssueFactory.create(
            id="test-2",
            title="Test Issue 2",
            content="Test content 2",
            status=Status.CLOSED,
            milestone=None,
            assignee="test-user-2",
            labels=["test2"],
        )

        # Save second issue
        success = state_manager.save_base_state(issue2)
        assert success

        # Load state and verify both issues are present
        state = state_manager.load_sync_state()
        assert state is not None
        assert "test-1" in state.issues
        assert "test-2" in state.issues

    def test_save_base_state_updates_timestamp(
        self, state_manager, sample_issue, temp_roadmap_dir
    ):
        """Test that save_base_state updates the last_sync timestamp."""
        state_manager.save_base_state(sample_issue)

        state = state_manager.load_sync_state()
        assert state is not None
        assert state.last_sync is not None

    def test_save_base_state_handles_minimal_issue(
        self, state_manager, temp_roadmap_dir
    ):
        """Test that save_base_state handles issues with minimal fields."""
        issue = IssueFactory.create(
            id="test-minimal",
            title="Minimal Issue",
            status=Status.TODO,
        )

        success = state_manager.save_base_state(issue)
        assert success

        state = state_manager.load_sync_state()
        assert state is not None
        assert "test-minimal" in state.issues


@pytest.mark.skip(
    reason="Deprecated file-based state persistence - using DB approach instead"
)
class TestSyncStateAfterPush:
    """Test sync state management after push operations."""

    @pytest.fixture
    def temp_roadmap_dir(self):
        """Create a temporary roadmap directory."""
        with temp_dir_context() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def state_manager(self, temp_roadmap_dir):
        """Create a state manager with temp directory."""
        return SyncStateManager(temp_roadmap_dir)

    def test_state_persists_across_multiple_saves(
        self, state_manager, temp_roadmap_dir
    ):
        """Test that state persists and accumulates across saves."""
        issue1 = IssueFactory.create(id="1", title="Issue 1", status=Status.TODO)
        issue2 = IssueFactory.create(id="2", title="Issue 2", status=Status.CLOSED)
        issue3 = IssueFactory.create(id="3", title="Issue 3", status=Status.IN_PROGRESS)

        # Save issues sequentially (simulating multiple push operations)
        state_manager.save_base_state(issue1)
        state_manager.save_base_state(issue2)
        state_manager.save_base_state(issue3)

        # Verify all are persisted
        state = state_manager.load_sync_state()
        assert state is not None
        assert len(state.issues) == 3
        assert all(issue_id in state.issues for issue_id in ["1", "2", "3"])

    def test_state_prevents_resync_of_pushed_issues(
        self, state_manager, temp_roadmap_dir
    ):
        """Test that saved state can be used to prevent re-syncing."""
        issue = IssueFactory.create(id="test-id", title="Test", status=Status.TODO)

        # Save base state (simulating a successful push)
        state_manager.save_base_state(issue)

        # Load and verify
        state = state_manager.load_sync_state()
        assert state is not None

        # In the actual sync logic, the state would be compared to detect
        # whether the issue needs re-syncing
        assert "test-id" in state.issues
        saved_issue_state = state.issues["test-id"]
        assert saved_issue_state.id == "test-id"
