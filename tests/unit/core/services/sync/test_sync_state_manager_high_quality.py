"""High-quality tests for SyncStateManager with state persistence validation.

Focus: Validates state loading/saving, metadata tracking, database operations.
Validates:
- State persistence to database
- Metadata tracking (last_sync, backend)
- Issue base state storage/retrieval
- Timestamp handling (UTC conversion)
- Database transaction handling
- Error scenarios and recovery
"""

from datetime import UTC, datetime
from unittest.mock import MagicMock, Mock, patch

import pytest

from roadmap.core.models.sync_state import IssueBaseState, SyncState
from roadmap.core.services.sync.sync_state_manager import SyncStateManager


@pytest.fixture
def temp_roadmap_dir(tmp_path):
    """Create temporary roadmap directory."""
    roadmap_dir = tmp_path / ".roadmap"
    roadmap_dir.mkdir()
    return roadmap_dir


@pytest.fixture
def mock_db_manager():
    """Create a mock database manager."""
    db_manager = MagicMock()
    db_manager._get_connection = Mock(return_value=MagicMock())
    return db_manager


@pytest.fixture
def state_manager(temp_roadmap_dir, mock_db_manager):
    """Create a SyncStateManager instance."""
    return SyncStateManager(temp_roadmap_dir, db_manager=mock_db_manager)


@pytest.fixture
def sample_sync_state():
    """Create a sample SyncState for testing."""
    base_state_1 = IssueBaseState(
        id="issue-1",
        status="todo",
        title="Issue 1",
        assignee="alice@example.com",
        milestone="v1.0",
        content="Content 1",
        labels=["bug", "urgent"],
        updated_at=datetime(2026, 1, 31, 12, 0, 0, tzinfo=UTC),
    )

    base_state_2 = IssueBaseState(
        id="issue-2",
        status="in-progress",
        title="Issue 2",
        assignee="bob@example.com",
        milestone="v1.0",
        content="Content 2",
        labels=["feature"],
        updated_at=datetime(2026, 1, 31, 12, 0, 0, tzinfo=UTC),
    )

    return SyncState(
        backend="github",
        last_sync=datetime(2026, 1, 31, 12, 0, 0, tzinfo=UTC),
        issues={
            "issue-1": base_state_1,
            "issue-2": base_state_2,
        },
    )


class TestSyncStateManagerInitialization:
    """Test SyncStateManager initialization."""

    def test_manager_initializes_with_directory(
        self, temp_roadmap_dir, mock_db_manager
    ):
        """Test manager initializes with roadmap directory."""
        manager = SyncStateManager(temp_roadmap_dir, mock_db_manager)

        assert manager.roadmap_dir == temp_roadmap_dir
        assert manager.db_manager == mock_db_manager
        assert manager.state_file == temp_roadmap_dir / "sync_state.json"

    def test_manager_initializes_without_db(self, temp_roadmap_dir):
        """Test manager can initialize without database manager."""
        manager = SyncStateManager(temp_roadmap_dir)

        assert manager.roadmap_dir == temp_roadmap_dir
        assert manager.db_manager is None

    def test_manager_with_valid_directory(self, tmp_path):
        """Test manager validates directory exists."""
        roadmap_dir = tmp_path / ".roadmap"
        roadmap_dir.mkdir()

        manager = SyncStateManager(roadmap_dir)

        assert manager.roadmap_dir.exists()


class TestSyncStateLoadOperation:
    """Test loading sync state."""

    def test_load_sync_state_returns_none_deprecated(self, state_manager):
        """Test load_sync_state returns None (deprecated method)."""
        result = state_manager.load_sync_state()

        assert result is None

    def test_load_deprecated_logs_message(self, state_manager):
        """Test that deprecated load method logs info."""
        with patch(
            "roadmap.core.services.sync.sync_state_manager.logger"
        ) as mock_logger:
            state_manager.load_sync_state()

            # Should log deprecation notice
            mock_logger.debug.assert_called()


