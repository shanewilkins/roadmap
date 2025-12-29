"""Tests for domain-specific entity sync coordinators."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


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
