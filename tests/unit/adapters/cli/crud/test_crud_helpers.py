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

    import pytest

    @pytest.mark.parametrize(
        "etype,expected",
        [
            (EntityType.ISSUE, "issue"),
            (EntityType.MILESTONE, "milestone"),
            (EntityType.PROJECT, "project"),
        ],
    )
    def test_entity_type_values(self, etype, expected):
        assert etype == expected
        assert etype.value == expected


class TestCRUDOperationEnum:
    """Test CRUDOperation enum."""

    def test_crud_operation_exists(self):
        """Test CRUDOperation enum exists."""
        # Just verify the enum exists and is empty (for future use)
        assert hasattr(CRUDOperation, "__members__")


class TestFormatEntityTitle:
    """Test format_entity_title function."""

    import pytest

    @pytest.mark.parametrize(
        "etype,attr,value,expected",
        [
            (EntityType.ISSUE, "title", "Test Issue Title", "Test Issue Title"),
            (EntityType.MILESTONE, "name", "v1.0.0", "v1.0.0"),
            (EntityType.PROJECT, "name", "My Project", "My Project"),
        ],
    )
    def test_format_entity_title(self, etype, attr, value, expected):
        entity = MagicMock()
        setattr(entity, attr, value)
        result = format_entity_title(etype, entity)
        assert result == expected

    def test_format_fallback_entity(self):
        entity = MagicMock()
        entity.id = "test-id"
        # fallback: should return entity.title if present
        entity.title = "fallback-title"
        result = format_entity_title(EntityType.ISSUE, entity)
        assert result == entity.title


class TestFormatEntityId:
    """Test format_entity_id function."""

    import pytest

    @pytest.mark.parametrize(
        "etype,entity,expected",
        [
            (EntityType.ISSUE, MagicMock(id="ISSUE-123"), "ISSUE-123"),
            (EntityType.ISSUE, "some_string", "some_string"),
            (EntityType.MILESTONE, MagicMock(id="v1.0.0"), "v1.0.0"),
        ],
    )
    def test_format_entity_id(self, etype, entity, expected):
        result = format_entity_id(etype, entity)
        assert result == expected


class TestValidateEntityExists:
    """Test validate_entity_exists function."""

    import pytest

    @pytest.mark.parametrize(
        "etype,exists_return,entity_id,should_exist,should_error,expected_call_attr",
        [
            (EntityType.ISSUE, True, "ISSUE-1", True, False, "issues"),
            (EntityType.ISSUE, False, "ISSUE-999", False, True, "issues"),
            (EntityType.MILESTONE, True, "v1.0.0", True, False, "milestones"),
            (EntityType.MILESTONE, False, "v2.0.0", False, True, "milestones"),
            (EntityType.PROJECT, True, "proj-1", True, False, "projects"),
            (EntityType.PROJECT, False, "proj-999", False, True, "projects"),
        ],
    )
    def test_validate_entity_exists(
        self,
        etype,
        exists_return,
        entity_id,
        should_exist,
        should_error,
        expected_call_attr,
    ):
        core = MagicMock()
        entity_mock = MagicMock() if exists_return else None
        getattr(core, expected_call_attr).get.return_value = entity_mock
        exists, error = validate_entity_exists(core, etype, entity_id)
        assert exists is should_exist
        if should_error:
            assert error is not None
            assert "not found" in error.lower()
        else:
            assert error is None
        getattr(core, expected_call_attr).get.assert_called_once_with(entity_id)

    def test_validate_unknown_entity_type(self):
        core = MagicMock()
        invalid_entity = "unknown"  # type: ignore
        exists, error = validate_entity_exists(core, invalid_entity, "id")  # type: ignore
        assert exists is False
        assert error is not None
        assert "Unknown entity type" in error or "Unknown" in error

    def test_validate_exception_handling(self):
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