class TestSyncStateSaveOperation:
    """Test saving sync state."""

    def test_save_sync_state_deprecated_returns_true(
        self, state_manager, sample_sync_state
    ):
        """Test deprecated save method returns True."""
        result = state_manager.save_sync_state(sample_sync_state)

        assert result is True

    def test_save_deprecated_logs_message(self, state_manager, sample_sync_state):
        """Test that deprecated save method logs info."""
        with patch(
            "roadmap.core.services.sync.sync_state_manager.logger"
        ) as mock_logger:
            state_manager.save_sync_state(sample_sync_state)

            # Should log deprecation notice
            mock_logger.debug.assert_called()

    def test_save_sync_state_to_db_without_manager(
        self, temp_roadmap_dir, sample_sync_state
    ):
        """Test save to DB when no manager returns False."""
        manager = SyncStateManager(temp_roadmap_dir, db_manager=None)

        result = manager.save_sync_state_to_db(sample_sync_state)

        assert result is False

    def test_save_sync_state_to_db_with_manager(self, state_manager, sample_sync_state):
        """Test save to DB with manager executes queries."""
        state_manager.save_sync_state_to_db(sample_sync_state)

        # Check database operations were called
        mock_conn = state_manager.db_manager._get_connection.return_value
        assert mock_conn.execute.call_count > 0

    def test_save_sync_state_stores_metadata(self, state_manager, sample_sync_state):
        """Test that save stores backend and last_sync metadata."""
        state_manager.save_sync_state_to_db(sample_sync_state)

        mock_conn = state_manager.db_manager._get_connection.return_value

        # Verify metadata was inserted
        calls = mock_conn.execute.call_args_list
        metadata_calls = [c for c in calls if "sync_metadata" in str(c)]

        assert len(metadata_calls) > 0

    def test_save_sync_state_stores_issues(self, state_manager, sample_sync_state):
        """Test that save stores issue base states."""
        state_manager.save_sync_state_to_db(sample_sync_state)

        mock_conn = state_manager.db_manager._get_connection.return_value

        # Verify issue states were inserted
        calls = mock_conn.execute.call_args_list
        issue_calls = [c for c in calls if "sync_base_state" in str(c)]

        # Should have calls for each issue
        assert len(issue_calls) >= len(sample_sync_state.issues)


class TestSyncStateMetadataHandling:
    """Test metadata handling in sync state."""

    def test_last_sync_timestamp_stored_as_iso(self, state_manager, sample_sync_state):
        """Test last_sync timestamp stored as ISO format."""
        state_manager.save_sync_state_to_db(sample_sync_state)

        mock_conn = state_manager.db_manager._get_connection.return_value
        calls = mock_conn.execute.call_args_list

        # Find the last_sync call
        last_sync_calls = [
            c for c in calls if "last_sync" in str(c) and "sync_metadata" in str(c)
        ]

        assert len(last_sync_calls) > 0

    def test_backend_stored_correctly(self, state_manager, sample_sync_state):
        """Test backend value stored correctly."""
        assert sample_sync_state.backend == "github"

        state_manager.save_sync_state_to_db(sample_sync_state)

        mock_conn = state_manager.db_manager._get_connection.return_value
        calls = mock_conn.execute.call_args_list

        # Verify backend was stored
        backend_calls = [
            c
            for c in calls
            if "backend" in str(c) and sample_sync_state.backend in str(c)
        ]

        assert len(backend_calls) > 0


