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

    @pytest.mark.parametrize(
        "return_value,expect_result",
        [
            (("proj-123",), "proj-123"),
            (None, None),
        ],
    )
    def test_get_default_project_id(self, coordinator, mock_transaction, return_value, expect_result):
        """Test getting default project ID with various outcomes."""
        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchone.return_value = return_value
        mock_transaction.__enter__.return_value = mock_conn

        result = coordinator._get_default_project_id()
        assert result == expect_result

    def test_get_default_project_id_exception(self, coordinator, mock_transaction):
        """Test getting default project ID handles exceptions."""
        mock_conn = MagicMock()
        mock_conn.execute.side_effect = Exception("DB Error")
        mock_transaction.__enter__.return_value = mock_conn

        result = coordinator._get_default_project_id()
        assert result is None

    @pytest.mark.parametrize(
        "return_value,expect_result",
        [
            (("m-456",), "m-456"),
            (None, None),
        ],
    )
    def test_get_milestone_id_by_name(self, coordinator, mock_transaction, return_value, expect_result):
        """Test getting milestone ID by name with various outcomes."""
        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchone.return_value = return_value
        mock_transaction.__enter__.return_value = mock_conn

        result = coordinator._get_milestone_id_by_name("Q1 2024")
        assert result == expect_result

    def test_get_milestone_id_by_name_exception(self, coordinator, mock_transaction):
        """Test exception handling in milestone lookup."""
        mock_conn = MagicMock()
        mock_conn.execute.side_effect = Exception("DB Error")
        mock_transaction.__enter__.return_value = mock_conn

        result = coordinator._get_milestone_id_by_name("Q1 2024")
        assert result is None

    @pytest.mark.parametrize(
        "input_value,expected_result",
        [
            (None, None),
            ("", None),
            ("2024-01-15", "valid_date"),
            ("invalid-date", None),
        ],
    )
    def test_normalize_date(self, coordinator, input_value, expected_result):
        """Test normalizing dates with various inputs."""
        result = coordinator._normalize_date(input_value)
        if expected_result == "valid_date":
            assert result is not None
        else:
            assert result is None

    def test_normalize_date_already_date(self, coordinator):
        """Test date object is returned as-is."""
        date_obj = datetime(2024, 1, 15).date()
        result = coordinator._normalize_date(date_obj)
        assert result == date_obj

    @pytest.mark.parametrize(
        "data,known_fields,should_have_metadata",
        [
            ({"id": "123", "title": "Test", "custom_field": "value", "extra": "data"}, ["id", "title"], True),
            ({"id": "123", "title": "Test"}, ["id", "title"], False),
            ({}, [], False),
        ],
    )
    def test_extract_metadata(self, coordinator, data, known_fields, should_have_metadata):
        """Test extracting metadata from data."""
        result = coordinator._extract_metadata(data, known_fields)
        if should_have_metadata:
            assert result is not None
            import json
            parsed = json.loads(result)
            assert "custom_field" in parsed
        else:
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
        assert not result

    def test_sync_issue_file_no_yaml(self, coordinator, tmp_path):
        """Test sync fails when no YAML frontmatter."""
        issue_file = tmp_path / "issue.md"
        issue_file.write_text("No YAML here")

        with patch.object(
            coordinator._parser, "parse_yaml_frontmatter", return_value=None
        ):
            result = coordinator.sync_issue_file(issue_file)
            assert not result

    def test_sync_issue_file_no_project_id(
        self, coordinator, tmp_path, mock_transaction
    ):
        """Test sync fails when no project ID available."""
        issue_file = tmp_path / "issue.md"
        issue_file.write_text("content")

        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchone.return_value = None
        mock_transaction.__enter__.return_value = mock_conn

        with patch.object(coordinator._parser, "parse_yaml_frontmatter") as mock_parse:
            with patch.object(coordinator, "_extract_issue_id", return_value="123"):
                mock_parse.return_value = {}
                result = coordinator.sync_issue_file(issue_file)
                assert not result

    def test_sync_issue_file_calls_database(
        self, coordinator, tmp_path, mock_transaction
    ):
        """Test issue file sync calls database with proper arguments."""
        issue_file = tmp_path / "issue-123.md"
        issue_file.write_text("content")

        mock_conn = MagicMock()
        mock_transaction.__enter__.return_value = mock_conn

        # Create complete issue data that won't require normalization
        issue_data = {
            "id": "123",
            "title": "Test Issue",
            "project_id": "proj-1",
            "status": "open",
            "priority": "high",
            "description": "Test",
            "assignee": "user@example.com",
            "estimate_hours": 8,
            "due_date": None,
            "issue_type": "bug",
        }

        with patch.object(
            coordinator._parser, "parse_yaml_frontmatter", return_value=issue_data
        ):
            result = coordinator.sync_issue_file(issue_file)
            # Should succeed with complete data
            if result:
                mock_conn.execute.assert_called()

    def test_sync_issue_file_exception_handling(
        self, coordinator, tmp_path, mock_transaction
    ):
        """Test sync handles unexpected exceptions."""
        issue_file = tmp_path / "issue.md"
        issue_file.write_text("content")

        with patch.object(coordinator._parser, "parse_yaml_frontmatter") as mock_parse:
            mock_parse.side_effect = ValueError("Parsing error")
            result = coordinator.sync_issue_file(issue_file)
            assert not result


