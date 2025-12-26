"""Tests for CRUD helper utilities."""

from unittest.mock import MagicMock, patch

from roadmap.adapters.cli.crud.crud_helpers import (
    CRUDOperation,
    EntityType,
    collect_archive_files,
    display_archive_success,
    display_restore_success,
    format_entity_id,
    format_entity_title,
    get_active_dir,
    get_archive_dir,
    validate_entity_exists,
)


class TestEntityTypeEnum:
    """Test EntityType enum."""

    def test_entity_type_issue(self):
        """Test ISSUE entity type."""
        assert EntityType.ISSUE == "issue"
        assert EntityType.ISSUE.value == "issue"

    def test_entity_type_milestone(self):
        """Test MILESTONE entity type."""
        assert EntityType.MILESTONE == "milestone"
        assert EntityType.MILESTONE.value == "milestone"

    def test_entity_type_project(self):
        """Test PROJECT entity type."""
        assert EntityType.PROJECT == "project"
        assert EntityType.PROJECT.value == "project"


class TestCRUDOperationEnum:
    """Test CRUDOperation enum."""

    def test_crud_operation_exists(self):
        """Test CRUDOperation enum exists."""
        # Just verify the enum exists and is empty (for future use)
        assert hasattr(CRUDOperation, "__members__")


class TestFormatEntityTitle:
    """Test format_entity_title function."""

    def test_format_issue_title(self):
        """Test formatting issue title."""
        issue = MagicMock()
        issue.title = "Test Issue Title"

        result = format_entity_title(EntityType.ISSUE, issue)

        assert result == "Test Issue Title"

    def test_format_milestone_name(self):
        """Test formatting milestone name."""
        milestone = MagicMock()
        milestone.name = "v1.0.0"

        result = format_entity_title(EntityType.MILESTONE, milestone)

        assert result == "v1.0.0"

    def test_format_project_name(self):
        """Test formatting project name."""
        project = MagicMock()
        project.name = "My Project"

        result = format_entity_title(EntityType.PROJECT, project)

        assert result == "My Project"

    def test_format_fallback_entity(self):
        """Test formatting fallback case."""
        entity = MagicMock()
        entity.id = "test-id"

        # Test with a valid entity type that might not be specially handled
        result = format_entity_title(EntityType.ISSUE, entity)

        assert result == entity.title


class TestFormatEntityId:
    """Test format_entity_id function."""

    def test_format_entity_with_id(self):
        """Test formatting entity with id attribute."""
        entity = MagicMock()
        entity.id = "ISSUE-123"

        result = format_entity_id(EntityType.ISSUE, entity)

        assert result == "ISSUE-123"

    def test_format_entity_without_id(self):
        """Test formatting entity without id attribute."""
        entity = "some_string"

        result = format_entity_id(EntityType.ISSUE, entity)

        assert result == "some_string"

    def test_format_entity_id_milestone(self):
        """Test formatting milestone ID."""
        milestone = MagicMock()
        milestone.id = "v1.0.0"

        result = format_entity_id(EntityType.MILESTONE, milestone)

        assert result == "v1.0.0"


class TestValidateEntityExists:
    """Test validate_entity_exists function."""

    def test_validate_issue_exists(self):
        """Test validation of existing issue."""
        core = MagicMock()
        issue = MagicMock()
        core.issues.get.return_value = issue

        exists, error = validate_entity_exists(core, EntityType.ISSUE, "ISSUE-1")

        assert exists is True
        assert error is None
        core.issues.get.assert_called_once_with("ISSUE-1")

    def test_validate_issue_not_exists(self):
        """Test validation of non-existent issue."""
        core = MagicMock()
        core.issues.get.return_value = None

        exists, error = validate_entity_exists(core, EntityType.ISSUE, "ISSUE-999")

        assert exists is False
        assert error is not None
        assert "not found" in error.lower()

    def test_validate_milestone_exists(self):
        """Test validation of existing milestone."""
        core = MagicMock()
        milestone = MagicMock()
        core.milestones.get.return_value = milestone

        exists, error = validate_entity_exists(core, EntityType.MILESTONE, "v1.0.0")

        assert exists is True
        assert error is None
        core.milestones.get.assert_called_once_with("v1.0.0")

    def test_validate_milestone_not_exists(self):
        """Test validation of non-existent milestone."""
        core = MagicMock()
        core.milestones.get.return_value = None

        exists, error = validate_entity_exists(core, EntityType.MILESTONE, "v2.0.0")

        assert exists is False
        assert error is not None
        assert "not found" in error.lower()

    def test_validate_project_exists(self):
        """Test validation of existing project."""
        core = MagicMock()
        project = MagicMock()
        core.projects.get.return_value = project

        exists, error = validate_entity_exists(core, EntityType.PROJECT, "proj-1")

        assert exists is True
        assert error is None
        core.projects.get.assert_called_once_with("proj-1")

    def test_validate_project_not_exists(self):
        """Test validation of non-existent project."""
        core = MagicMock()
        core.projects.get.return_value = None

        exists, error = validate_entity_exists(core, EntityType.PROJECT, "proj-999")

        assert exists is False
        assert error is not None
        assert "not found" in error.lower()

    def test_validate_unknown_entity_type(self):
        """Test validation with invalid entity type."""
        core = MagicMock()

        # When called with an invalid EntityType, function returns error
        invalid_entity = "unknown"  # type: ignore
        exists, error = validate_entity_exists(core, invalid_entity, "id")  # type: ignore

        assert exists is False
        assert error is not None
        assert "Unknown entity type" in error or "Unknown" in error

    def test_validate_exception_handling(self):
        """Test validation handles exceptions."""
        core = MagicMock()
        core.issues.get.side_effect = Exception("Database error")

        exists, error = validate_entity_exists(core, EntityType.ISSUE, "ISSUE-1")

        assert exists is False
        assert error is not None
        assert "Error" in error or "error" in error