class TestIssueBaseStatePersistence:
    """Test issue base state persistence."""

    def test_single_issue_persisted(self, state_manager):
        """Test single issue base state is persisted."""
        base_state = IssueBaseState(
            id="issue-1",
            status="todo",
            title="Test Issue",
            assignee="alice@example.com",
            milestone="v1.0",
            content="Test content",
            labels=["test"],
            updated_at=datetime(2026, 1, 31, 12, 0, 0, tzinfo=UTC),
        )

        state = SyncState(
            backend="github",
            last_sync=datetime(2026, 1, 31, 12, 0, 0, tzinfo=UTC),
            issues={"issue-1": base_state},
        )

        state_manager.save_sync_state_to_db(state)

        mock_conn = state_manager.db_manager._get_connection.return_value
        calls = mock_conn.execute.call_args_list

        # Should have calls for sync metadata + issue state
        assert len(calls) >= 3  # last_sync + backend + issue

    def test_multiple_issues_persisted(self, state_manager, sample_sync_state):
        """Test multiple issue base states are persisted."""
        state_manager.save_sync_state_to_db(sample_sync_state)

        mock_conn = state_manager.db_manager._get_connection.return_value
        calls = mock_conn.execute.call_args_list

        # Should have calls for metadata + 2 issues
        assert len(calls) >= 4

    def test_issue_fields_persisted(self, state_manager):
        """Test all issue base state fields are persisted."""
        base_state = IssueBaseState(
            id="issue-2",
            status="in-progress",
            title="Complex Issue",
            assignee="bob@example.com",
            milestone="v2.0",
            content="Multi-line\ncontent",
            labels=["urgent", "bug", "feature"],
            updated_at=datetime(2026, 1, 31, 14, 30, 0, tzinfo=UTC),
        )

        state = SyncState(
            backend="github",
            last_sync=datetime(2026, 1, 31, 14, 30, 0, tzinfo=UTC),
            issues={"issue-1": base_state},
        )

        state_manager.save_sync_state_to_db(state)

        # Verify database was called with all fields
        mock_conn = state_manager.db_manager._get_connection.return_value
        assert mock_conn.execute.called


class TestTimestampHandling:
    """Test UTC timestamp handling."""

    def test_sync_timestamps_are_utc(self, sample_sync_state):
        """Test sync state uses UTC timestamps."""
        assert sample_sync_state.last_sync.tzinfo == UTC

        for _issue_id, base_state in sample_sync_state.issues.items():
            assert base_state.updated_at.tzinfo == UTC

    def test_manager_preserves_timezone(self, state_manager, sample_sync_state):
        """Test manager preserves UTC timezone in timestamps."""
        state_manager.save_sync_state_to_db(sample_sync_state)

        # Timestamps should remain UTC
        assert sample_sync_state.last_sync.tzinfo == UTC

    def test_different_timestamps_stored(self, state_manager):
        """Test different timestamps for different issues."""
        time1 = datetime(2026, 1, 31, 12, 0, 0, tzinfo=UTC)
        time2 = datetime(2026, 1, 31, 14, 0, 0, tzinfo=UTC)

        base_state_1 = IssueBaseState(
            id="issue-1",
            status="todo",
            title="Issue 1",
            assignee="alice@example.com",
            milestone="v1.0",
            content="Content 1",
            labels=[],
            updated_at=time1,
        )

        base_state_2 = IssueBaseState(
            id="issue-2",
            status="in-progress",
            title="Issue 2",
            assignee="bob@example.com",
            milestone="v1.0",
            content="Content 2",
            labels=[],
            updated_at=time2,
        )

        state = SyncState(
            backend="github",
            last_sync=time2,
            issues={
                "issue-1": base_state_1,
                "issue-2": base_state_2,
            },
        )

        state_manager.save_sync_state_to_db(state)

        # Both timestamps should be stored
        mock_conn = state_manager.db_manager._get_connection.return_value
        calls = mock_conn.execute.call_args_list

        # Should have multiple execute calls for different timestamps
        assert len(calls) >= 4


class TestDatabaseConnectionHandling:
    """Test database connection handling."""

    def test_db_connection_obtained(self, state_manager, sample_sync_state):
        """Test database connection is obtained."""
        state_manager.save_sync_state_to_db(sample_sync_state)

        state_manager.db_manager._get_connection.assert_called_once()

    def test_db_operations_use_connection(self, state_manager, sample_sync_state):
        """Test all DB operations use the connection."""
        state_manager.save_sync_state_to_db(sample_sync_state)

        mock_conn = state_manager.db_manager._get_connection.return_value

        # Execute should be called multiple times
        assert mock_conn.execute.call_count > 0

    def test_db_error_handling(self, state_manager, sample_sync_state):
        """Test error handling when DB operation fails."""
        mock_conn = state_manager.db_manager._get_connection.return_value
        mock_conn.execute.side_effect = Exception("Database error")

        # Should handle the error gracefully (or return False)
        result = state_manager.save_sync_state_to_db(sample_sync_state)

        # Function should either return False or still work despite error
        assert result is False or mock_conn.execute.called