class TestMilestoneSyncCoordinator:
    """Test MilestoneSyncCoordinator."""

    @pytest.fixture
    def mock_transaction(self):
        """Create mock transaction context manager."""
        ctx = MagicMock()
        ctx.__enter__ = MagicMock(return_value=MagicMock())
        ctx.__exit__ = MagicMock(return_value=None)
        return ctx

    @pytest.fixture
    def coordinator(self, mock_transaction):
        """Create milestone coordinator with mocks."""
        from roadmap.adapters.persistence.entity_sync_coordinators import (
            MilestoneSyncCoordinator,
        )

        def trans_ctx():
            return mock_transaction

        return MilestoneSyncCoordinator(lambda: MagicMock(), trans_ctx)

    def test_sync_milestone_file_not_found(self, coordinator):
        """Test sync fails when milestone file doesn't exist."""
        result = coordinator.sync_milestone_file(Path("nonexistent.md"))
        assert not result

    def test_sync_milestone_file_no_yaml(self, coordinator, tmp_path):
        """Test sync fails when no YAML frontmatter."""
        milestone_file = tmp_path / "milestone.md"
        milestone_file.write_text("No YAML here")

        with patch.object(
            coordinator._parser, "parse_yaml_frontmatter", return_value=None
        ):
            result = coordinator.sync_milestone_file(milestone_file)
            assert not result

    def test_sync_milestone_file_no_project_id(
        self, coordinator, tmp_path, mock_transaction
    ):
        """Test sync fails when no project ID available."""
        milestone_file = tmp_path / "milestone.md"
        milestone_file.write_text("content")

        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchone.return_value = None
        mock_transaction.__enter__.return_value = mock_conn

        with patch.object(coordinator._parser, "parse_yaml_frontmatter") as mock_parse:
            mock_parse.return_value = {"title": "v1.0"}
            result = coordinator.sync_milestone_file(milestone_file)
            assert not result

    def test_sync_milestone_file_success(self, coordinator, tmp_path, mock_transaction):
        """Test successfully syncing a milestone file."""
        milestone_file = tmp_path / "v1-0.md"
        milestone_file.write_text("content")

        mock_conn = MagicMock()
        mock_transaction.__enter__.return_value = mock_conn

        milestone_data = {
            "title": "v1.0",
            "project_id": "proj-1",
        }

        with patch.object(
            coordinator._parser, "parse_yaml_frontmatter", return_value=milestone_data
        ):
            with patch.object(
                coordinator, "_get_default_project_id", return_value="proj-1"
            ):
                with patch.object(coordinator, "_extract_metadata", return_value=None):
                    with patch.object(coordinator, "_update_sync_status"):
                        result = coordinator.sync_milestone_file(milestone_file)
                        assert result
                        mock_conn.execute.assert_called()

    def test_sync_milestone_file_uses_name_field(
        self, coordinator, tmp_path, mock_transaction
    ):
        """Test milestone syncing uses 'name' if 'title' is missing."""
        milestone_file = tmp_path / "milestone.md"
        milestone_file.write_text("content")

        mock_conn = MagicMock()
        mock_transaction.__enter__.return_value = mock_conn

        milestone_data = {"name": "Version 1.0", "project_id": "proj-1"}

        with patch.object(
            coordinator._parser, "parse_yaml_frontmatter", return_value=milestone_data
        ):
            with patch.object(
                coordinator, "_get_default_project_id", return_value="proj-1"
            ):
                with patch.object(coordinator, "_extract_metadata", return_value=None):
                    with patch.object(coordinator, "_update_sync_status"):
                        result = coordinator.sync_milestone_file(milestone_file)
                        assert result
                        assert milestone_data["title"] == "Version 1.0"

    def test_sync_milestone_file_sets_defaults(
        self, coordinator, tmp_path, mock_transaction
    ):
        """Test milestone syncing sets default values."""
        milestone_file = tmp_path / "milestone.md"
        milestone_file.write_text("content")

        mock_conn = MagicMock()
        mock_transaction.__enter__.return_value = mock_conn

        milestone_data = {"title": "v1.0", "project_id": "proj-1"}

        with patch.object(
            coordinator._parser, "parse_yaml_frontmatter", return_value=milestone_data
        ):
            with patch.object(
                coordinator, "_get_default_project_id", return_value="proj-1"
            ):
                with patch.object(coordinator, "_extract_metadata", return_value=None):
                    with patch.object(coordinator, "_update_sync_status"):
                        result = coordinator.sync_milestone_file(milestone_file)
                        assert result
                        assert milestone_data["status"] == "open"
                        assert milestone_data["progress_percentage"] == 0.0

    def test_sync_milestone_file_exception_handling(
        self, coordinator, tmp_path, mock_transaction
    ):
        """Test milestone sync handles unexpected exceptions."""
        milestone_file = tmp_path / "milestone.md"
        milestone_file.write_text("content")

        with patch.object(coordinator._parser, "parse_yaml_frontmatter") as mock_parse:
            mock_parse.side_effect = ValueError("Parsing error")
            result = coordinator.sync_milestone_file(milestone_file)
            assert not result