class TestCollectArchiveFiles:
    """Test collect_archive_files function."""

    def test_collect_issue_files(self, tmp_path):
        """Test collecting archived issue files."""
        archive_dir = tmp_path / "archive" / "issues"
        archive_dir.mkdir(parents=True)

        # Create test files
        (archive_dir / "ISSUE-1.md").touch()
        (archive_dir / "milestone-1" / "ISSUE-2.md").parent.mkdir(parents=True)
        (archive_dir / "milestone-1" / "ISSUE-2.md").touch()

        files = collect_archive_files(archive_dir, EntityType.ISSUE)

        assert len(files) == 2

    def test_collect_milestone_files(self, tmp_path):
        """Test collecting archived milestone files."""
        archive_dir = tmp_path / "archive" / "milestones"
        archive_dir.mkdir(parents=True)

        (archive_dir / "v1.0.0.md").touch()
        (archive_dir / "v2.0.0.md").touch()

        files = collect_archive_files(archive_dir, EntityType.MILESTONE)

        assert len(files) == 2

    def test_collect_nonexistent_archive(self, tmp_path):
        """Test collecting from non-existent archive directory."""
        archive_dir = tmp_path / "nonexistent"

        files = collect_archive_files(archive_dir, EntityType.ISSUE)

        assert files == []

    def test_collect_empty_archive(self, tmp_path):
        """Test collecting from empty archive."""
        archive_dir = tmp_path / "archive" / "issues"
        archive_dir.mkdir(parents=True)

        files = collect_archive_files(archive_dir, EntityType.ISSUE)

        assert files == []


class TestGetArchiveDir:
    """Test get_archive_dir function."""

    def test_get_issue_archive_dir(self):
        """Test getting issue archive directory."""
        result = get_archive_dir(EntityType.ISSUE)

        assert result.name == "issues"
        assert "archive" in str(result)

    def test_get_milestone_archive_dir(self):
        """Test getting milestone archive directory."""
        result = get_archive_dir(EntityType.MILESTONE)

        assert result.name == "milestones"
        assert "archive" in str(result)

    def test_get_project_archive_dir(self):
        """Test getting project archive directory."""
        result = get_archive_dir(EntityType.PROJECT)

        assert result.name == "projects"
        assert "archive" in str(result)


class TestGetActiveDir:
    """Test get_active_dir function."""

    def test_get_issue_active_dir(self):
        """Test getting issue active directory."""
        result = get_active_dir(EntityType.ISSUE)

        assert result.name == "issues"
        assert ".roadmap" in str(result)
        assert "archive" not in str(result)

    def test_get_milestone_active_dir(self):
        """Test getting milestone active directory."""
        result = get_active_dir(EntityType.MILESTONE)

        assert result.name == "milestones"
        assert ".roadmap" in str(result)

    def test_get_project_active_dir(self):
        """Test getting project active directory."""
        result = get_active_dir(EntityType.PROJECT)

        assert result.name == "projects"
        assert ".roadmap" in str(result)


class TestDisplayArchiveSuccess:
    """Test display_archive_success function."""

    def test_display_single_archived_item(self):
        """Test display message for single archived item."""
        console = MagicMock()

        display_archive_success(EntityType.ISSUE, 1, 0, console)

        console.print.assert_called()
        call_args = str(console.print.call_args)
        assert "1 issue" in call_args
        assert "Archived" in call_args

    def test_display_multiple_archived_items(self):
        """Test display message for multiple archived items."""
        console = MagicMock()

        display_archive_success(EntityType.ISSUE, 5, 0, console)

        call_args = str(console.print.call_args)
        assert "5 issues" in call_args

    def test_display_with_skipped_items(self):
        """Test display message includes skipped count."""
        console = MagicMock()

        display_archive_success(EntityType.MILESTONE, 3, 2, console)

        # Should print twice - once for success, once for skipped
        assert console.print.call_count == 2

    def test_display_no_console_provided(self):
        """Test display works when no console provided."""
        # Should use default console
        with patch("roadmap.adapters.cli.crud.crud_helpers.get_console") as mock_get:
            mock_console = MagicMock()
            mock_get.return_value = mock_console

            display_archive_success(EntityType.PROJECT, 1, 0)

            mock_get.assert_called_once()
            mock_console.print.assert_called()


class TestDisplayRestoreSuccess:
    """Test display_restore_success function."""

    def test_display_single_restored_item(self):
        """Test display message for single restored item."""
        console = MagicMock()

        display_restore_success(EntityType.ISSUE, 1, 0, console)

        console.print.assert_called()
        call_args = str(console.print.call_args)
        assert "1 issue" in call_args
        assert "Restored" in call_args

    def test_display_multiple_restored_items(self):
        """Test display message for multiple restored items."""
        console = MagicMock()

        display_restore_success(EntityType.MILESTONE, 4, 0, console)

        call_args = str(console.print.call_args)
        assert "4 milestones" in call_args

    def test_display_with_failed_items(self):
        """Test display message includes failed count."""
        console = MagicMock()

        display_restore_success(EntityType.PROJECT, 2, 1, console)

        # Should print twice - once for success, once for failures
        assert console.print.call_count == 2

    def test_display_no_console_provided(self):
        """Test display works when no console provided."""
        with patch("roadmap.adapters.cli.crud.crud_helpers.get_console") as mock_get:
            mock_console = MagicMock()
            mock_get.return_value = mock_console

            display_restore_success(EntityType.ISSUE, 1, 0)

            mock_get.assert_called_once()
            mock_console.print.assert_called()