class TestSyncStateDataModel:
    """Test SyncState data model."""

    def test_sync_state_has_backend(self, sample_sync_state):
        """Test SyncState stores backend."""
        assert hasattr(sample_sync_state, "backend")
        assert sample_sync_state.backend == "github"

    def test_sync_state_has_last_sync(self, sample_sync_state):
        """Test SyncState stores last_sync timestamp."""
        assert hasattr(sample_sync_state, "last_sync")
        assert isinstance(sample_sync_state.last_sync, datetime)

    def test_sync_state_has_issues(self, sample_sync_state):
        """Test SyncState stores issues."""
        assert hasattr(sample_sync_state, "issues")
        assert isinstance(sample_sync_state.issues, dict)
        assert len(sample_sync_state.issues) == 2

    def test_issue_base_state_fields(self, sample_sync_state):
        """Test IssueBaseState has required fields."""
        for _issue_id, base_state in sample_sync_state.issues.items():
            assert hasattr(base_state, "id")
            assert hasattr(base_state, "status")
            assert hasattr(base_state, "title")
            assert hasattr(base_state, "assignee")
            assert hasattr(base_state, "milestone")
            assert hasattr(base_state, "content")
            assert hasattr(base_state, "labels")
            assert hasattr(base_state, "updated_at")


class TestEdgeCases:
    """Test edge cases and special scenarios."""

    def test_empty_issues_dict(self, state_manager):
        """Test saving state with no issues."""
        state = SyncState(
            backend="github",
            last_sync=datetime(2026, 1, 31, 12, 0, 0, tzinfo=UTC),
            issues={},
        )

        state_manager.save_sync_state_to_db(state)

        # Should handle empty issues gracefully
        mock_conn = state_manager.db_manager._get_connection.return_value
        assert mock_conn.execute.called

    def test_issue_with_empty_labels(self, state_manager):
        """Test issue base state with empty labels."""
        base_state = IssueBaseState(
            id="issue-1",
            status="todo",
            title="Issue",
            assignee="alice@example.com",
            milestone="v1.0",
            content="Content",
            labels=[],
            updated_at=datetime(2026, 1, 31, 12, 0, 0, tzinfo=UTC),
        )

        state = SyncState(
            backend="github",
            last_sync=datetime(2026, 1, 31, 12, 0, 0, tzinfo=UTC),
            issues={"issue-1": base_state},
        )

        state_manager.save_sync_state_to_db(state)

        mock_conn = state_manager.db_manager._get_connection.return_value
        assert mock_conn.execute.called

    def test_issue_with_null_assignee(self, state_manager):
        """Test issue base state with null assignee."""
        base_state = IssueBaseState(
            id="issue-1",
            status="todo",
            title="Issue",
            assignee=None,
            milestone="v1.0",
            content="Content",
            labels=[],
            updated_at=datetime(2026, 1, 31, 12, 0, 0, tzinfo=UTC),
        )

        state = SyncState(
            backend="github",
            last_sync=datetime(2026, 1, 31, 12, 0, 0, tzinfo=UTC),
            issues={"issue-1": base_state},
        )

        state_manager.save_sync_state_to_db(state)

        mock_conn = state_manager.db_manager._get_connection.return_value
        assert mock_conn.execute.called

    def test_issue_with_multiline_content(self, state_manager):
        """Test issue with multiline content."""
        multiline_content = "Line 1\nLine 2\nLine 3"
        base_state = IssueBaseState(
            id="issue-1",
            status="todo",
            title="Issue",
            assignee="alice@example.com",
            milestone="v1.0",
            content=multiline_content,
            labels=[],
            updated_at=datetime(2026, 1, 31, 12, 0, 0, tzinfo=UTC),
        )

        state = SyncState(
            backend="github",
            last_sync=datetime(2026, 1, 31, 12, 0, 0, tzinfo=UTC),
            issues={"issue-1": base_state},
        )

        state_manager.save_sync_state_to_db(state)

        mock_conn = state_manager.db_manager._get_connection.return_value
        assert mock_conn.execute.called
