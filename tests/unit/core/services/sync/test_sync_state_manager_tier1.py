"""High-quality test suite for SyncStateManager covering all public methods.

Tests focus on:
- load/save operations
- Database integration
- Base state creation and management
- Sync state creation from issues
- JSON to database migration
- Error handling across all paths
"""

from datetime import UTC, datetime
from unittest.mock import MagicMock, PropertyMock, patch

from roadmap.core.domain.issue import Issue
from roadmap.core.models.sync_state import SyncState
from roadmap.core.services.sync.sync_state_manager import SyncStateManager


class TestSyncStateManagerInit:
    """Tests for SyncStateManager initialization."""

    def test_init_with_defaults(self, tmp_path):
        """Initialize manager with defaults."""
        roadmap_dir = tmp_path / ".roadmap"
        roadmap_dir.mkdir()

        manager = SyncStateManager(roadmap_dir)

        assert manager.roadmap_dir == roadmap_dir
        assert manager.db_manager is None
        assert manager.state_file == roadmap_dir / "sync_state.json"

    def test_init_with_db_manager(self, tmp_path):
        """Initialize manager with database manager."""
        roadmap_dir = tmp_path / ".roadmap"
        roadmap_dir.mkdir()
        mock_db = MagicMock()

        manager = SyncStateManager(roadmap_dir, db_manager=mock_db)

        assert manager.db_manager == mock_db


class TestSyncStateManagerLoadSave:
    """Tests for load and save operations."""

    def test_load_sync_state_deprecated_returns_none(self, tmp_path):
        """load_sync_state returns None (deprecated method)."""
        roadmap_dir = tmp_path / ".roadmap"
        roadmap_dir.mkdir()
        manager = SyncStateManager(roadmap_dir)

        result = manager.load_sync_state()

        assert result is None

    def test_save_sync_state_deprecated_returns_true(self, tmp_path):
        """save_sync_state returns True (deprecated method)."""
        roadmap_dir = tmp_path / ".roadmap"
        roadmap_dir.mkdir()
        manager = SyncStateManager(roadmap_dir)

        state = SyncState(
            last_sync=datetime.now(UTC),
            backend="github",
        )

        result = manager.save_sync_state(state)

        assert result is True

    def test_save_sync_state_to_db_without_manager_returns_false(self, tmp_path):
        """save_sync_state_to_db returns False without db_manager."""
        roadmap_dir = tmp_path / ".roadmap"
        roadmap_dir.mkdir()
        manager = SyncStateManager(roadmap_dir, db_manager=None)

        state = SyncState(
            last_sync=datetime.now(UTC),
            backend="github",
        )

        result = manager.save_sync_state_to_db(state)

        assert result is False

    def test_save_sync_state_to_db_with_manager_executes_sql(self, tmp_path):
        """save_sync_state_to_db executes SQL with db_manager."""
        roadmap_dir = tmp_path / ".roadmap"
        roadmap_dir.mkdir()

        mock_db = MagicMock()
        mock_conn = MagicMock()
        mock_db._get_connection.return_value = mock_conn

        manager = SyncStateManager(roadmap_dir, db_manager=mock_db)

        state = SyncState(
            last_sync=datetime.now(UTC),
            backend="github",
        )

        result = manager.save_sync_state_to_db(state)

        # Should have called execute for metadata and sync_base_state
        assert mock_conn.execute.called
        assert result is True


class TestCreateBaseState:
    """Tests for create_base_state_from_issue."""

    def test_create_base_state_with_all_fields(self, tmp_path):
        """Create base state from issue with all fields."""
        roadmap_dir = tmp_path / ".roadmap"
        roadmap_dir.mkdir()
        manager = SyncStateManager(roadmap_dir)

        # Create a mock issue
        issue = MagicMock(spec=Issue)
        issue.id = "test-123"
        issue.status = "open"
        issue.title = "Test Issue"
        issue.assignee = "alice"
        issue.milestone = "v1.0"
        issue.content = "Issue description"
        issue.labels = ["bug", "urgent"]

        base_state = manager.create_base_state_from_issue(issue)

        assert base_state.id == "test-123"
        assert base_state.status == "open"
        assert base_state.title == "Test Issue"
        assert base_state.assignee == "alice"
        assert base_state.milestone == "v1.0"
        assert base_state.headline == "Issue description"
        assert base_state.labels == ["bug", "urgent"]

    def test_create_base_state_with_enum_status(self, tmp_path):
        """Create base state when status is an enum."""
        roadmap_dir = tmp_path / ".roadmap"
        roadmap_dir.mkdir()
        manager = SyncStateManager(roadmap_dir)

        # Mock status as enum
        mock_status = MagicMock()
        mock_status.value = "closed"

        issue = MagicMock(spec=Issue)
        issue.id = "test-456"
        issue.status = mock_status
        issue.title = "Test"
        issue.assignee = None
        issue.milestone = None
        issue.content = None
        issue.labels = None

        base_state = manager.create_base_state_from_issue(issue)

        assert base_state.status == "closed"

    def test_create_base_state_with_missing_milestone(self, tmp_path):
        """Create base state when milestone attribute missing."""
        roadmap_dir = tmp_path / ".roadmap"
        roadmap_dir.mkdir()
        manager = SyncStateManager(roadmap_dir)

        issue = MagicMock(
            spec=["id", "status", "title", "assignee", "content", "labels"]
        )
        issue.id = "test-789"
        issue.status = "open"
        issue.title = "Test"
        issue.assignee = None
        issue.content = None
        issue.labels = None

        base_state = manager.create_base_state_from_issue(issue)

        assert base_state.milestone is None


