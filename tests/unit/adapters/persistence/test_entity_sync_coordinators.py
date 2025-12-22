"""Tests for entity sync coordinators."""

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from roadmap.adapters.persistence.entity_sync_coordinators import (
    EntitySyncCoordinator,
    IssueSyncCoordinator,
)


class TestEntitySyncCoordinator:
    """Test EntitySyncCoordinator base class."""

    @pytest.fixture
    def mock_connection(self):
        """Create mock database connection."""
        return MagicMock()

    @pytest.fixture
    def mock_transaction(self):
        """Create mock transaction context manager."""
        ctx = MagicMock()
        ctx.__enter__ = MagicMock(return_value=MagicMock())
        ctx.__exit__ = MagicMock(return_value=None)
        return ctx

    @pytest.fixture
    def coordinator(self, mock_connection, mock_transaction):
        """Create coordinator with mocks."""

        def get_conn():
            return mock_connection

        def trans_ctx():
            return mock_transaction

        return EntitySyncCoordinator(get_conn, trans_ctx)

    def test_init(self, mock_connection, mock_transaction):
        """Test coordinator initialization."""

        def get_conn():
            return mock_connection

        def trans_ctx():
            return mock_transaction

        coordinator = EntitySyncCoordinator(get_conn, trans_ctx)
        assert coordinator._get_connection == get_conn
        assert coordinator._transaction == trans_ctx
        assert coordinator._parser is not None

    def test_get_default_project_id_success(self, coordinator, mock_transaction):
        """Test getting default project ID successfully."""
        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchone.return_value = ("proj-123",)
        mock_transaction.__enter__.return_value = mock_conn

        result = coordinator._get_default_project_id()
        assert result == "proj-123"

    def test_get_default_project_id_no_projects(self, coordinator, mock_transaction):
        """Test getting default project ID when none exist."""
        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchone.return_value = None
        mock_transaction.__enter__.return_value = mock_conn

        result = coordinator._get_default_project_id()
        assert result is None

    def test_get_default_project_id_exception(self, coordinator, mock_transaction):
        """Test getting default project ID handles exceptions."""
        mock_conn = MagicMock()
        mock_conn.execute.side_effect = Exception("DB Error")
        mock_transaction.__enter__.return_value = mock_conn

        result = coordinator._get_default_project_id()
        assert result is None

    def test_get_milestone_id_by_name_success(self, coordinator, mock_transaction):
        """Test getting milestone ID by name."""
        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchone.return_value = ("m-456",)
        mock_transaction.__enter__.return_value = mock_conn

        result = coordinator._get_milestone_id_by_name("Q1 2024")
        assert result == "m-456"

    def test_get_milestone_id_by_name_not_found(self, coordinator, mock_transaction):
        """Test milestone not found returns None."""
        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchone.return_value = None
        mock_transaction.__enter__.return_value = mock_conn

        result = coordinator._get_milestone_id_by_name("Nonexistent")
        assert result is None

    def test_get_milestone_id_by_name_exception(self, coordinator, mock_transaction):
        """Test exception handling in milestone lookup."""
        mock_conn = MagicMock()
        mock_conn.execute.side_effect = Exception("DB Error")
        mock_transaction.__enter__.return_value = mock_conn

        result = coordinator._get_milestone_id_by_name("Q1 2024")
        assert result is None

    def test_normalize_date_none(self, coordinator):
        """Test normalizing None date."""
        result = coordinator._normalize_date(None)
        assert result is None

    def test_normalize_date_empty_string(self, coordinator):
        """Test normalizing empty string date."""
        result = coordinator._normalize_date("")
        assert result is None

    def test_normalize_date_iso_string(self, coordinator):
        """Test normalizing ISO format date string."""
        result = coordinator._normalize_date("2024-01-15")
        assert result is not None

    def test_normalize_date_invalid_string(self, coordinator):
        """Test invalid date string returns None."""
        result = coordinator._normalize_date("invalid-date")
        assert result is None

    def test_normalize_date_already_date(self, coordinator):
        """Test date object is returned as-is."""
        date_obj = datetime(2024, 1, 15).date()
        result = coordinator._normalize_date(date_obj)
        assert result == date_obj

    def test_extract_metadata_with_extra_fields(self, coordinator):
        """Test extracting metadata from extra fields."""
        data = {
            "id": "123",
            "title": "Test",
            "custom_field": "value",
            "extra": "data",
        }
        result = coordinator._extract_metadata(data, ["id", "title"])
        assert result is not None
        import json

        parsed = json.loads(result)
        assert "custom_field" in parsed
        assert "extra" in parsed
        assert "id" not in parsed

    def test_extract_metadata_no_extra_fields(self, coordinator):
        """Test extracting metadata when no extra fields."""
        data = {"id": "123", "title": "Test"}
        result = coordinator._extract_metadata(data, ["id", "title"])
        assert result is None

    def test_extract_metadata_empty_data(self, coordinator):
        """Test extracting metadata from empty dict."""
        result = coordinator._extract_metadata({}, [])
        assert result is None

    def test_update_sync_status_success(self, coordinator, mock_transaction):
        """Test updating sync status for a file."""
        mock_conn = MagicMock()
        mock_transaction.__enter__.return_value = mock_conn

        with patch.object(coordinator._parser, "extract_file_metadata") as mock_extract:
            mock_extract.return_value = {
                "hash": "abc123",
                "size": 1024,
                "modified_time": "2024-01-15T10:00:00",
            }

            coordinator._update_sync_status(Path("test.md"))

            mock_conn.execute.assert_called_once()
            call_args = mock_conn.execute.call_args
            assert "file_sync_state" in call_args[0][0]

    def test_update_sync_status_no_metadata(self, coordinator):
        """Test updating sync status with no metadata."""
        with patch.object(
            coordinator._parser, "extract_file_metadata", return_value=None
        ):
            # Should not raise, just return silently
            coordinator._update_sync_status(Path("test.md"))