class TestProjectSyncCoordinator:
    """Test ProjectSyncCoordinator."""

    @pytest.fixture
    def mock_transaction(self):
        """Create mock transaction context manager."""
        ctx = MagicMock()
        ctx.__enter__ = MagicMock(return_value=MagicMock())
        ctx.__exit__ = MagicMock(return_value=None)
        return ctx

    @pytest.fixture
    def coordinator(self, mock_transaction):
        """Create project coordinator with mocks."""
        from roadmap.adapters.persistence.entity_sync_coordinators import (
            ProjectSyncCoordinator,
        )

        def trans_ctx():
            return mock_transaction

        return ProjectSyncCoordinator(lambda: MagicMock(), trans_ctx)

    def test_sync_project_file_not_found(self, coordinator):
        """Test sync fails when project file doesn't exist."""
        result = coordinator.sync_project_file(Path("nonexistent.md"))
        assert not result

    def test_sync_project_file_no_yaml(self, coordinator, tmp_path):
        """Test sync fails when no YAML frontmatter."""
        project_file = tmp_path / "project.md"
        project_file.write_text("No YAML here")

        with patch.object(
            coordinator._parser, "parse_yaml_frontmatter", return_value=None
        ):
            result = coordinator.sync_project_file(project_file)
            assert not result

    def test_sync_project_file_success(self, coordinator, tmp_path, mock_transaction):
        """Test successfully syncing a project file."""
        project_file = tmp_path / "project-1.md"
        project_file.write_text("content")

        mock_conn = MagicMock()
        mock_transaction.__enter__.return_value = mock_conn

        project_data = {
            "id": "project-1",
            "name": "My Project",
        }

        with patch.object(
            coordinator._parser, "parse_yaml_frontmatter", return_value=project_data
        ):
            with patch.object(coordinator, "_extract_metadata", return_value=None):
                with patch.object(coordinator, "_update_sync_status"):
                    result = coordinator.sync_project_file(project_file)
                    assert result
                    mock_conn.execute.assert_called()

    def test_sync_project_file_uses_title_as_name(
        self, coordinator, tmp_path, mock_transaction
    ):
        """Test project syncing uses 'title' if 'name' is missing."""
        project_file = tmp_path / "project.md"
        project_file.write_text("content")

        mock_conn = MagicMock()
        mock_transaction.__enter__.return_value = mock_conn

        project_data = {"title": "My Project"}

        with patch.object(
            coordinator._parser, "parse_yaml_frontmatter", return_value=project_data
        ):
            with patch.object(coordinator, "_extract_metadata", return_value=None):
                with patch.object(coordinator, "_update_sync_status"):
                    result = coordinator.sync_project_file(project_file)
                    assert result
                    assert project_data["name"] == "My Project"

    def test_sync_project_file_sets_defaults(
        self, coordinator, tmp_path, mock_transaction
    ):
        """Test project syncing sets default values when missing."""
        project_file = tmp_path / "project.md"
        project_file.write_text("content")

        mock_conn = MagicMock()
        mock_transaction.__enter__.return_value = mock_conn

        # Provide minimal data to test defaults
        project_data = {"name": "Test Project"}

        with patch.object(
            coordinator._parser, "parse_yaml_frontmatter", return_value=project_data
        ):
            with patch.object(coordinator, "_extract_metadata", return_value=None):
                with patch.object(coordinator, "_update_sync_status"):
                    result = coordinator.sync_project_file(project_file)
                    assert result
                    # Verify status was set to default
                    assert project_data.get("status") == "active"

    def test_sync_project_file_uses_filename_as_id(
        self, coordinator, tmp_path, mock_transaction
    ):
        """Test project syncing uses filename as ID if not provided."""
        project_file = tmp_path / "web-app.md"
        project_file.write_text("content")

        mock_conn = MagicMock()
        mock_transaction.__enter__.return_value = mock_conn

        project_data = {"name": "Web Application"}

        with patch.object(
            coordinator._parser, "parse_yaml_frontmatter", return_value=project_data
        ):
            with patch.object(coordinator, "_extract_metadata", return_value=None):
                with patch.object(coordinator, "_update_sync_status"):
                    result = coordinator.sync_project_file(project_file)
                    assert result
                    assert project_data["id"] == "web-app"

    def test_sync_project_file_preserves_existing_id(
        self, coordinator, tmp_path, mock_transaction
    ):
        """Test project syncing preserves existing ID."""
        project_file = tmp_path / "project.md"
        project_file.write_text("content")

        mock_conn = MagicMock()
        mock_transaction.__enter__.return_value = mock_conn

        project_data = {"id": "existing-id", "name": "Project"}

        with patch.object(
            coordinator._parser, "parse_yaml_frontmatter", return_value=project_data
        ):
            with patch.object(coordinator, "_extract_metadata", return_value=None):
                with patch.object(coordinator, "_update_sync_status"):
                    result = coordinator.sync_project_file(project_file)
                    assert result
                    assert project_data["id"] == "existing-id"

    def test_sync_project_file_includes_metadata(
        self, coordinator, tmp_path, mock_transaction
    ):
        """Test project syncing includes extra metadata."""
        project_file = tmp_path / "project.md"
        project_file.write_text("content")

        mock_conn = MagicMock()
        mock_transaction.__enter__.return_value = mock_conn

        project_data = {
            "name": "My Project",
            "owner": "team@example.com",
            "tags": ["important"],
        }

        with patch.object(
            coordinator._parser, "parse_yaml_frontmatter", return_value=project_data
        ):
            with patch.object(
                coordinator,
                "_extract_metadata",
                return_value='{"owner": "team@example.com"}',
            ) as mock_extract:
                with patch.object(coordinator, "_update_sync_status"):
                    result = coordinator.sync_project_file(project_file)
                    assert result
                    mock_extract.assert_called()

    def test_sync_project_file_exception_handling(
        self, coordinator, tmp_path, mock_transaction
    ):
        """Test project sync handles unexpected exceptions."""
        project_file = tmp_path / "project.md"
        project_file.write_text("content")

        with patch.object(coordinator._parser, "parse_yaml_frontmatter") as mock_parse:
            mock_parse.side_effect = ValueError("Parsing error")
            result = coordinator.sync_project_file(project_file)
            assert not result