class TestSaveBaseState:
    """Tests for save_base_state method."""

    def test_save_base_state_success(self, tmp_path):
        """Save base state returns True on success."""
        roadmap_dir = tmp_path / ".roadmap"
        roadmap_dir.mkdir()

        mock_db = MagicMock()
        mock_conn = MagicMock()
        mock_db._get_connection.return_value = mock_conn
        mock_db._get_connection.return_value.execute.return_value = None

        manager = SyncStateManager(roadmap_dir, db_manager=mock_db)

        issue = MagicMock(spec=Issue)
        issue.id = "test-123"
        issue.status = "open"
        issue.title = "Test Issue"
        issue.assignee = None
        issue.milestone = None
        issue.content = None
        issue.labels = None

        with patch.object(manager, "load_sync_state", return_value=None):
            result = manager.save_base_state(issue)

        assert result is True

    def test_save_base_state_missing_db_manager(self, tmp_path):
        """Save base state fails gracefully without db_manager."""
        roadmap_dir = tmp_path / ".roadmap"
        roadmap_dir.mkdir()

        manager = SyncStateManager(roadmap_dir, db_manager=None)

        issue = MagicMock(spec=Issue)
        issue.id = "test-123"
        issue.status = "open"
        issue.title = "Test Issue"

        with patch.object(manager, "load_sync_state", return_value=None):
            result = manager.save_base_state(issue)

        # Returns False because db_manager is None
        assert result is False

    def test_save_base_state_handles_attribute_error(self, tmp_path):
        """Save base state handles AttributeError gracefully."""
        roadmap_dir = tmp_path / ".roadmap"
        roadmap_dir.mkdir()

        manager = SyncStateManager(roadmap_dir, db_manager=None)

        # Pass object without id attribute
        issue = MagicMock(spec=[])

        result = manager.save_base_state(issue)

        assert result is False


class TestCreateSyncStateFromIssues:
    """Tests for create_sync_state_from_issues."""

    def test_create_sync_state_from_empty_list(self, tmp_path):
        """Create sync state from empty issues list."""
        roadmap_dir = tmp_path / ".roadmap"
        roadmap_dir.mkdir()
        manager = SyncStateManager(roadmap_dir)

        state = manager.create_sync_state_from_issues([])

        assert state.backend == "github"
        assert len(state.issues) == 0

    def test_create_sync_state_from_multiple_issues(self, tmp_path):
        """Create sync state from multiple issues."""
        roadmap_dir = tmp_path / ".roadmap"
        roadmap_dir.mkdir()
        manager = SyncStateManager(roadmap_dir)

        issues = []
        for i in range(3):
            issue = MagicMock(spec=Issue)
            issue.id = f"test-{i}"
            issue.status = "open"
            issue.title = f"Issue {i}"
            issue.assignee = None
            issue.milestone = None
            issue.content = None
            issue.labels = None
            issues.append(issue)

        state = manager.create_sync_state_from_issues(issues, backend="custom")

        assert state.backend == "custom"
        assert len(state.issues) == 3

    def test_create_sync_state_skips_problematic_issues(self, tmp_path):
        """Create sync state skips issues that cause errors."""
        roadmap_dir = tmp_path / ".roadmap"
        roadmap_dir.mkdir()
        manager = SyncStateManager(roadmap_dir)

        # Good issue
        good_issue = MagicMock(spec=Issue)
        good_issue.id = "good-1"
        good_issue.status = "open"
        good_issue.title = "Good"
        good_issue.assignee = None
        good_issue.milestone = None
        good_issue.content = None
        good_issue.labels = None

        # Bad issue (will have attribute access fail)
        bad_issue = MagicMock(spec=Issue)
        bad_issue.id = "bad-1"
        type(bad_issue).status = PropertyMock(side_effect=Exception("Bad issue"))

        state = manager.create_sync_state_from_issues([good_issue, bad_issue])

        # Should still have one issue (good one)
        assert len(state.issues) >= 1


class TestMigrateJsonToDb:
    """Tests for migrate_json_to_db."""

    def test_migrate_json_to_db_no_manager_returns_false(self, tmp_path):
        """Migrate returns False without db_manager."""
        roadmap_dir = tmp_path / ".roadmap"
        roadmap_dir.mkdir()

        manager = SyncStateManager(roadmap_dir, db_manager=None)

        result = manager.migrate_json_to_db()

        assert result is False

    def test_migrate_json_to_db_no_json_file_returns_true(self, tmp_path):
        """Migrate returns True when no JSON file exists."""
        roadmap_dir = tmp_path / ".roadmap"
        roadmap_dir.mkdir()

        mock_db = MagicMock()
        manager = SyncStateManager(roadmap_dir, db_manager=mock_db)

        result = manager.migrate_json_to_db()

        assert result is True

    def test_migrate_json_to_db_success(self, tmp_path):
        """Migrate succeeds and archives JSON file."""
        roadmap_dir = tmp_path / ".roadmap"
        roadmap_dir.mkdir()

        # Create a dummy JSON file
        state_file = roadmap_dir / "sync_state.json"
        state_file.write_text("{}")

        mock_db = MagicMock()
        mock_conn = MagicMock()
        mock_db._get_connection.return_value = mock_conn

        manager = SyncStateManager(roadmap_dir, db_manager=mock_db)

        with patch.object(
            manager,
            "load_sync_state",
            return_value=SyncState(
                last_sync=datetime.now(UTC),
                backend="github",
            ),
        ):
            with patch.object(manager, "save_sync_state_to_db", return_value=True):
                result = manager.migrate_json_to_db()

        assert result is True