class TestIssueSyncCoordinator:
    """Test IssueSyncCoordinator."""

    @pytest.fixture
    def mock_transaction(self):
        """Create mock transaction context manager."""
        ctx = MagicMock()
        ctx.__enter__ = MagicMock(return_value=MagicMock())
        ctx.__exit__ = MagicMock(return_value=None)
        return ctx

    @pytest.fixture
    def coordinator(self, mock_transaction):
        """Create issue coordinator with mocks."""

        def trans_ctx():
            return mock_transaction

        return IssueSyncCoordinator(lambda: MagicMock(), trans_ctx)

    def test_extract_issue_id_from_data(self, coordinator):
        """Test extracting issue ID from data."""
        issue_data = {"id": "ISSUE-123"}
        result = coordinator._extract_issue_id(issue_data, Path("file.md"))
        assert result == "ISSUE-123"

    def test_extract_issue_id_from_filename_issue_prefix(self, coordinator):
        """Test extracting issue ID from filename with 'issue-' prefix."""
        issue_data = {}
        result = coordinator._extract_issue_id(issue_data, Path("issue-456.md"))
        assert result == "456"
        assert issue_data["id"] == "456"

    def test_extract_issue_id_from_filename_stem(self, coordinator):
        """Test extracting issue ID from filename stem."""
        issue_data = {}
        result = coordinator._extract_issue_id(issue_data, Path("ISSUE-789.md"))
        assert result == "ISSUE-789"
        assert issue_data["id"] == "ISSUE-789"

    def test_handle_project_id_from_data(self, coordinator):
        """Test getting project ID from issue data."""
        issue_data = {"project_id": "proj-123"}
        result = coordinator._handle_project_id(issue_data, "issue-1")
        assert result == "proj-123"

    def test_handle_project_id_default(self, coordinator, mock_transaction):
        """Test getting default project ID when not in data."""
        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchone.return_value = ("default-proj",)
        mock_transaction.__enter__.return_value = mock_conn

        issue_data = {}
        result = coordinator._handle_project_id(issue_data, "issue-1")
        assert result == "default-proj"
        assert issue_data["project_id"] == "default-proj"

    def test_handle_project_id_none(self, coordinator, mock_transaction):
        """Test when no project ID is available."""
        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchone.return_value = None
        mock_transaction.__enter__.return_value = mock_conn

        issue_data = {}
        result = coordinator._handle_project_id(issue_data, "issue-1")
        assert result is None

    def test_handle_milestone_field_with_id(self, coordinator):
        """Test handling milestone field when ID is provided."""
        issue_data = {"milestone_id": "m-123"}
        coordinator._handle_milestone_field(issue_data)
        assert issue_data["milestone_id"] == "m-123"

    def test_handle_milestone_field_with_name(self, coordinator, mock_transaction):
        """Test handling milestone field when name is provided."""
        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchone.return_value = ("m-456",)
        mock_transaction.__enter__.return_value = mock_conn

        issue_data = {"milestone": "Q1 2024"}
        coordinator._handle_milestone_field(issue_data)
        assert issue_data["milestone_id"] == "m-456"

    def test_normalize_issue_fields_defaults(self, coordinator):
        """Test normalizing issue fields sets defaults."""
        issue_data = {"status": "closed"}
        coordinator._normalize_issue_fields(issue_data)
        assert issue_data["title"] == "Untitled"
        assert issue_data["priority"] == "medium"
        assert issue_data["issue_type"] == "task"

    def test_normalize_issue_fields_keeps_values(self, coordinator):
        """Test normalizing issue fields preserves existing values."""
        issue_data = {
            "title": "My Issue",
            "priority": "high",
            "type": "bug",
        }
        coordinator._normalize_issue_fields(issue_data)
        assert issue_data["title"] == "My Issue"
        assert issue_data["priority"] == "high"
        assert issue_data["issue_type"] == "bug"

    def test_normalize_issue_fields_converts_type(self, coordinator):
        """Test that 'type' field is converted to 'issue_type'."""
        issue_data = {"type": "feature"}
        coordinator._normalize_issue_fields(issue_data)
        assert "issue_type" in issue_data
        assert issue_data["issue_type"] == "feature"
        assert "type" not in issue_data

    def test_sync_issue_file_file_not_found(self, coordinator):
        """Test sync fails when file doesn't exist."""
        result = coordinator.sync_issue_file(Path("nonexistent.md"))
        assert result is False

    def test_sync_issue_file_no_yaml(self, coordinator, tmp_path):
        """Test sync fails when no YAML frontmatter."""
        issue_file = tmp_path / "issue.md"
        issue_file.write_text("No YAML here")

        with patch.object(
            coordinator._parser, "parse_yaml_frontmatter", return_value=None
        ):
            result = coordinator.sync_issue_file(issue_file)
            assert result is False
